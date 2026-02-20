"""
Generated Sites API endpoints.

Updated: January 22, 2026
- Integrated CRM services for automated lifecycle tracking
- Ensures all site generations have associated business records
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
import logging

from core.database import get_db
from api.deps import get_current_user
from api.schemas.site import (
    SiteGenerateRequest,
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


@router.get("/{site_id}", response_model=SiteDetailResponse)
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
