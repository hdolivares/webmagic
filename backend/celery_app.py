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
    "tasks.generation_sync",  # Synchronous generation tasks
    "tasks.monitoring_sync",  # Synchronous monitoring tasks (replaces monitoring)
    "tasks.sms_sync",  # Synchronous SMS tasks (replaces sms_campaign_tasks)
    "tasks.campaigns",
])

# Periodic task schedule (using SYNC tasks only)
celery_app.conf.beat_schedule = {
    # Scrape new territories every 6 hours
    "scrape-territories": {
        "task": "tasks.scraping.scrape_pending_territories",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
    # Generate sites for qualified leads every hour (using SYNC task)
    "generate-sites": {
        "task": "tasks.generation_sync.generate_pending_sites",
        "schedule": crontab(minute=0),  # Every hour
    },
    # Send pending campaigns every 30 minutes
    "send-campaigns": {
        "task": "tasks.campaigns.send_pending_campaigns",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    # Process scheduled SMS campaigns every 5 minutes (using SYNC task, reduced frequency)
    "process-scheduled-sms": {
        "task": "tasks.sms_sync.process_scheduled_sms_campaigns",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes (reduced from 1)
    },
    # Calculate SMS stats daily (using SYNC task)
    "calculate-sms-stats": {
        "task": "tasks.sms_sync.calculate_sms_campaign_stats",
        "schedule": crontab(minute=0, hour=2),  # 2 AM daily
    },
    # Clean up old cooldowns daily
    "cleanup-cooldowns": {
        "task": "tasks.scraping.cleanup_expired_cooldowns",
        "schedule": crontab(minute=0, hour=3),  # 3 AM daily
    },
    # Health check every 10 minutes (using SYNC task, reduced frequency)
    "health-check": {
        "task": "tasks.monitoring_sync.health_check",
        "schedule": crontab(minute="*/10"),  # Every 10 minutes (reduced from 5)
    },
}

# Task routes (route tasks to dedicated queues for isolation)
celery_app.conf.task_routes = {
    "tasks.scraping.*": {"queue": "scraping"},
    "tasks.generation.*": {"queue": "generation"},
    "tasks.generation_sync.*": {"queue": "generation"},  # Sync generation tasks
    "tasks.campaigns.*": {"queue": "campaigns"},
    "tasks.sms_sync.*": {"queue": "campaigns"},  # Sync SMS uses campaigns queue
    "tasks.monitoring_sync.*": {"queue": "monitoring"},  # Sync monitoring tasks
}

if __name__ == "__main__":
    celery_app.start()
