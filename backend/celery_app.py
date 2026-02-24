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
    worker_max_tasks_per_child=100,  # Reduced from 1000 to prevent memory buildup
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # Keep results for 1 hour
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    "tasks.scraping",  # Legacy scraping tasks
    "tasks.scraping_tasks",  # Phase 2: Async scraping with progress
    "tasks.generation",
    "tasks.generation_sync",  # Synchronous generation tasks
    "tasks.monitoring_sync",  # Synchronous monitoring tasks (replaces monitoring)
    "tasks.sms_sync",  # Synchronous SMS tasks (replaces sms_campaign_tasks)
    "tasks.campaigns",
    "tasks.validation_tasks",  # Playwright website validation (old system)
    "tasks.validation_tasks_enhanced",  # Enhanced V2 validation with metadata
    "tasks.discovery_tasks",  # Website discovery pipeline (ScrapingDog)
    "tasks.ticket_tasks",  # Support ticket AI processing
    "tasks.abandoned_cart_tasks",  # Abandoned cart recovery (15min window, 24h coupon)
])

# Periodic task schedule (using SYNC tasks only)
# All times are UTC. Compliance / quiet-hours enforcement is handled per-business
# inside SMSComplianceService using the business's actual US state timezone.
celery_app.conf.beat_schedule = {
    # ── Stage 1: Scrape new territories every 6 hours ───────────────────────
    "scrape-territories": {
        "task": "tasks.scraping.scrape_pending_territories",
        "schedule": crontab(minute=0, hour="*/6"),
    },

    # ── Stage 2: Generate sites for qualified leads every hour ───────────────
    # Re-enabled: website detection pipeline is stable (ScrapingDog + LLM country check)
    "generate-sites": {
        "task": "tasks.generation_sync.generate_pending_sites",
        "schedule": crontab(minute=0),  # Top of every hour
    },

    # ── Stage 3: Auto-create campaigns for newly published sites ─────────────
    # Runs every 30 min; picks published sites that don't yet have a campaign
    "create-campaigns-for-new-sites": {
        "task": "tasks.campaigns.create_campaigns_for_new_sites",
        "schedule": crontab(minute="*/30"),
    },

    # ── Stage 4a: Send pending (non-scheduled) campaigns every 30 minutes ───
    # Only fires campaigns where scheduled_for IS NULL or scheduled_for <= now
    "send-campaigns": {
        "task": "tasks.campaigns.send_pending_campaigns",
        "schedule": crontab(minute="*/30"),
    },

    # ── Stage 4b: Process time-scheduled SMS campaigns every 5 minutes ──────
    # Picks campaigns with status='scheduled' and scheduled_for <= now (UTC).
    # TCPA quiet-hours are enforced per recipient local timezone inside the task.
    # Best-practice send windows (Tue–Thu, 1–5 PM or 7–9 PM local) are set at
    # campaign creation time via scheduled_for; this task just executes them.
    "process-scheduled-sms": {
        "task": "tasks.sms_sync.process_scheduled_sms_campaigns",
        "schedule": crontab(minute="*/5"),
    },

    # ── Maintenance ──────────────────────────────────────────────────────────
    "calculate-sms-stats": {
        "task": "tasks.sms_sync.calculate_sms_campaign_stats",
        "schedule": crontab(minute=0, hour=2),  # 2 AM UTC daily
    },
    "cleanup-cooldowns": {
        "task": "tasks.scraping.cleanup_expired_cooldowns",
        "schedule": crontab(minute=0, hour=3),  # 3 AM UTC daily
    },
    "health-check": {
        "task": "tasks.monitoring_sync.health_check",
        "schedule": crontab(minute="*/10"),
    },

    # Abandoned cart recovery: every 5 min; daily cleanup of old abandoned sessions
    "check-abandoned-carts": {
        "task": "tasks.abandoned_cart_tasks.check_abandoned_carts",
        "schedule": crontab(minute="*/5"),
    },
    "cleanup-old-abandoned-carts": {
        "task": "tasks.abandoned_cart_tasks.cleanup_old_abandoned_carts",
        "schedule": crontab(minute=0, hour=3),
    },
}

# Task routes (route tasks to dedicated queues for isolation)
# Phase 2: Separate queues for scraping → validation → discovery flow
celery_app.conf.task_routes = {
    # Queue 1: Outscraper scraping (I/O bound, slow external API)
    "tasks.scraping.*": {"queue": "scraping", "priority": 5},
    "tasks.scraping_tasks.*": {"queue": "scraping", "priority": 7},  # Phase 2 async scraping (higher priority)
    
    # Queue 2: URL validation (CPU + I/O bound, Playwright + LLM)
    "tasks.validation_tasks.*": {"queue": "validation", "priority": 6},
    "tasks.validation_tasks_enhanced.*": {"queue": "validation", "priority": 8},  # V2 validation (higher priority)
    
    # Queue 3: Website discovery (I/O bound, ScrapingDog + LLM)
    "tasks.discovery_tasks.*": {"queue": "discovery", "priority": 6},
    
    # Other queues (unchanged)
    "tasks.generation.*": {"queue": "generation"},
    "tasks.generation_sync.*": {"queue": "generation"},
    "tasks.campaigns.*": {"queue": "campaigns"},
    "tasks.sms_sync.*": {"queue": "campaigns"},
    "tasks.monitoring_sync.*": {"queue": "monitoring"},
    "tasks.ticket_tasks.*": {"queue": "celery"},  # Default queue, low latency
    "tasks.abandoned_cart_tasks.*": {"queue": "celery"},
}

# Enable priority support (0-10, 10 = highest)
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5

if __name__ == "__main__":
    celery_app.start()
