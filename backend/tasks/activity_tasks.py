"""
Celery tasks for business activity signal collection.

These tasks run after the main scraping loop and are purely additive —
they enrich existing Business records with activity timestamps that are
then used by the generation pipeline to gate site creation.

Designed to be non-blocking relative to the scrape itself: the scrape
queues these tasks and moves on; they process independently at a rate
that respects ScrapingDog's credit budget.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from celery import shared_task
from sqlalchemy import select, update

from core.database import CeleryAsyncSessionLocal
from models.business import Business
from services.activity.facebook_scraper import FacebookActivityScraper

logger = logging.getLogger(__name__)


# ── Single-business Facebook check ──────────────────────────────────────────

@shared_task(
    name="tasks.activity.fetch_facebook_activity",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    ignore_result=True,
)
def fetch_facebook_activity(self, business_id: str) -> Dict[str, Any]:
    """
    Fetch the last Facebook post date for a single business and persist it.

    Queued by ``HunterService`` after the main scrape loop for any business
    that has a Facebook URL in ``raw_data["social_urls"]["facebook"]`` and
    does not yet have a ``last_facebook_post_date``.

    Args:
        business_id: UUID string of the target Business record.

    Returns:
        Dict with ``status``, ``business_id``, and optionally ``last_post_date``.
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
        last_post_date = await scraper.get_last_post_date(facebook_url)

        if last_post_date is not None:
            await db.execute(
                update(Business)
                .where(Business.id == business_id)
                .values(
                    last_facebook_post_date=last_post_date,
                    updated_at=datetime.now(tz=timezone.utc),
                )
            )
            await db.commit()
            logger.info(
                "Updated last_facebook_post_date for %s (%s): %s",
                business.name,
                business_id,
                last_post_date.date(),
            )
            return {
                "status": "success",
                "business_id": business_id,
                "last_post_date": last_post_date.isoformat(),
            }

        logger.debug(
            "No Facebook post timestamps found for %s (%s)",
            business.name,
            facebook_url,
        )
        return {"status": "no_data", "business_id": business_id}


# ── Batch dispatcher ─────────────────────────────────────────────────────────

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


# ── Internal helpers ─────────────────────────────────────────────────────────

def _extract_facebook_url(business: Business) -> str | None:
    """
    Extract the Facebook page URL from a Business record's raw_data.

    Returns the URL string, or None if not present.
    """
    raw_data = business.raw_data or {}
    social_urls = raw_data.get("social_urls") or {}

    # Outscraper stores it under "facebook" within social_urls
    url = social_urls.get("facebook") or social_urls.get("Facebook")
    if url and "facebook.com" in url:
        return url

    return None
