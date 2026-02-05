"""
Synchronous monitoring tasks for Celery.

IMPORTANT: Celery tasks MUST be synchronous.
This module provides sync wrappers for monitoring tasks.
"""
from celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=1,
    default_retry_delay=300,  # 5 minutes
    soft_time_limit=60,  # 1 minute soft limit
    time_limit=120  # 2 minutes hard limit
)
def health_check(self):
    """
    Simple health check task (synchronous).
    Just logs that worker is alive.
    """
    try:
        logger.info("[Health Check] Worker is healthy and processing tasks")
        return {"status": "healthy", "worker": self.request.hostname}
    except Exception as e:
        logger.error(f"[Health Check] Error: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(
    bind=True,
    max_retries=1,
    soft_time_limit=300,  # 5 minutes
    time_limit=600  # 10 minutes
)
def cleanup_stuck_tasks(self):
    """
    Placeholder for stuck task cleanup.
    Implement if needed.
    """
    logger.info("[Cleanup] Checking for stuck tasks...")
    return {"status": "not_implemented"}


@celery_app.task(
    bind=True,
    max_retries=1,
    soft_time_limit=600,
    time_limit=900
)
def generate_daily_report(self):
    """
    Placeholder for daily report generation.
    Implement if needed.
    """
    logger.info("[Report] Generating daily report...")
    return {"status": "not_implemented"}


@celery_app.task(
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=600
)
def alert_on_failures(self):
    """
    Placeholder for failure alerting.
    Implement if needed.
    """
    logger.info("[Alert] Checking for failures...")
    return {"status": "not_implemented"}


