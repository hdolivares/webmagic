"""
Celery tasks for pre-generation phone validation.

Runs after triple-validation: for each business with no website and no
outreach_channel set, validates phone(s) and sets outreach_channel
(sms | email | call_later). Orchestration only; lookup logic lives in
phone_validation_service.
"""
import asyncio
import logging

from celery_app import celery_app
from sqlalchemy import select, and_, or_
from core.database import AsyncSessionLocal
from core.outreach_enums import OutreachChannel
from models.business import Business
from models.site import GeneratedSite
from services.hunter.phone_validation_service import validate_business_outreach
from services.sms.number_lookup import NumberLookupService

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async code from sync Celery context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# Statuses that mean "confirmed no website" (triple-validated)
_TRIPLE_VERIFIED_STATUSES = ("triple_verified", "confirmed_no_website")


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def run_phone_validation_job(self, limit: int = 50):
    """
    Select triple-validated businesses with outreach_channel NULL and no
    GeneratedSite; run phone validation and persist outreach_channel (and
    optional phone/phone_line_type).

    Args:
        limit: Max businesses to process per run (default 50).

    Returns:
        Dict with processed count and counts by channel.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            # Select: triple-verified, no site yet, outreach_channel not set
            result = await db.execute(
                select(Business)
                .outerjoin(GeneratedSite, Business.id == GeneratedSite.business_id)
                .where(
                    and_(
                        Business.country == "US",
                        or_(
                            Business.website_url.is_(None),
                            Business.website_url == "",
                        ),
                        Business.website_validation_status.in_(_TRIPLE_VERIFIED_STATUSES),
                        Business.outreach_channel.is_(None),
                        GeneratedSite.id.is_(None),
                    )
                )
                .limit(limit)
            )
            businesses = result.unique().scalars().all()

        if not businesses:
            logger.info("Phone validation job: no businesses to process")
            return {"processed": 0, "by_channel": {}}

        lookup_service = NumberLookupService()
        by_channel = {OutreachChannel.SMS.value: 0, OutreachChannel.EMAIL.value: 0, OutreachChannel.CALL_LATER.value: 0}
        processed = 0

        for business in businesses:
            try:
                async with AsyncSessionLocal() as db:
                    # Re-load this business in this session
                    r = await db.execute(select(Business).where(Business.id == business.id))
                    b = r.scalar_one_or_none()
                    if not b:
                        continue
                    result_dto = await validate_business_outreach(b, lookup_service)
                    b.outreach_channel = result_dto.outreach_channel
                    b.phone_validated_at = result_dto.phone_validated_at
                    if result_dto.chosen_phone:
                        b.phone = result_dto.chosen_phone
                        b.phone_line_type = result_dto.phone_line_type
                        b.phone_lookup_at = result_dto.phone_validated_at
                    by_channel[result_dto.outreach_channel] = by_channel.get(result_dto.outreach_channel, 0) + 1
                    processed += 1
                    await db.commit()
            except Exception as e:
                logger.warning("Phone validation failed for business %s: %s", business.id, e)
                continue

        logger.info(
            "Phone validation job: processed %s (%s sms, %s email, %s call_later)",
            processed,
            by_channel.get(OutreachChannel.SMS.value, 0),
            by_channel.get(OutreachChannel.EMAIL.value, 0),
            by_channel.get(OutreachChannel.CALL_LATER.value, 0),
        )
        return {"processed": processed, "by_channel": by_channel}

    return _run_async(_run())
