"""
Celery tasks for business activity signal collection and contact enrichment.

These tasks run after the main scraping loop and are purely additive —
they enrich existing Business records with signals fetched from Facebook:

    - last_facebook_post_date  (activity gate for site generation)
    - phone                    (only written when currently NULL)
    - email                    (only written when currently NULL)
    - website_url              (only written when currently NULL; triggers re-validation)

A full audit record is always written to ``raw_data["facebook_enrichment"]``
regardless of whether any main fields were updated.

Designed to be non-blocking relative to the scrape itself: the scrape
queues these tasks and moves on; they process independently at a rate
that respects ScrapingDog's credit budget.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from celery import shared_task
from sqlalchemy import select

from core.database import CeleryAsyncSessionLocal
from models.business import Business
from services.activity.facebook_scraper import (
    FacebookActivityScraper,
    FacebookPageData,
    extract_facebook_url_from_raw,
)

logger = logging.getLogger(__name__)


# ── Single-business Facebook enrichment ──────────────────────────────────────

@shared_task(
    name="tasks.activity.fetch_facebook_activity",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    ignore_result=True,
)
def fetch_facebook_activity(self, business_id: str) -> Dict[str, Any]:
    """
    Scrape the Facebook page for a single business and persist all signals.

    Queued by ``HunterService`` after the main scrape loop for any business
    that has a Facebook URL in its ``raw_data`` and does not yet have a
    ``last_facebook_post_date``.

    Persists the following fields (non-destructively — existing values are
    never overwritten):
        - ``last_facebook_post_date``
        - ``phone``
        - ``email``
        - ``website_url`` (also resets ``website_validation_status`` to "pending")

    Always writes an audit record to ``raw_data["facebook_enrichment"]``.

    Args:
        business_id: UUID string of the target Business record.

    Returns:
        Dict with ``status``, ``business_id``, and ``enriched`` field list.
    """
    return asyncio.run(_fetch_facebook_activity_async(business_id))


async def _fetch_facebook_activity_async(business_id: str) -> Dict[str, Any]:
    async with CeleryAsyncSessionLocal() as db:
        result = await db.execute(
            select(Business).where(Business.id == business_id)
        )
        business = result.scalar_one_or_none()

        if not business:
            logger.error("fetch_facebook_activity: Business not found: %s", business_id)
            return {"status": "error", "business_id": business_id, "error": "not_found"}

        facebook_url = _extract_facebook_url(business)
        if not facebook_url:
            return {"status": "skipped", "business_id": business_id, "reason": "no_facebook_url"}

        scraper = FacebookActivityScraper()
        data = await scraper.scrape_page(facebook_url)

        enriched = _apply_enrichment(business, data, facebook_url)

        if enriched:
            await db.commit()
            logger.info(
                "Facebook enrichment for %s (%s): updated %s",
                business.name,
                business_id,
                ", ".join(enriched),
            )
        else:
            logger.debug(
                "No enrichment data found for %s (%s) at %s",
                business.name,
                business_id,
                facebook_url,
            )

        return {
            "status": "success" if enriched else "no_data",
            "business_id": business_id,
            "enriched": enriched,
        }


# ── Batch dispatcher ──────────────────────────────────────────────────────────

@shared_task(
    name="tasks.activity.batch_fetch_facebook_activity",
    bind=True,
    ignore_result=True,
)
def batch_fetch_facebook_activity(
    self, business_ids: List[str]
) -> Dict[str, Any]:
    """
    Dispatch individual ``fetch_facebook_activity`` tasks for a list of businesses.

    Designed to be called by ``HunterService`` at the end of a scrape batch.
    Each individual task handles its own error handling and retries so a
    single failure does not block the rest of the batch.
    """
    queued = 0
    failed = 0

    for business_id in business_ids:
        try:
            fetch_facebook_activity.delay(business_id)
            queued += 1
        except Exception as exc:
            logger.error(
                "Failed to queue fetch_facebook_activity for %s: %s",
                business_id,
                exc,
            )
            failed += 1

    logger.info(
        "batch_fetch_facebook_activity: queued=%d, failed=%d",
        queued,
        failed,
    )
    return {"queued": queued, "failed": failed, "total": len(business_ids)}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_facebook_url(business: Business) -> Optional[str]:
    """
    Extract the Facebook page URL from a Business record's raw_data.

    Delegates to ``extract_facebook_url_from_raw`` which checks both the
    explicit social_urls map and the ScrapingDog organic search results.
    """
    return extract_facebook_url_from_raw(business.raw_data or {})


def _apply_enrichment(
    business: Business,
    data: FacebookPageData,
    facebook_url: str,
) -> List[str]:
    """
    Apply ``FacebookPageData`` signals to the Business ORM object in-place.

    Rules:
    - Each main field is only written when the Business field is currently
      empty (``None`` or empty string), preserving validated data.
    - ``website_url`` enrichment also resets ``website_validation_status``
      to "pending" so the existing validator picks it up automatically.
    - An audit record is always written to ``raw_data["facebook_enrichment"]``
      so we can see what Facebook returned even when no fields changed.

    Returns:
        List of field names that were actually updated on the Business record.
    """
    now = datetime.now(tz=timezone.utc)
    updated: List[str] = []

    if data.last_post_date and not business.last_facebook_post_date:
        business.last_facebook_post_date = data.last_post_date
        updated.append("last_facebook_post_date")

    if data.phone and not business.phone:
        business.phone = data.phone
        updated.append("phone")

    if data.email and not business.email:
        business.email = data.email
        updated.append("email")

    if data.website_url and not business.website_url:
        business.website_url = data.website_url
        business.website_validation_status = "pending"
        updated.append("website_url")

    # Always persist an audit record so we know the page was checked.
    enrichment_record = {
        "scraped_at": now.isoformat(),
        "facebook_url": facebook_url,
        "last_post_date": data.last_post_date.isoformat() if data.last_post_date else None,
        "phone": data.phone,
        "email": data.email,
        "website": data.website_url,
    }
    business.raw_data = {**(business.raw_data or {}), "facebook_enrichment": enrichment_record}

    if updated:
        business.updated_at = now

    return updated
