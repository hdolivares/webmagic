"""
Celery application configuration.
Handles background task processing for WebMagic automation.
"""
from celery import Celery
from celery.schedules import crontab
from core.config import get_settings

settings = get_settings()

# Initialize Celery app
celery_app = Celery(
    "webmagic",
    broker=settings.CELERY_BROKER_URL or settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND or settings.REDIS_URL,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    "tasks.scraping",
    "tasks.generation",
    "tasks.generation_sync",  # NEW: Synchronous generation tasks
    "tasks.campaigns",
    "tasks.sms_campaign_tasks",  # SMS campaigns (Phase 7)
    "tasks.monitoring",
])

# Periodic task schedule
celery_app.conf.beat_schedule = {
    # Scrape new territories every 6 hours
    "scrape-territories": {
        "task": "tasks.scraping.scrape_pending_territories",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
    # Generate sites for qualified leads every hour
    "generate-sites": {
        "task": "tasks.generation.generate_pending_sites",
        "schedule": crontab(minute=0),  # Every hour
    },
    # Send pending campaigns every 30 minutes
    "send-campaigns": {
        "task": "tasks.campaigns.send_pending_campaigns",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    # Process scheduled SMS campaigns every minute
    "process-scheduled-sms": {
        "task": "tasks.sms.process_scheduled_sms_campaigns",
        "schedule": crontab(minute="*"),  # Every minute
    },
    # Calculate SMS stats daily
    "calculate-sms-stats": {
        "task": "tasks.sms.calculate_sms_campaign_stats",
        "schedule": crontab(minute=0, hour=2),  # 2 AM daily
    },
    # Clean up old cooldowns daily
    "cleanup-cooldowns": {
        "task": "tasks.scraping.cleanup_expired_cooldowns",
        "schedule": crontab(minute=0, hour=3),  # 3 AM daily
    },
    # Health check every 5 minutes
    "health-check": {
        "task": "tasks.monitoring.health_check",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}

# Task routes (optional: route specific tasks to specific queues)
celery_app.conf.task_routes = {
    "tasks.scraping.*": {"queue": "scraping"},
    "tasks.generation.*": {"queue": "generation"},
    "tasks.generation_sync.*": {"queue": "generation"},  # NEW: Sync tasks use same queue
    "tasks.campaigns.*": {"queue": "campaigns"},
    "tasks.sms.*": {"queue": "campaigns"},  # SMS uses same queue as campaigns
    "tasks.monitoring.*": {"queue": "monitoring"},
}

if __name__ == "__main__":
    celery_app.start()
