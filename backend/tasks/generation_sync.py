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

from core.database import get_db_session_sync, CeleryAsyncSessionLocal
from core.outreach_enums import OutreachChannel
from models.business import Business
from models.site import GeneratedSite
from services.activity.analyzer import compute_activity_status
from services.creative.orchestrator import CreativeOrchestrator
from services.hunter.scraper import OutscraperClient
from services.sms.number_lookup import NumberLookupService
from services.sms.phone_validator import PhoneValidator

logger = logging.getLogger(__name__)


# Minimum HTML size (bytes) — based on observed floor of 40 real generations (~22.4 KB min).
# Sites below this are almost certainly truncated.
_MIN_HTML_BYTES = 22_000

# Keywords expected near the top of <body> for a valid full-page generation.
# Both hero AND nav must be present — having only nav can still indicate a truncated page
# (e.g. the header rendered but generation was cut off before the hero section).
_HERO_KEYWORDS = ["hero", 'class="hero', 'id="hero', "class='hero", "id='hero"]
_NAV_KEYWORDS  = [
    "nav-link", "nav-logo", "nav-brand", "nav-content", "nav-menu",
    "hamburger", "menu-toggle",
]


def _is_html_complete(html: str | None) -> bool:
    """
    Return True only if the HTML looks like a full-page generation.

    Checks:
    1. Minimum byte size (_MIN_HTML_BYTES) — derived from observed floor across 40 real sites
    2. Presence of a <body> tag
    3. BOTH hero AND nav content in the first 2000 chars of <body>
       (requiring both prevents falsely passing pages where only nav rendered before truncation)
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
    return has_hero and has_nav


from utils.error_classifier import classify_error as _classify_error


def run_async(coro):
    """
    Helper to run async code in sync Celery task context.

    Uses asyncio.run() which always creates a brand-new event loop and
    closes it cleanly when done.  Combined with CeleryAsyncSessionLocal
    (NullPool), this prevents:
        RuntimeError: Task got Future attached to a different loop
    which occurred because the old pooled asyncpg connections held futures
    tied to a previous event loop that had already been replaced.
    """
    return asyncio.run(coro)


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
        async with CeleryAsyncSessionLocal() as db:
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

                # **SKIP businesses with no phone AND no email** — we have no way to
                # contact them, so generating a site is pointless.
                if not business.phone and not business.email:
                    logger.info(
                        f"Business {business_id} ({business.name}) has no phone and no email. "
                        "Skipping generation — no contact method available."
                    )
                    business.generation_queued_at = None
                    business.generation_started_at = None
                    business.website_status = 'ineligible'
                    await db.commit()
                    return {
                        "status": "skipped",
                        "reason": "no_contact_info",
                        "message": "No phone number or email address; cannot contact business"
                    }

                # **SKIP call_later businesses** (no valid SMS, no email)
                if OutreachChannel.is_call_later(business.outreach_channel):
                    logger.info(
                        f"Business {business_id} is call_later (no SMS, no email). Skipping generation."
                    )
                    # Reset ALL generation tracking fields so this business is
                    # not re-dispatched by generate_pending_sites on every cycle.
                    business.generation_queued_at = None
                    business.generation_started_at = None
                    business.website_status = 'none'
                    await db.commit()
                    return {
                        "status": "skipped",
                        "reason": "call_later",
                        "message": "No valid SMS or email; in call-later queue"
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

                # ── Activity check ────────────────────────────────────────────
                # Skip businesses that are closed, have no verifiable activity,
                # or whose last signals fall outside the configured cutoff windows.
                #
                # business_status falls back to raw_data for records scraped
                # before the model column was populated.
                _raw = business.raw_data or {}
                _biz_status = business.business_status or _raw.get("business_status")
                activity = compute_activity_status(
                    last_review_date=business.last_review_date,
                    last_facebook_post_date=business.last_facebook_post_date,
                    business_status=_biz_status,
                    review_count=business.review_count,
                )
                if not activity.is_eligible:
                    logger.info(
                        "Skipping site generation for %s — %s",
                        business.name,
                        activity.detail,
                    )
                    business.website_status = "ineligible"
                    business.generation_queued_at = None
                    business.generation_started_at = None
                    await db.commit()
                    return {
                        "status": "skipped",
                        "reason": activity.ineligibility_reason,
                        "business_id": business_id,
                        "detail": activity.detail,
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
                        existing_site.error_category = "data_error"
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
                
                # Fetch actual review text if not already cached in raw_data.
                # The standard Outscraper search only stores review COUNT; real text
                # requires a separate reviews API call.  We cap at 10 to balance
                # cost vs. context quality and cache the result in raw_data so
                # retries don't re-fetch.
                reviews_data: list = []
                raw = business.raw_data or {}
                cached_reviews = raw.get("reviews_text")  # set by us after first fetch
                if cached_reviews and isinstance(cached_reviews, list):
                    reviews_data = cached_reviews
                    logger.info(
                        f"[Gen] Using {len(reviews_data)} cached review texts for {business.name}"
                    )
                elif business.gmb_place_id:
                    try:
                        outscraper = OutscraperClient()
                        fetched = await outscraper.fetch_reviews(
                            place_id=business.gmb_place_id,
                            limit=10,
                        )
                        if fetched:
                            reviews_data = fetched
                            # Cache in raw_data to avoid paying for this on retries
                            updated_raw = dict(raw)
                            updated_raw["reviews_text"] = fetched
                            business.raw_data = updated_raw
                            logger.info(
                                f"[Gen] Fetched and cached {len(fetched)} reviews for "
                                f"{business.name} ({business.gmb_place_id})"
                            )
                            # Opportunistically populate last_review_date when it
                            # was not set during scraping (e.g. for older records).
                            if business.last_review_date is None:
                                from services.activity.analyzer import extract_last_review_date
                                last_date = extract_last_review_date(fetched)
                                if last_date is not None:
                                    business.last_review_date = last_date
                                    logger.info(
                                        "[Gen] Set last_review_date=%s for %s",
                                        last_date.date(),
                                        business.name,
                                    )
                    except Exception as rev_err:
                        logger.warning(
                            f"[Gen] Review fetch failed for {business.name} "
                            f"(non-fatal): {rev_err}"
                        )

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
                    "reviews_data": reviews_data,
                }

                # For manually-created businesses, unpack the user's original input
                # into the business_data dict so the orchestrator can run Stage 0.
                manual_input: dict = (business.raw_data or {}).get("manual_input") or {}
                if manual_input or (business.raw_data or {}).get("manual_generation"):
                    business_data["is_manual"] = True
                    business_data["raw_description"] = manual_input.get("description", "")
                    business_data["website_type"] = manual_input.get("website_type", "informational")

                    branding_notes = manual_input.get("branding_notes")
                    branding_images = manual_input.get("branding_images") or []
                    if branding_notes or branding_images:
                        business_data["branding_context"] = {
                            "notes": branding_notes,
                            "images": branding_images,
                        }

                    logger.info(
                        "[Gen] Manual mode for %s — website_type=%s, branding=%s",
                        business.name,
                        business_data["website_type"],
                        "yes" if business_data.get("branding_context") else "no",
                    )

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

                # Persist the exact Gemini prompts used for each image slot so we can
                # review and improve them without having to regenerate the whole site.
                design_brief = result.get("design_brief") or {}
                generated_images = result.get("website", {}).get("generated_images", [])
                if generated_images:
                    design_brief["image_prompts"] = {
                        img["slot"]: img.get("full_prompt")
                        for img in generated_images
                        if isinstance(img, dict) and img.get("slot")
                    }
                site.design_brief = design_brief
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
                    err_category, err_message = _classify_error(e)
                    if 'site' in locals() and site and site.id:
                        site.status = "failed"
                        site.error_message = err_message
                        site.error_category = err_category
                    if 'business' in locals() and business:
                        # Reset to queued so retry_failed_generations can pick it up
                        business.website_status = 'queued'
                        business.generation_started_at = None
                    await db.commit()
                    logger.warning(
                        f"[{err_category}] Generation failed for {business_id}: {err_message[:120]}"
                    )
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
        async with CeleryAsyncSessionLocal() as db:
            # Find businesses that need websites
            result = await db.execute(
                select(Business)
                .where(
                    Business.website_status == 'queued',
                    Business.generation_started_at.is_(None)
                )
                .limit(20)  # Generate up to 20 sites per run
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
        async with CeleryAsyncSessionLocal() as db:
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
        async with CeleryAsyncSessionLocal() as db:
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

