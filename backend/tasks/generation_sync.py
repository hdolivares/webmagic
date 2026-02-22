"""
Synchronous site generation tasks for Celery.

IMPORTANT: Celery tasks MUST be synchronous functions.
Async functions will be registered but never executed.

This module provides sync wrappers around async generation logic.
"""
from celery import Task
from celery_app import celery_app
from sqlalchemy import select, update
from datetime import datetime
import logging
import asyncio

from core.database import get_db_session_sync, AsyncSessionLocal
from models.business import Business
from models.site import GeneratedSite
from services.creative.orchestrator import CreativeOrchestrator
from services.sms.number_lookup import NumberLookupService
from services.sms.phone_validator import PhoneValidator

logger = logging.getLogger(__name__)


# Minimum HTML size (bytes) — anything below this is almost certainly truncated
_MIN_HTML_BYTES = 20_000

# Keywords expected near the top of <body> for a valid full-page generation
_HERO_KEYWORDS = ["hero", 'class="hero', "id=\"hero", "class='hero", "id='hero"]
_NAV_KEYWORDS  = [
    "nav-link", "nav-logo", "nav-brand", "nav-content", "nav-menu",
    "<a href", "logo", "hamburger", "menu-toggle",
]


def _is_html_complete(html: str | None) -> bool:
    """
    Return True only if the HTML looks like a full-page generation.

    Checks:
    1. Minimum byte size (_MIN_HTML_BYTES)
    2. Presence of a <body> tag
    3. Hero or nav content in the first 2000 chars of <body>
    """
    if not html or len(html) < _MIN_HTML_BYTES:
        return False

    lower = html.lower()
    body_pos = lower.find("<body")
    if body_pos == -1:
        return False

    body_start = lower[body_pos: body_pos + 2_000]
    has_hero = any(kw in body_start for kw in _HERO_KEYWORDS)
    has_nav  = any(kw in body_start for kw in _NAV_KEYWORDS)
    return has_hero or has_nav


