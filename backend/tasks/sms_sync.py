"""
Synchronous SMS tasks for Celery.

IMPORTANT: Celery tasks MUST be synchronous.
This module provides sync wrappers for SMS tasks.

Sending guardrails:
- Only sends scheduled campaigns whose scheduled_for <= now (UTC)
- Compliance check (opt-out list + business-hours in recipient local TZ) is
  handled inside CampaignService._create_sms_campaign / send_campaign
- Rate limit: max 10 SMS per Celery Beat tick (every 5 min = 120/hr max)
"""
from celery_app import celery_app
import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)

# Max campaigns to send per scheduled tick to avoid rate-limit spikes
_MAX_PER_RUN = 10


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=180,
    time_limit=300
)
def process_scheduled_sms_campaigns(self):
    """
    Process SMS campaigns that are scheduled and due.

    Runs every 5 minutes via Celery Beat.
    Picks up campaigns with status='scheduled' where scheduled_for <= now (UTC).
    The per-business timezone compliance check (TCPA quiet hours) happens inside
    CampaignService.send_campaign via SMSComplianceService.check_can_send.
    """
    async def _run():
        from utils.autopilot_guard import check_autopilot_async
        guard = await check_autopilot_async("process_scheduled_sms_campaigns")
        if guard:
            return guard

        from core.database import get_db_session
        from sqlalchemy import select
        from models.campaign import Campaign
        from services.pitcher.campaign_service import CampaignService

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC to match DB

        results = {"checked": 0, "sent": 0, "skipped": 0, "failed": 0, "errors": []}

        async with get_db_session() as db:
            stmt = (
                select(Campaign)
                .where(
                    Campaign.channel == "sms",
                    Campaign.status == "scheduled",
                    Campaign.scheduled_for <= now_utc,
                )
                .order_by(Campaign.scheduled_for.asc())
                .limit(_MAX_PER_RUN)
            )
            result = await db.execute(stmt)
            campaigns = result.scalars().all()

            if not campaigns:
                logger.info("[SMS-Sync] No scheduled SMS campaigns due")
                return results

            logger.info(f"[SMS-Sync] Found {len(campaigns)} scheduled SMS campaigns due")
            campaign_service = CampaignService(db)

            for campaign in campaigns:
                results["checked"] += 1
                try:
                    # preferred_only=True: autopilot only sends during 1–5 PM,
                    # 7–9 PM, or 10 AM–12 PM in the business's local timezone.
                    sent = await campaign_service.send_campaign(campaign.id, preferred_only=True)
                    if sent:
                        results["sent"] += 1
                    else:
                        results["skipped"] += 1
                        logger.info(f"[SMS-Sync] Campaign {campaign.id} deferred (outside preferred window)")
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({"campaign_id": str(campaign.id), "error": str(e)})
                    logger.error(f"[SMS-Sync] Campaign {campaign.id} error: {e}", exc_info=True)

                # Small delay between sends — 100 ms → max ~10/sec
                await asyncio.sleep(0.1)

        logger.info(
            f"[SMS-Sync] Done — sent={results['sent']} skipped={results['skipped']} failed={results['failed']}"
        )
        return results

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"[SMS-Sync] process_scheduled_sms_campaigns error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=300,
    time_limit=600
)
def calculate_sms_campaign_stats(self):
    """Calculate SMS campaign statistics (last 30 days)."""
    async def _run():
        from core.database import get_db_session
        from sqlalchemy import select, func
        from models.campaign import Campaign
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)

        async with get_db_session() as db:
            result = await db.execute(
                select(
                    func.count(Campaign.id).label("total_sms"),
                    func.count(Campaign.id).filter(Campaign.status == "delivered").label("delivered"),
                    func.count(Campaign.id).filter(Campaign.status == "failed").label("failed"),
                    func.sum(Campaign.sms_cost).label("total_cost"),
                ).where(
                    Campaign.channel == "sms",
                    Campaign.sent_at >= cutoff,
                )
            )
            row = result.one()
            stats = {
                "period": "last_30_days",
                "total_sms": row.total_sms or 0,
                "delivered": row.delivered or 0,
                "failed": row.failed or 0,
                "total_cost": float(row.total_cost or 0),
                "delivery_rate": (
                    round(row.delivered / row.total_sms * 100, 1) if row.total_sms else 0
                ),
            }
            logger.info(f"[SMS-Sync] Stats: {stats}")
            return stats

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"[SMS-Sync] calculate_sms_campaign_stats error: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=600,
    time_limit=900
)
def send_batch_sms_campaigns(self, campaign_ids: list):
    """Send a specific list of SMS campaign IDs (used for manual batch triggers)."""
    async def _run():
        from core.database import get_db_session
        from services.pitcher.campaign_service import CampaignService

        results = {"total": len(campaign_ids), "sent": 0, "failed": 0, "errors": []}

        async with get_db_session() as db:
            campaign_service = CampaignService(db)
            for cid in campaign_ids:
                try:
                    sent = await campaign_service.send_campaign(UUID(cid))
                    if sent:
                        results["sent"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append({"campaign_id": cid, "error": "Send returned False"})
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({"campaign_id": cid, "error": str(e)})
                    logger.error(f"[SMS-Sync] Batch send error for {cid}: {e}", exc_info=True)
                await asyncio.sleep(0.1)

        logger.info(f"[SMS-Sync] Batch done: {results['sent']}/{results['total']} sent")
        return results

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"[SMS-Sync] send_batch_sms_campaigns error: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=30,
    time_limit=60
)
def send_sms_campaign(self, campaign_id: str):
    """Send a single SMS campaign by ID."""
    async def _run():
        from core.database import get_db_session
        from services.pitcher.campaign_service import CampaignService
        async with get_db_session() as db:
            campaign_service = CampaignService(db)
            sent = await campaign_service.send_campaign(UUID(campaign_id))
            return {"status": "sent" if sent else "failed", "campaign_id": campaign_id}

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.error(f"[SMS-Sync] send_sms_campaign {campaign_id} error: {e}")
        raise self.retry(exc=e)
