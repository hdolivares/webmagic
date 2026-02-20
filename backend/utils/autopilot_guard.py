"""
Autopilot Guard — shared helper for Celery Beat tasks.

Every automated task calls `check_autopilot()` at the start.
If autopilot is disabled the task returns immediately without doing any work.
If a `needs_generation_count` threshold is provided (for the scraper), the
task also pauses when the pipeline already has enough queued businesses.
"""
import asyncio
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


async def _fetch_autopilot(check_target: bool = False) -> Tuple[bool, int, int]:
    """
    Returns (enabled, target_businesses, current_queued_count).
    current_queued_count is only populated when check_target=True.
    """
    from core.database import get_db_session
    from services.system_settings_service import SystemSettingsService
    from models.business import Business
    from sqlalchemy import select, func

    async with get_db_session() as db:
        settings = await SystemSettingsService.get_autopilot_settings(db)
        enabled: bool = settings["enabled"]
        target: int = settings["target_businesses"]

        queued = 0
        if check_target and enabled:
            # Count businesses ready for generation but not yet generated
            result = await db.execute(
                select(func.count(Business.id)).where(
                    Business.country == "US",
                    Business.website_validation_status.in_(
                        ["confirmed_no_website", "triple_verified"]
                    ),
                    Business.website_status.notin_(["queued", "generated", "published"]),
                )
            )
            queued = result.scalar() or 0

        return enabled, target, queued


def check_autopilot(task_name: str, check_target: bool = False) -> Optional[dict]:
    """
    Synchronous gate for Celery tasks.

    Returns a result dict (task should return this immediately) if autopilot is
    disabled OR the target has been reached.  Returns None if the task should proceed.

    Args:
        task_name:    Name used in log messages.
        check_target: If True, also check the generation queue count vs target
                      (use for the scraping task only).
    """
    try:
        enabled, target, queued = asyncio.run(_fetch_autopilot(check_target))
    except Exception as e:
        # If the DB check itself fails, let the task run (fail open).
        logger.warning(f"[Autopilot] Guard DB check failed for {task_name}: {e} — proceeding")
        return None

    if not enabled:
        logger.info(f"[Autopilot] {task_name} skipped — autopilot is OFF")
        return {"status": "skipped", "reason": "autopilot_disabled"}

    if check_target and queued >= target:
        logger.info(
            f"[Autopilot] {task_name} paused — pipeline has {queued}/{target} businesses queued"
        )
        return {
            "status": "skipped",
            "reason": "target_reached",
            "queued": queued,
            "target": target,
        }

    return None  # All clear — proceed


async def check_autopilot_async(task_name: str, check_target: bool = False) -> Optional[dict]:
    """
    Async version for tasks that are already running in an async context.
    """
    try:
        enabled, target, queued = await _fetch_autopilot(check_target)
    except Exception as e:
        logger.warning(f"[Autopilot] Guard DB check failed for {task_name}: {e} — proceeding")
        return None

    if not enabled:
        logger.info(f"[Autopilot] {task_name} skipped — autopilot is OFF")
        return {"status": "skipped", "reason": "autopilot_disabled"}

    if check_target and queued >= target:
        logger.info(
            f"[Autopilot] {task_name} paused — pipeline has {queued}/{target} businesses queued"
        )
        return {
            "status": "skipped",
            "reason": "target_reached",
            "queued": queued,
            "target": target,
        }

    return None
