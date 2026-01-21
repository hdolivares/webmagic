"""
Celery Tasks for SMS Campaigns.

Background tasks for:
- Sending SMS campaigns asynchronously
- Batch SMS sending for coverage campaigns
- Scheduled SMS delivery

Author: WebMagic Team
Date: January 21, 2026
"""
from celery import shared_task
from sqlalchemy import select
from uuid import UUID
import logging
from typing import List, Dict, Any
from datetime import datetime

from core.database import get_db_context
from models.campaign import Campaign
from services.pitcher.campaign_service import CampaignService
from core.exceptions import ValidationException, ExternalAPIException

logger = logging.getLogger(__name__)


# ============================================================================
# SINGLE SMS CAMPAIGN TASKS
# ============================================================================

@shared_task(
    name="tasks.sms.send_sms_campaign",
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def send_sms_campaign_task(self, campaign_id: str):
    """
    Send a single SMS campaign asynchronously.
    
    Args:
        campaign_id: UUID of campaign to send
    
    Returns:
        Dict with send result
    
    Retries:
        - 3 retries with 5-minute delays
        - Only retries on transient errors (API rate limits, network issues)
        - Does NOT retry on permanent errors (invalid phone, opt-out)
    """
    logger.info(f"[Celery] Sending SMS campaign: {campaign_id}")
    
    async def _send_campaign():
        async with get_db_context() as db:
            campaign_service = CampaignService(db)
            
            try:
                # Send campaign
                result = await campaign_service.send_campaign(UUID(campaign_id))
                
                if result:
                    logger.info(f"[Celery] SMS campaign {campaign_id} sent successfully")
                    return {
                        "status": "success",
                        "campaign_id": campaign_id,
                        "message": "SMS sent successfully"
                    }
                else:
                    logger.error(f"[Celery] SMS campaign {campaign_id} failed")
                    return {
                        "status": "failed",
                        "campaign_id": campaign_id,
                        "message": "SMS send failed"
                    }
            
            except ValidationException as e:
                # Permanent errors - don't retry
                logger.warning(
                    f"[Celery] SMS campaign {campaign_id} validation error: {e}"
                )
                return {
                    "status": "failed",
                    "campaign_id": campaign_id,
                    "error": str(e),
                    "message": "Validation error - not retrying"
                }
            
            except ExternalAPIException as e:
                # Transient API errors - retry
                logger.warning(
                    f"[Celery] SMS campaign {campaign_id} API error: {e} - will retry"
                )
                # Raise for Celery retry mechanism
                raise self.retry(exc=e)
            
            except Exception as e:
                # Unknown errors - log and fail
                logger.error(
                    f"[Celery] SMS campaign {campaign_id} unexpected error: {e}",
                    exc_info=True
                )
                return {
                    "status": "failed",
                    "campaign_id": campaign_id,
                    "error": str(e),
                    "message": "Unexpected error"
                }
    
    # Run async function in event loop
    import asyncio
    return asyncio.run(_send_campaign())


# ============================================================================
# BATCH SMS CAMPAIGN TASKS
# ============================================================================

@shared_task(
    name="tasks.sms.send_batch_sms_campaigns",
    bind=True
)
def send_batch_sms_campaigns_task(self, campaign_ids: List[str]):
    """
    Send multiple SMS campaigns in batch.
    
    Used for coverage campaigns where we send SMS to many businesses.
    Includes rate limiting and error handling.
    
    Args:
        campaign_ids: List of campaign UUIDs to send
    
    Returns:
        Dict with batch send results
    """
    logger.info(f"[Celery] Starting batch SMS send: {len(campaign_ids)} campaigns")
    
    async def _send_batch():
        results = {
            "total": len(campaign_ids),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        async with get_db_context() as db:
            campaign_service = CampaignService(db)
            
            for campaign_id in campaign_ids:
                try:
                    result = await campaign_service.send_campaign(UUID(campaign_id))
                    
                    if result:
                        results["sent"] += 1
                        logger.info(f"[Celery] Batch SMS: {campaign_id} sent")
                    else:
                        results["failed"] += 1
                        results["errors"].append({
                            "campaign_id": campaign_id,
                            "error": "Send failed"
                        })
                
                except ValidationException as e:
                    # Permanent error - skip
                    results["failed"] += 1
                    results["errors"].append({
                        "campaign_id": campaign_id,
                        "error": f"Validation: {str(e)}"
                    })
                    logger.warning(
                        f"[Celery] Batch SMS: {campaign_id} validation error: {e}"
                    )
                
                except Exception as e:
                    # Unexpected error - log and continue
                    results["failed"] += 1
                    results["errors"].append({
                        "campaign_id": campaign_id,
                        "error": f"Unexpected: {str(e)}"
                    })
                    logger.error(
                        f"[Celery] Batch SMS: {campaign_id} error: {e}",
                        exc_info=True
                    )
                
                # Rate limiting: Small delay between sends to avoid API throttling
                # Twilio has rate limits (messaging service-dependent, typically 1000/sec)
                import asyncio
                await asyncio.sleep(0.1)  # 100ms delay = max 10 SMS/sec
        
        logger.info(
            f"[Celery] Batch SMS complete: "
            f"{results['sent']} sent, {results['failed']} failed"
        )
        
        return results
    
    # Run async function in event loop
    import asyncio
    return asyncio.run(_send_batch())


# ============================================================================
# SCHEDULED SMS CAMPAIGN TASKS
# ============================================================================

@shared_task(
    name="tasks.sms.process_scheduled_sms_campaigns",
    bind=True
)
def process_scheduled_sms_campaigns_task(self):
    """
    Process scheduled SMS campaigns that are due to be sent.
    
    This task runs periodically (e.g., every minute) via Celery Beat.
    It finds campaigns with `scheduled_for <= now` and sends them.
    
    Returns:
        Dict with processing results
    """
    logger.info("[Celery] Processing scheduled SMS campaigns")
    
    async def _process_scheduled():
        results = {
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        async with get_db_context() as db:
            # Find scheduled SMS campaigns that are due
            result = await db.execute(
                select(Campaign).where(
                    Campaign.channel == "sms",
                    Campaign.status == "scheduled",
                    Campaign.scheduled_for <= datetime.utcnow()
                )
            )
            scheduled_campaigns = result.scalars().all()
            
            if not scheduled_campaigns:
                logger.info("[Celery] No scheduled SMS campaigns due")
                return results
            
            logger.info(
                f"[Celery] Found {len(scheduled_campaigns)} scheduled SMS campaigns"
            )
            
            campaign_service = CampaignService(db)
            
            for campaign in scheduled_campaigns:
                results["processed"] += 1
                
                try:
                    send_result = await campaign_service.send_campaign(campaign.id)
                    
                    if send_result:
                        results["sent"] += 1
                        logger.info(
                            f"[Celery] Scheduled SMS sent: {campaign.id}"
                        )
                    else:
                        results["failed"] += 1
                        results["errors"].append({
                            "campaign_id": str(campaign.id),
                            "error": "Send failed"
                        })
                
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "campaign_id": str(campaign.id),
                        "error": str(e)
                    })
                    logger.error(
                        f"[Celery] Scheduled SMS error for {campaign.id}: {e}",
                        exc_info=True
                    )
            
            logger.info(
                f"[Celery] Scheduled SMS processing complete: "
                f"{results['sent']} sent, {results['failed']} failed"
            )
            
            return results
    
    # Run async function in event loop
    import asyncio
    return asyncio.run(_process_scheduled())


# ============================================================================
# SMS CAMPAIGN STATISTICS TASKS
# ============================================================================

@shared_task(
    name="tasks.sms.calculate_sms_campaign_stats",
    bind=True
)
def calculate_sms_campaign_stats_task(self):
    """
    Calculate SMS campaign statistics for reporting.
    
    This task runs periodically (e.g., daily) to aggregate:
    - Total SMS sent
    - Total cost
    - Delivery rates
    - Opt-out rates
    
    Returns:
        Dict with calculated statistics
    """
    logger.info("[Celery] Calculating SMS campaign statistics")
    
    async def _calculate_stats():
        from sqlalchemy import func
        
        async with get_db_context() as db:
            # SMS campaigns in last 30 days
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            result = await db.execute(
                select(
                    func.count(Campaign.id).label("total_sms"),
                    func.count(Campaign.id).filter(
                        Campaign.status == "delivered"
                    ).label("delivered"),
                    func.count(Campaign.id).filter(
                        Campaign.status == "failed"
                    ).label("failed"),
                    func.sum(Campaign.sms_cost).label("total_cost"),
                    func.sum(Campaign.sms_segments).label("total_segments")
                ).where(
                    Campaign.channel == "sms",
                    Campaign.sent_at >= cutoff_date
                )
            )
            
            stats = result.one()
            
            calculated_stats = {
                "period": "last_30_days",
                "total_sms": stats.total_sms or 0,
                "delivered": stats.delivered or 0,
                "failed": stats.failed or 0,
                "total_cost": float(stats.total_cost or 0),
                "total_segments": stats.total_segments or 0,
                "delivery_rate": (
                    (stats.delivered / stats.total_sms * 100)
                    if stats.total_sms > 0
                    else 0
                )
            }
            
            logger.info(f"[Celery] SMS stats calculated: {calculated_stats}")
            
            return calculated_stats
    
    # Run async function in event loop
    import asyncio
    return asyncio.run(_calculate_stats())

