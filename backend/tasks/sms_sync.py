"""
Synchronous SMS tasks for Celery.

IMPORTANT: Celery tasks MUST be synchronous.
This module provides sync wrappers for SMS tasks.
"""
from celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=180,  # 3 minutes
    time_limit=300  # 5 minutes
)
def process_scheduled_sms_campaigns(self):
    """
    Synchronous SMS campaign processor.
    
    TODO: Implement actual SMS processing logic when needed.
    For now, just logs to prevent worker blocking.
    """
    try:
        logger.info("[SMS] Processing scheduled SMS campaigns...")
        # Actual implementation would go here
        return {"status": "not_implemented", "message": "SMS processing placeholder"}
    except Exception as e:
        logger.error(f"[SMS] Error processing campaigns: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=300,
    time_limit=600
)
def calculate_sms_campaign_stats(self):
    """
    Calculate SMS campaign statistics.
    """
    try:
        logger.info("[SMS] Calculating campaign stats...")
        return {"status": "not_implemented"}
    except Exception as e:
        logger.error(f"[SMS] Error calculating stats: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=600,
    time_limit=900
)
def send_batch_sms_campaigns(self):
    """
    Send batch SMS campaigns.
    """
    try:
        logger.info("[SMS] Sending batch campaigns...")
        return {"status": "not_implemented"}
    except Exception as e:
        logger.error(f"[SMS] Error sending batch: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=30,
    time_limit=60
)
def send_sms_campaign(self, campaign_id: str):
    """
    Send individual SMS campaign.
    """
    try:
        logger.info(f"[SMS] Sending campaign {campaign_id}...")
        return {"status": "not_implemented", "campaign_id": campaign_id}
    except Exception as e:
        logger.error(f"[SMS] Error sending campaign {campaign_id}: {e}")
        return {"status": "error", "message": str(e)}