def run_async(coro):
    """
    Helper to run async code in sync context.
    Creates new event loop if needed.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10 minutes
    autoretry_for=(Exception,),
    retry_backoff=True
)
def generate_site_for_business(self, business_id: str):
    """
    Generate a website for a specific business (SYNC wrapper).
    
    Args:
        business_id: Business UUID string
        
    Returns:
        Dict with generation result
    """
    logger.info(f"[Celery Task] Starting site generation for business: {business_id}")
    
    async def _generate():
        """Inner async function with actual generation logic."""
        async with AsyncSessionLocal() as db:
            try:
                # Get business
                result = await db.execute(
                    select(Business).where(Business.id == business_id)
                )
                business = result.scalar_one_or_none()
                
                if not business:
                    logger.error(f"Business not found: {business_id}")
                    return {"status": "error", "message": "Business not found"}
                
                # **IDEMPOTENCY CHECK: Verify business still needs a website**
                if business.website_validation_status == 'valid':
                    logger.warning(
                        f"Business {business_id} has valid website: {business.website_url}. "
                        "Skipping generation."
                    )
                    # Update status to reflect it doesn't need generation
                    business.website_status = 'none'
                    business.generation_queued_at = None
                    await db.commit()
                    return {
                        "status": "skipped",
                        "reason": "has_valid_website",
                        "website_url": business.website_url
                    }
                
                # ── Phone line-type check ─────────────────────────────────────
                # Run before Claude to avoid wasting tokens on businesses we
                # can never reach. Skips ONLY when phone is the sole contact
                # method and it's a definitively non-SMS line type.
                # Businesses with email can still get a site for email outreach.
                if business.phone and business.phone_line_type is None:
                    is_valid, formatted_phone, _ = PhoneValidator.validate_and_format(
                        business.phone
                    )
                    if is_valid:
                        lookup = await NumberLookupService().lookup(formatted_phone)
                        business.phone_line_type = lookup.line_type
                        business.phone_lookup_at = datetime.utcnow()
                        await db.flush()
                        logger.info(
                            "Phone lookup for %s (%s): %s — sms_capable=%s",
                            business.name, formatted_phone,
                            lookup.line_type, lookup.is_sms_capable,
                        )

                # If the phone is blocked AND there is no email, skip generation.
                # (Email-only path still gets a site; no-contact businesses are useless.)
                _blocked_types = {"landline", "toll_free", "premium_rate"}
                if (
                    business.phone_line_type in _blocked_types
                    and not business.email
                ):
                    logger.info(
                        "Skipping site generation for %s — %s phone, no email",
                        business.name, business.phone_line_type,
                    )
                    business.website_status = "ineligible"
                    business.generation_queued_at = None
                    await db.commit()
                    return {
                        "status": "skipped",
                        "reason": "landline_no_email",
                        "business_id": business_id,
                        "line_type": business.phone_line_type,
                    }
                # ─────────────────────────────────────────────────────────────

                # Mark generation as started
                business.generation_started_at = datetime.utcnow()
                business.website_status = 'generating'
                await db.flush()
                
                # Check if site already exists
                site_result = await db.execute(
                    select(GeneratedSite).where(GeneratedSite.business_id == business_id)
                )
                existing_site = site_result.scalar_one_or_none()
                
                if existing_site and existing_site.status == "completed":
                    # Validate the existing completed site isn't broken (truncated/empty HTML)
                    if _is_html_complete(existing_site.html_content):
                        logger.info(f"Valid completed site already exists for business {business_id}")
                        business.generation_completed_at = datetime.utcnow()
                        business.website_status = 'generated'
                        await db.commit()
                        return {
                            "status": "skipped",
                            "reason": "already_exists",
                            "site_id": str(existing_site.id)
                        }
                    else:
                        logger.warning(
                            f"Existing 'completed' site for {business_id} has broken/truncated HTML "
                            f"({len(existing_site.html_content or '')} bytes). Re-generating."
                        )
                        existing_site.status = "failed"
                        existing_site.error_message = "HTML validation failed: missing hero or nav content"
                        await db.flush()
                
                # Create or update site record
                subdomain = (
                    existing_site.subdomain
                    if existing_site
                    else f"{business.slug}-{str(business.id)[:8]}"
                )
                if existing_site:
                    site = existing_site
                    site.status = "generating"
                else:
                    site = GeneratedSite(
                        business_id=business.id,
                        subdomain=subdomain,
                        status="generating"
                    )
                    db.add(site)
                
                await db.flush()
                await db.refresh(site)
                
                # Generate site using orchestrator
                logger.info(f"Generating site content for {business.name}...")
                orchestrator = CreativeOrchestrator(db)
                
                # Prepare business data for generation
                business_data = {
                    "id": str(business.id),
                    "name": business.name,
                    "category": business.category,
                    "subcategory": business.subcategory,
                    "city": business.city,
                    "state": business.state,
                    "phone": business.phone,
                    "email": business.email,
                    "rating": business.rating,
                    "review_count": business.review_count,
                    "reviews_summary": business.reviews_summary,
                }
                
                # Pass subdomain so architect can generate and save images
                result = await orchestrator.generate_website(
                    business_data,
                    subdomain=subdomain,
                )
                
                # Update site with generated content
                # CRITICAL FIX: Orchestrator returns website content in result["website"]
                website = result.get("website", {})
                html_content = website.get("html")
                css_content = website.get("css")
                js_content = website.get("js")

                # Validate HTML quality before saving — never mark a broken site as completed
                if not _is_html_complete(html_content):
                    html_len = len(html_content or "")
                    raise ValueError(
                        f"Generated HTML failed quality check: {html_len} bytes, "
                        "missing hero or nav content. Site will not be saved."
                    )

                site.html_content = html_content
                site.css_content = css_content
                site.js_content = js_content
                site.brand_analysis = result.get("analysis")
                site.brand_concept = result.get("concepts", {}).get("creative_dna")
                site.design_brief = result.get("design_brief")
                site.status = "completed"
                site.generation_completed_at = datetime.utcnow()
                
                # Update business status
                business.generation_completed_at = datetime.utcnow()
                business.website_status = 'generated'
                
                await db.commit()
                
                logger.info(f"✅ Successfully generated site for business {business_id}")
                return {
                    "status": "completed",
                    "business_id": business_id,
                    "business_name": business.name,
                    "site_id": str(site.id),
                    "subdomain": site.subdomain
                }
                
            except Exception as e:
                logger.error(f"Error generating site for business {business_id}: {str(e)}", exc_info=True)
                await db.rollback()
                
                # Mark site as failed and reset business status so it can be re-queued
                try:
                    if 'site' in locals() and site and site.id:
                        site.status = "failed"
                        site.error_message = str(e)[:500]
                    if 'business' in locals() and business:
                        # Reset to queued so retry_failed_generations can pick it up
                        business.website_status = 'queued'
                        business.generation_started_at = None
                    await db.commit()
                except Exception as db_err:
                    logger.error(f"Failed to persist failure state: {db_err}")
                
                raise  # Re-raise for Celery auto-retry
    
    # Run the async function synchronously
    try:
        return run_async(_generate())
    except Exception as e:
        logger.error(f"Task failed for business {business_id}: {str(e)}")
        raise self.retry(exc=e)


@celery_app.task(bind=True)
def generate_pending_sites(self):
    """
    Generate sites for qualified businesses that don't have sites yet.
    Scheduled task that runs periodically.
    """
    from utils.autopilot_guard import check_autopilot
    guard = check_autopilot("generate_pending_sites")
    if guard:
        return guard

    logger.info("[Celery Task] Starting generate_pending_sites")
    
    async def _generate_pending():
        async with AsyncSessionLocal() as db:
            # Find businesses that need websites
            result = await db.execute(
                select(Business)
                .where(
                    Business.website_status == 'queued',
                    Business.generation_started_at.is_(None)
                )
                .limit(5)  # Generate up to 5 sites per run
            )
            businesses = result.scalars().all()
            
            if not businesses:
                logger.info("No pending sites to generate")
                return {"status": "completed", "sites_queued": 0}
            
            # Queue generation tasks
            tasks_queued = 0
            for business in businesses:
                generate_site_for_business.delay(str(business.id))
                tasks_queued += 1
            
            logger.info(f"Queued {tasks_queued} site generation tasks")
            return {
                "status": "completed",
                "sites_queued": tasks_queued
            }
    
    return run_async(_generate_pending())


@celery_app.task(bind=True)
def publish_completed_sites(self):
    """
    Publish completed sites to production.
    """
    logger.info("[Celery Task] Starting publish_completed_sites")
    
    async def _publish():
        async with AsyncSessionLocal() as db:
            # Find completed sites
            result = await db.execute(
                select(GeneratedSite)
                .where(GeneratedSite.status == "completed")
                .limit(10)
            )
            sites = result.scalars().all()
            
            if not sites:
                logger.info("No completed sites to publish")
                return {"status": "completed", "sites_published": 0}
            
            # Publish each (in real implementation, write to filesystem/CDN)
            published = 0
            for site in sites:
                # TODO: Write to filesystem or CDN
                # For now, just mark as published
                site.status = "published"
                published += 1
            
            await db.commit()
            
            logger.info(f"Published {published} sites")
            return {
                "status": "completed",
                "sites_published": published
            }
    
    return run_async(_publish())


@celery_app.task(bind=True)
def retry_failed_generations(self):
    """
    Retry site generation for failed sites.
    """
    logger.info("[Celery Task] Starting retry_failed_generations")
    
    async def _retry():
        async with AsyncSessionLocal() as db:
            # Find failed sites
            result = await db.execute(
                select(GeneratedSite)
                .where(GeneratedSite.status == "failed")
                .limit(3)  # Retry up to 3 per run
            )
            sites = result.scalars().all()
            
            if not sites:
                logger.info("No failed generations to retry")
                return {"status": "completed", "retries_queued": 0}
            
            # Queue retry tasks
            retries_queued = 0
            for site in sites:
                # Reset site status
                site.status = "generating"
                site.error_message = None

                # Also reset the business so it won't be stuck in 'generating'/'queued' limbo
                biz_result = await db.execute(
                    select(Business).where(Business.id == site.business_id)
                )
                biz = biz_result.scalar_one_or_none()
                if biz:
                    biz.website_status = 'queued'
                    biz.generation_started_at = None
                
                # Queue task
                generate_site_for_business.delay(str(site.business_id))
                retries_queued += 1
            
            await db.commit()
            
            logger.info(f"Queued {retries_queued} retry tasks")
            return {
                "status": "completed",
                "retries_queued": retries_queued
            }
    
    return run_async(_retry())

