"""
Generated Sites API endpoints.

Updated: January 22, 2026
- Integrated CRM services for automated lifecycle tracking
- Ensures all site generations have associated business records
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
import io
import json
import logging
import re
import time

from core.database import get_db
from core.config import get_settings as _get_settings
from api.deps import get_current_user
from api.schemas.site import (
    SiteGenerateRequest,
    ManualGenerationRequest,
    SiteResponse,
    SiteDetailResponse,
    SiteListResponse,
    SiteGenerationResult,
    SiteUpdate,
    SiteStats
)
from services.hunter.business_service import BusinessService
from services.creative.site_service import SiteService
from services.creative.orchestrator import CreativeOrchestrator
from services.crm import BusinessLifecycleService
from models.user import AdminUser
from models.business import Business
from models.site import GeneratedSite

router = APIRouter(prefix="/sites", tags=["sites"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=SiteGenerationResult)
async def generate_site(
    request: SiteGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Generate a new website for a business.
    Runs the complete AI pipeline (Analyst → Concept → Director → Architect).
    """
    business_service = BusinessService(db)
    site_service = SiteService(db)
    
    # Get business
    business = await business_service.get_business(request.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check if site already exists
    existing_sites = await site_service.get_sites_by_business(
        request.business_id,
        status="live"
    )
    
    if existing_sites and not request.force_regenerate:
        raise HTTPException(
            status_code=400,
            detail="Site already exists for this business. Use force_regenerate=true to regenerate."
        )
    
    # Generate site in background
    async def generate_task():
        try:
            # Initialize services
            orchestrator = CreativeOrchestrator(db)
            lifecycle_service = BusinessLifecycleService(db)
            
            # Update business status: none → generating
            await lifecycle_service.mark_website_generating(business.id)
            await db.commit()
            
            # Prepare business data
            business_data = {
                "id": str(business.id),
                "name": business.name,
                "category": business.category,
                "city": business.city,
                "state": business.state,
                "country": business.country,
                "phone": business.phone,
                "email": business.email,
                "rating": float(business.rating) if business.rating else 0,
                "review_count": business.review_count,
                "reviews_data": [],  # TODO: Add actual reviews
                "photos_urls": business.photos_urls or []
            }
            
            # Run generation pipeline
            results = await orchestrator.generate_website(business_data)
            
            # Extract website code
            website = results.get("website", {})
            
            # Generate subdomain
            subdomain = await site_service.generate_subdomain(business.name)
            
            # Create site record
            site = await site_service.create_site(
                business_id=business.id,
                subdomain=subdomain,
                html_content=website.get("html", ""),
                css_content=website.get("css", ""),
                js_content=website.get("js", ""),
                design_brief=results.get("design_brief", {}),
                assets_urls=website.get("assets_needed", []),
                status="preview"
            )
            
            # Update business status: generating → generated
            await lifecycle_service.mark_website_generated(business.id)
            await db.commit()
            
            logger.info(
                f"Site generated successfully: {subdomain} "
                f"(Business: {business.name}, Status: generated)"
            )
            
        except Exception as e:
            logger.error(f"Site generation failed: {str(e)}", exc_info=True)
            await db.rollback()
            # Note: business status will remain "generating" on failure
            # Admin can retry or manually update
    
    background_tasks.add_task(generate_task)
    
    return SiteGenerationResult(
        site_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
        status="generating",
        message=f"Site generation started for {business.name}",
        duration_ms=None,
        summary=None
    )


@router.post("/generate-manual", response_model=SiteGenerationResult)
async def generate_manual_site(
    request: ManualGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Generate a website from a free-form business description.

    Creates a Business record using provided details (or a placeholder derived
    from the description), stores the full request in ``raw_data["manual_input"]``,
    and queues the existing generation pipeline.  Stage 0 of the pipeline
    (BusinessInterpreterAgent) will interpret and enrich the description before
    the main agents run.
    """
    from tasks.generation_sync import generate_site_for_business  # lazy import to avoid circular

    # Derive a display name: use the hard-fact name if given, otherwise take
    # the first 5 words of the description as a working title.
    display_name: str = (
        request.name
        or " ".join(request.description.split()[:5]).rstrip(".,!?")
    )

    # Generate a URL-safe slug from the display name.
    base_slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-")
    # Ensure uniqueness by appending a short random suffix.
    import uuid as _uuid
    slug = f"{base_slug}-{str(_uuid.uuid4())[:8]}"

    # Build raw_data payload — everything the pipeline needs.
    manual_input = {
        "description": request.description,
        "website_type": request.website_type,
        "branding_notes": request.branding_notes,
        "branding_images": request.branding_images or [],
    }
    hard_facts = {
        k: getattr(request, k)
        for k in ("name", "phone", "email", "address", "city", "state")
        if getattr(request, k)
    }
    manual_input.update(hard_facts)

    # Store pricing when supplied; claim bar and checkout will read from here.
    if request.one_time_price is not None:
        manual_input["one_time_price"] = request.one_time_price
    if request.monthly_price is not None:
        manual_input["monthly_price"] = request.monthly_price

    raw_data = {
        "manual_generation": True,
        "manual_input": manual_input,
    }

    # Create the Business record.
    business = Business(
        name=display_name,
        slug=slug,
        phone=request.phone,
        email=request.email,
        address=request.address,
        city=request.city,
        state=request.state,
        website_status="queued",
        raw_data=raw_data,
    )
    db.add(business)
    await db.flush()
    await db.refresh(business)

    # Create a placeholder GeneratedSite record so the frontend can poll its status.
    site_service = SiteService(db)
    subdomain = await site_service.generate_subdomain(display_name)
    site = GeneratedSite(
        business_id=business.id,
        subdomain=subdomain,
        status="generating",
    )
    db.add(site)
    await db.flush()
    await db.refresh(site)
    await db.commit()

    # Queue the existing generation task (it now reads manual_input from raw_data).
    generate_site_for_business.delay(str(business.id))

    logger.info(
        "Manual site generation queued for '%s' (business=%s, site=%s, type=%s)",
        display_name,
        business.id,
        site.id,
        request.website_type,
    )

    return SiteGenerationResult(
        site_id=site.id,
        status="generating",
        message=f"Manual site generation started for '{display_name}'",
        duration_ms=None,
        summary=None,
    )


@router.get("/", response_model=SiteListResponse)
async def list_sites(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """List all generated sites with pagination."""
    service = SiteService(db)
    
    skip = (page - 1) * page_size
    sites, total = await service.list_sites(
        skip=skip,
        limit=page_size,
        status=status
    )
    
    pages = (total + page_size - 1) // page_size
    
    # Convert sites to response format, serializing business relationship
    site_responses = []
    for s in sites:
        site_dict = {
            "id": s.id,
            "business_id": s.business_id,
            "subdomain": s.subdomain,
            "custom_domain": s.custom_domain,
            "short_url": s.short_url,  # Pre-generated short link
            "status": s.status,
            "version": s.version,
            "deployed_at": s.deployed_at,
            "sold_at": s.sold_at,
            "lighthouse_score": s.lighthouse_score,
            "load_time_ms": s.load_time_ms,
            "screenshot_desktop_url": s.screenshot_desktop_url,
            "screenshot_mobile_url": s.screenshot_mobile_url,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "full_url": s.full_url,
            "is_live": s.is_live,
            "business": {
                "id": str(s.business.id),
                "name": s.business.name,
                "category": s.business.category,
                "phone": s.business.phone,
                "address": s.business.address,
                "city": s.business.city,
                "state": s.business.state,
                "rating": float(s.business.rating) if s.business.rating else None,
                "review_count": s.business.review_count,
                "website_url": s.business.website_url,
                "website_validation_status": s.business.website_validation_status,
                "gmb_place_id": s.business.gmb_place_id,
            } if s.business else None
        }
        site_responses.append(SiteResponse.model_validate(site_dict))
    
    return SiteListResponse(
        sites=site_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/stats", response_model=SiteStats)
async def get_site_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get site statistics."""
    service = SiteService(db)
    stats = await service.get_stats()
    return SiteStats(**stats)


@router.get("/detail/{site_id}", response_model=SiteDetailResponse)
async def get_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get a specific site by ID with full content and business data."""
    service = SiteService(db)
    site = await service.get_site(site_id)
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    site_dict = {
        "id": site.id,
        "business_id": site.business_id,
        "subdomain": site.subdomain,
        "custom_domain": site.custom_domain,
        "short_url": site.short_url,
        "status": site.status,
        "version": site.version,
        "deployed_at": site.deployed_at,
        "sold_at": site.sold_at,
        "lighthouse_score": site.lighthouse_score,
        "load_time_ms": site.load_time_ms,
        "screenshot_desktop_url": site.screenshot_desktop_url,
        "screenshot_mobile_url": site.screenshot_mobile_url,
        "created_at": site.created_at,
        "updated_at": site.updated_at,
        "full_url": site.full_url,
        "is_live": site.is_live,
        "html_content": site.html_content,
        "css_content": site.css_content,
        "js_content": site.js_content,
        "design_brief": site.design_brief,
        "assets_urls": site.assets_urls or [],
        "business": {
            "id": str(site.business.id),
            "name": site.business.name,
            "category": site.business.category,
            "phone": site.business.phone,
            "address": site.business.address,
            "city": site.business.city,
            "state": site.business.state,
            "rating": float(site.business.rating) if site.business.rating else None,
            "review_count": site.business.review_count,
            "website_url": site.business.website_url,
            "gmb_place_id": site.business.gmb_place_id,
        } if site.business else None,
    }
    return SiteDetailResponse.model_validate(site_dict)


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: UUID,
    updates: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Update a site."""
    service = SiteService(db)
    
    # Get existing site
    existing = await service.get_site(site_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Apply updates
    update_dict = updates.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated = await service.update_site(site_id, update_dict)
    await db.commit()
    
    return SiteResponse.model_validate(updated)


@router.post("/{site_id}/deploy")
async def deploy_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Deploy site to live status."""
    service = SiteService(db)
    
    site = await service.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    await service.update_site(
        site_id,
        {
            "status": "live",
            "deployed_at": datetime.utcnow()
        }
    )
    await db.commit()
    
    return {
        "message": "Site deployed successfully",
        "site_id": str(site_id),
        "url": site.full_url
    }


from datetime import datetime
from pydantic import BaseModel, Field
from services.creative.image_service import ImageGenerationService
from fastapi.responses import Response


class ImageGenerationRequest(BaseModel):
    """Request for testing image generation."""
    business_name: str = Field(..., description="Business name")
    category: str = Field(..., description="Business category (e.g., 'restaurant', 'spa')")
    brand_archetype: str = Field(
        default="Regular Guy",
        description="Brand archetype (Explorer, Creator, Caregiver, etc.)"
    )
    color_primary: str = Field(default="#2563eb", description="Primary color hex")
    color_secondary: str = Field(default="#7c3aed", description="Secondary color hex")
    color_accent: str = Field(default="#f59e0b", description="Accent color hex")
    image_type: str = Field(
        default="hero",
        description="Type of image to generate (hero, background, product, icon)"
    )
    aspect_ratio: str = Field(default="16:9", description="Image aspect ratio")


class ImageGenerationResponse(BaseModel):
    """Response for image generation test."""
    success: bool
    message: str
    size_bytes: Optional[int] = None
    aspect_ratio: Optional[str] = None
    image_type: str


@router.post("/{site_id}/mark-has-website")
async def mark_site_has_website(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Mark a generated site as 'superseded' because the business already has its own website.

    Updates:
    - generated_sites.status → 'superseded'
    - business.website_validation_status → 'valid_manual'
    - business.website_status → cleared (set to 'none') so it doesn't re-enter the queue
    """
    from sqlalchemy import select
    from models.site import GeneratedSite
    from models.business import Business

    result = await db.execute(select(GeneratedSite).where(GeneratedSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    site.status = "superseded"

    if site.business_id:
        biz_result = await db.execute(select(Business).where(Business.id == site.business_id))
        business = biz_result.scalar_one_or_none()
        if business:
            business.website_validation_status = "valid_manual"
            business.website_status = "none"

    await db.commit()
    return {"success": True, "message": "Site marked as superseded (business has own website)"}


@router.post("/{site_id}/mark-unreachable")
async def mark_site_unreachable(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Mark a generated site as 'superseded' because the business is unreachable
    (no phone, no email, or uncontactable).

    Updates:
    - generated_sites.status → 'superseded'
    - business.website_status → 'ineligible'
    - business.outreach_channel → 'call_later' (deprioritised — no SMS/email contact available)
    """
    from sqlalchemy import select
    from models.site import GeneratedSite
    from models.business import Business
    from core.outreach_enums import OutreachChannel

    result = await db.execute(select(GeneratedSite).where(GeneratedSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    site.status = "superseded"

    if site.business_id:
        biz_result = await db.execute(select(Business).where(Business.id == site.business_id))
        business = biz_result.scalar_one_or_none()
        if business:
            business.website_status = "ineligible"
            business.outreach_channel = OutreachChannel.CALL_LATER.value
            business.generation_queued_at = None
            business.generation_started_at = None

    await db.commit()
    return {"success": True, "message": "Site marked as superseded (business unreachable)"}


@router.post("/{site_id}/regenerate-images")
async def regenerate_site_images(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Regenerate the 3 AI images (hero, about, services) for an existing generated site.

    After saving new image files, updates the img src attributes in the stored HTML to
    append a ?v=<timestamp> cache-buster.  Nginx caches .jpg files for 30 days, so
    without a version parameter the browser would serve the old image from its cache
    even though the file on disk has been replaced.  Only the 3 src attributes change —
    no other HTML is touched.
    """
    from sqlalchemy import select
    from models.site import GeneratedSite
    from models.business import Business
    from services.creative.image_service import ImageGenerationService

    result = await db.execute(select(GeneratedSite).where(GeneratedSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if not site.subdomain:
        raise HTTPException(status_code=400, detail="Site has no subdomain — cannot save images")

    business = None
    if site.business_id:
        biz_result = await db.execute(select(Business).where(Business.id == site.business_id))
        business = biz_result.scalar_one_or_none()

    # Derive inputs for image generation
    business_name = business.name if business else "Business"
    category = (business.category or business.subcategory or "") if business else ""

    # Extract brand context from design_brief (the only creative data persisted to DB).
    # brand_concept / brand_analysis were set as transient Python attrs in generation_sync
    # but are not mapped DB columns — design_brief is the real storage.
    brief = site.design_brief or {}
    colors = brief.get("colors") or {}
    brand_colors: dict = {
        "primary": colors.get("primary", ""),
        "secondary": colors.get("secondary", ""),
    }

    # Build a minimal creative_dna-style dict from what we have in design_brief
    # so ImageGenerationService can still apply some brand direction.
    vibe = brief.get("vibe", "")
    industry_persona = brief.get("industry_persona", "")
    creative_dna: dict = {}
    if vibe:
        creative_dna["visual_identity"] = vibe
    if industry_persona:
        creative_dna["value_proposition"] = industry_persona

    image_service = ImageGenerationService()
    if not image_service.api_key:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")

    try:
        image_results = await image_service.generate_images_for_site(
            business_name=business_name,
            category=category,
            subdomain=site.subdomain,
            brand_colors=brand_colors or None,
            creative_dna=creative_dna or None,
        )
    except Exception as e:
        logger.error(f"Image regeneration failed for site {site_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

    saved = [r for r in image_results if r.get("saved")]
    failed = [r["slot"] for r in image_results if not r.get("saved")]

    # ── Save prompts + cache-bust HTML ──────────────────────────────────────
    if saved:
        # 1. Persist prompts, subjects, and version history for each regenerated slot.
        updated_brief = dict(site.design_brief or {})
        new_prompts = {
            r["slot"]: r.get("full_prompt")
            for r in image_results
            if isinstance(r, dict) and r.get("slot") and r.get("full_prompt")
        }
        if new_prompts:
            updated_brief["image_prompts"] = {
                **(updated_brief.get("image_prompts") or {}),
                **new_prompts,
            }

        new_subjects = {
            r["slot"]: r.get("subject")
            for r in image_results
            if isinstance(r, dict) and r.get("slot") and r.get("subject")
        }
        if new_subjects:
            updated_brief["image_subjects"] = {
                **(updated_brief.get("image_subjects") or {}),
                **new_subjects,
            }

        # Append versioned filenames for history tracking
        _run_ts = int(time.time())
        prev_versions = updated_brief.get("image_versions") or {}
        for r in image_results:
            if isinstance(r, dict) and r.get("slot") and r.get("version"):
                entry = {"filename": r["version"], "timestamp": _run_ts}
                prev_versions.setdefault(r["slot"], []).append(entry)
        updated_brief["image_versions"] = prev_versions

        site.design_brief = updated_brief
        logger.info(
            f"[RegenImages] Updated design_brief for site {site_id} "
            f"(slots: {list(new_prompts.keys())})"
        )

        # 2. Append ?v=<timestamp> cache-busters to img src attributes in the
        #    stored HTML so browsers bypass Nginx's 30-day .jpg cache.
        if site.html_content:
            version = int(time.time())
            updated_html = re.sub(
                r'(src="img/(hero|about|services)\.jpg)(?:\?v=\d+)?(")',
                lambda m: f'{m.group(1)}?v={version}{m.group(3)}',
                site.html_content,
            )
            if updated_html != site.html_content:
                site.html_content = updated_html
                logger.info(
                    f"[RegenImages] Updated img src cache-busters to v={version} "
                    f"for site {site_id} ({site.subdomain})"
                )

        await db.commit()

    return {
        "success": len(saved) > 0,
        "saved": len(saved),
        "total": len(image_results),
        "slots": {r["slot"]: r.get("filename") for r in image_results if r.get("saved")},
        "failed_slots": failed,
        "message": f"Regenerated {len(saved)}/{len(image_results)} images for {business_name}",
    }


@router.post("/{site_id}/remap-product-images")
async def remap_product_images(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Fix image-to-product mismatches on an existing generated site without full regeneration.

    Reads the stored image subjects from design_brief (set during generation) and the
    product card HTML, then uses Claude to determine the optimal image ↔ product-name
    mapping and updates the src attributes in the stored HTML.

    This is a targeted fix that costs a few hundred tokens instead of the full pipeline.
    """
    import anthropic

    result = await db.execute(select(GeneratedSite).where(GeneratedSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if not site.html_content:
        raise HTTPException(status_code=400, detail="Site has no HTML content")

    brief = site.design_brief or {}

    # Build image subject map — prefer stored subjects, fall back to parsing full_prompt
    image_subjects: dict = brief.get("image_subjects") or {}
    if not image_subjects:
        for slot, full_prompt in (brief.get("image_prompts") or {}).items():
            if full_prompt:
                # full_prompt starts with desc, ends with "For a business called '...'"
                subject = full_prompt.split("For a business called")[0].strip()
                if subject:
                    image_subjects[slot] = subject

    if not image_subjects:
        raise HTTPException(
            status_code=400,
            detail="No image subject data found in design_brief — regenerate images first"
        )

    # Extract all `img/product-N.jpg` occurrences with their surrounding context
    product_src_pattern = re.compile(
        r'src=["\']img/(product-\d+)\.jpg(?:\?[^"\']*)?["\']'
    )
    slots_in_html = product_src_pattern.findall(site.html_content)
    if not slots_in_html:
        raise HTTPException(status_code=400, detail="No product image src attributes found in HTML")

    # Build context for Claude: what does each image file show, and what slot is currently there
    image_index = "\n".join(
        f"  {slot}: \"{subject}\""
        for slot, subject in sorted(image_subjects.items())
    )

    # Ask Claude to produce the correct mapping: each product card slot → image slot
    prompt = f"""You are fixing an ecommerce website where product images were assigned in the wrong order.

The website has these product image files. Each file depicts a specific item:
{image_index}

The HTML currently places product images using `src="img/product-N.jpg"` attributes.
There are {len(set(slots_in_html))} unique product slots used in the HTML: {sorted(set(slots_in_html))}

Your job: produce a JSON object that maps each CURRENT slot in the HTML to the slot it SHOULD be
(i.e. which image file best fits each position based on what the image depicts).
The goal is that product cards with names like "cat tree" or "scratching post" get the image
that shows a cat tree, not a water fountain.

Here is a snippet of the HTML product section to help you understand the current product names:
{site.html_content[site.html_content.lower().find('featured') if 'featured' in site.html_content.lower() else 0:][:3000]}

Return ONLY a valid JSON object in this exact format — no explanation:
{{
  "product-1": "product-X",
  "product-2": "product-Y",
  ...
}}
where the keys are the current slots used in HTML and the values are the correct image slots to use.
Every slot that appears in the HTML must be present as a key. Values must be valid slot names from
the image index above."""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    # Parse the JSON mapping
    try:
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        mapping: dict = json.loads(raw)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Claude returned invalid JSON: {e}. Raw: {raw[:200]}"
        )

    # Validate: all mapped-to slots must exist as image files on disk
    from pathlib import Path as _Path
    img_dir = _Path(_get_settings().SITES_BASE_PATH) / site.subdomain / "img"

    valid_mapping = {
        current: target
        for current, target in mapping.items()
        if current != target  # skip no-ops
        and (img_dir / f"{target}.jpg").exists()
    }

    if not valid_mapping:
        return {
            "success": False,
            "message": "Claude determined that no remapping is necessary (images already correctly assigned)",
            "mapping": mapping,
        }

    # Apply the mapping: replace src="img/product-N.jpg" occurrences in HTML
    # Use a two-pass approach with a sentinel to avoid double-replacement
    updated_html = site.html_content
    version = int(time.time())
    sentinel_map = {}
    for current_slot, target_slot in valid_mapping.items():
        sentinel = f"__REMAP_{current_slot.upper()}__"
        sentinel_map[sentinel] = f"img/{target_slot}.jpg?v={version}"
        updated_html = re.sub(
            rf'(src=["\'])img/{re.escape(current_slot)}\.jpg(?:\?[^"\']*)?(["\'])',
            rf'\g<1>{sentinel}\g<2>',
            updated_html,
        )
    for sentinel, replacement in sentinel_map.items():
        updated_html = updated_html.replace(sentinel, replacement)

    site.html_content = updated_html
    await db.commit()

    logger.info(
        "[RemapImages] Applied %d remappings for site %s: %s",
        len(valid_mapping), site_id, valid_mapping,
    )

    return {
        "success": True,
        "message": f"Remapped {len(valid_mapping)} product image(s)",
        "mapping": valid_mapping,
    }


@router.get("/{site_id}/image-versions")
async def get_image_versions(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Return the version history for all image slots on a site.
    Version entries are stored in design_brief.image_versions, created each time
    images are generated or regenerated.
    """
    result = await db.execute(select(GeneratedSite).where(GeneratedSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    brief = site.design_brief or {}
    versions = brief.get("image_versions") or {}
    subjects = brief.get("image_subjects") or {}

    return {
        "subdomain": site.subdomain,
        "slots": {
            slot: {
                "subject": subjects.get(slot),
                "versions": sorted(entries, key=lambda x: x.get("timestamp", 0), reverse=True),
            }
            for slot, entries in versions.items()
        },
    }


@router.post("/{site_id}/activate-image-version")
async def activate_image_version(
    site_id: UUID,
    slot: str = Query(..., description="Image slot, e.g. 'product-1' or 'hero'"),
    version_filename: str = Query(..., description="Versioned filename, e.g. 'img/product-1_v1709000000.jpg'"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Make a previously-generated image version the active (canonical) image for a slot.

    Copies the versioned file to the canonical filename (e.g. product-1.jpg) and
    appends a cache-buster to the HTML src so browsers fetch the new version.
    """
    import shutil as _shutil
    from pathlib import Path as _Path2

    result = await db.execute(select(GeneratedSite).where(GeneratedSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    img_dir = _Path2(_get_settings().SITES_BASE_PATH) / site.subdomain / "img"

    # Resolve source path — version_filename is relative like "img/product-1_v123.jpg"
    versioned_name = version_filename.lstrip("img/").lstrip("/")
    src_path = img_dir / versioned_name
    if not src_path.exists():
        raise HTTPException(status_code=404, detail=f"Versioned file not found: {versioned_name}")

    canonical_name = f"{slot}.jpg"
    dest_path = img_dir / canonical_name

    # Copy versioned → canonical
    _shutil.copy2(str(src_path), str(dest_path))

    # Update HTML src with cache-buster
    version_stamp = int(time.time())
    if site.html_content:
        updated_html = re.sub(
            rf'(src=["\'])img/{re.escape(slot)}\.jpg(?:\?[^"\']*)?(["\'])',
            rf'\g<1>img/{slot}.jpg?v={version_stamp}\g<2>',
            site.html_content,
        )
        if updated_html != site.html_content:
            site.html_content = updated_html

    await db.commit()

    logger.info(
        "[ActivateVersion] Site %s slot '%s': activated %s",
        site_id, slot, versioned_name,
    )

    return {
        "success": True,
        "message": f"Activated {versioned_name} as the active image for slot '{slot}'",
        "slot": slot,
        "canonical": f"img/{canonical_name}",
        "version_stamp": version_stamp,
    }


@router.post("/{site_id}/regenerate", response_model=SiteGenerationResult)
async def regenerate_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Regenerate a site from scratch.

    Resets the existing GeneratedSite record (clears HTML/CSS/JS, sets status
    back to "generating") and re-queues the Celery generation task for the
    associated business.  Works regardless of the current site status — useful
    when a site completed but the output is unsatisfactory.
    """
    from tasks.generation_sync import generate_site_for_business  # lazy import

    result = await db.execute(select(GeneratedSite).where(GeneratedSite.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if not site.business_id:
        raise HTTPException(status_code=400, detail="Site has no associated business — cannot regenerate")

    # Fetch the business so we can reset its status too
    biz_result = await db.execute(select(Business).where(Business.id == site.business_id))
    business = biz_result.scalar_one_or_none()

    # Reset site content and status
    site.html_content = None
    site.css_content = None
    site.js_content = None
    site.status = "generating"
    site.error_message = None
    site.error_category = None
    site.deployed_at = None

    # Reset business generation flags so the task doesn't skip the eligibility check
    if business:
        business.website_status = "queued"
        business.generation_started_at = None
        business.generation_completed_at = None

    await db.commit()

    # Re-queue the generation task
    generate_site_for_business.delay(str(site.business_id))

    logger.info(
        "Site regeneration queued for site %s (business: %s — %s)",
        site_id,
        site.business_id,
        business.name if business else "unknown",
    )

    return SiteGenerationResult(
        site_id=site_id,
        status="generating",
        message=f"Site regeneration started for {business.name if business else str(site_id)}",
        duration_ms=None,
        summary=None,
    )


@router.post("/test-image-generation", response_model=ImageGenerationResponse)
async def test_image_generation(
    request: ImageGenerationRequest,
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Test image generation endpoint.
    Generates an AI image based on parameters and returns metadata.
    Protected by authentication - only logged-in admins can use this.
    """
    logger.info(f"Testing image generation for {request.business_name}")
    
    # Initialize image service
    try:
        image_service = ImageGenerationService()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Image generation service not available: {str(e)}"
        )
    
    # Prepare color palette
    color_palette = {
        "primary": request.color_primary,
        "secondary": request.color_secondary,
        "accent": request.color_accent
    }
    
    try:
        # Generate image based on type
        image_bytes = None
        
        if request.image_type == "hero":
            image_bytes = await image_service.generate_hero_image(
                business_name=request.business_name,
                category=request.category,
                brand_archetype=request.brand_archetype,
                color_palette=color_palette,
                aspect_ratio=request.aspect_ratio
            )
        
        elif request.image_type == "background":
            image_bytes = await image_service.generate_section_background(
                section_type="about",
                mood="professional",
                color_palette=color_palette,
                aspect_ratio=request.aspect_ratio
            )
        
        elif request.image_type == "product":
            image_bytes = await image_service.generate_product_image(
                product_description=f"{request.category} service",
                style="professional",
                aspect_ratio=request.aspect_ratio
            )
        
        elif request.image_type == "icon":
            image_bytes = await image_service.generate_icon(
                icon_description=f"{request.category} icon",
                style="modern minimalist"
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image_type: {request.image_type}"
            )
        
        if not image_bytes:
            return ImageGenerationResponse(
                success=False,
                message="Image generation failed - no data returned",
                image_type=request.image_type
            )
        
        return ImageGenerationResponse(
            success=True,
            message=f"Image generated successfully",
            size_bytes=len(image_bytes),
            aspect_ratio=request.aspect_ratio,
            image_type=request.image_type
        )
    
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        return ImageGenerationResponse(
            success=False,
            message=f"Image generation failed: {str(e)}",
            image_type=request.image_type
        )


@router.post("/test-image-generation/download")
async def test_image_generation_download(
    request: ImageGenerationRequest,
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Test image generation and return the actual image file.
    Protected by authentication - only logged-in admins can use this.
    """
    logger.info(f"Generating image download for {request.business_name}")
    
    # Initialize image service
    try:
        image_service = ImageGenerationService()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Image generation service not available: {str(e)}"
        )
    
    # Prepare color palette
    color_palette = {
        "primary": request.color_primary,
        "secondary": request.color_secondary,
        "accent": request.color_accent
    }
    
    try:
        # Generate image based on type
        image_bytes = None
        
        if request.image_type == "hero":
            image_bytes = await image_service.generate_hero_image(
                business_name=request.business_name,
                category=request.category,
                brand_archetype=request.brand_archetype,
                color_palette=color_palette,
                aspect_ratio=request.aspect_ratio
            )
        
        elif request.image_type == "background":
            image_bytes = await image_service.generate_section_background(
                section_type="about",
                mood="professional",
                color_palette=color_palette,
                aspect_ratio=request.aspect_ratio
            )
        
        elif request.image_type == "product":
            image_bytes = await image_service.generate_product_image(
                product_description=f"{request.category} service",
                style="professional",
                aspect_ratio=request.aspect_ratio
            )
        
        elif request.image_type == "icon":
            image_bytes = await image_service.generate_icon(
                icon_description=f"{request.category} icon",
                style="modern minimalist"
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image_type: {request.image_type}"
            )
        
        if not image_bytes:
            raise HTTPException(
                status_code=500,
                detail="Image generation failed - no data returned"
            )
        
        # Return image as PNG
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename={request.image_type}-{request.business_name.replace(' ', '-').lower()}.png"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Image generation failed: {str(e)}"
        )


# ── Site file export ──────────────────────────────────────────────────────────

@router.get("/{site_id}/export")
async def export_site_files(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Export all files for a generated site as a downloadable ZIP archive.

    The archive contains:
      - index.html  (the full site HTML, from the database)
      - styles.css  (the stylesheet, from the database)
      - script.js   (JavaScript, from the database, if present)
      - img/        (hero.jpg, about.jpg, services.jpg from disk, if present)

    As a side-effect the text files are also written to
    ``SITES_BASE_PATH/{subdomain}/`` so the folder is kept in sync with the
    database and could be served statically if needed.
    """
    from models.site import GeneratedSite
    from core.config import get_settings
    from services.creative.site_export_service import write_site_files, build_site_zip

    result = await db.execute(select(GeneratedSite).where(GeneratedSite.id == site_id))
    site = result.scalar_one_or_none()

    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if not site.html_content:
        raise HTTPException(
            status_code=422,
            detail="Site has no HTML content yet — generation may still be in progress.",
        )

    settings = get_settings()

    # Write text files to disk so the folder is self-contained
    write_site_files(
        subdomain=site.subdomain,
        html=site.html_content,
        css=site.css_content,
        js=site.js_content,
        sites_base_path=settings.SITES_BASE_PATH,
    )

    # Build the ZIP in memory (includes images already on disk)
    zip_bytes = build_site_zip(
        subdomain=site.subdomain,
        html=site.html_content,
        css=site.css_content,
        js=site.js_content,
        sites_base_path=settings.SITES_BASE_PATH,
    )

    filename = f"{site.subdomain}.zip"
    logger.info(
        "Exporting site %r (%s) — %d bytes",
        site.subdomain,
        site_id,
        len(zip_bytes),
    )

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
