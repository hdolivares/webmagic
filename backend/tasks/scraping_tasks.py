"""
Asynchronous Scraping Tasks.

Purpose:
    Move Outscraper scraping to background Celery tasks with real-time progress.
    Integrates with existing HunterService while adding progress tracking.

Best Practices:
    - Single Responsibility: Each task has one clear purpose
    - Idempotent operations: Safe to retry
    - Comprehensive error handling
    - Progress tracking at each step
    - Proper async/sync boundary handling
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from celery import shared_task
from sqlalchemy import select

from core.database import get_db_session_sync, get_db
from models.scrape_session import ScrapeSession
from models.geo_strategy import GeoStrategy
from services.hunter.hunter_service import HunterService
from services.progress.progress_publisher import ProgressPublisher
from services.progress.redis_service import RedisService

logger = logging.getLogger(__name__)


@shared_task(
    name="tasks.scraping.scrape_zone_async",
    bind=True,
    max_retries=2,
    time_limit=600,  # 10 minutes
    soft_time_limit=570,  # 9.5 minutes soft limit
    acks_late=True  # Only acknowledge after completion
)
def scrape_zone_async(
    self,
    session_id: str,
    city: str,
    state: str,
    category: str,
    country: str = "US",
    limit_per_zone: int = 50,
    zone_id: Optional[str] = None,
    strategy_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Asynchronously scrape a zone using existing HunterService.
    
    This task:
    1. Updates scrape session status
    2. Runs scraping via HunterService
    3. Publishes progress updates via Redis
    4. Handles errors and retries
    
    Args:
        session_id: UUID of scrape session
        city: City name (e.g., "Los Angeles")
        state: State code (e.g., "CA")
        category: Business category (e.g., "plumbers")
        country: Country code (default "US")
        limit_per_zone: Maximum results per zone
        zone_id: Specific zone to scrape (optional)
        strategy_id: Existing strategy UUID (optional)
        
    Returns:
        Summary dictionary with counts and status
    """
    try:
        logger.info(
            f"🚀 Starting async scrape: {city}, {state} - {category} "
            f"(session: {session_id}, zone: {zone_id or 'next'})"
        )
        
        # Initialize services
        redis = RedisService.get_client()
        publisher = ProgressPublisher(redis)
        
        # Update session status and publish start event
        with get_db_session_sync() as db:
            session = db.query(ScrapeSession).filter(
                ScrapeSession.id == session_id
            ).first()
            
            if not session:
                error_msg = f"Session {session_id} not found"
                logger.error(f"❌ {error_msg}")
                return {"error": error_msg, "status": "failed"}
            
            # Update to scraping status
            session.status = "scraping"
            session.started_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"✅ Session {session_id} marked as scraping")
        
        # Publish scraping started event
        publisher.publish_scraping_started(
            session_id=session_id,
            query=f"{category} in {city}, {state}",
            zone_id=zone_id or "auto-select"
        )
        
        # Run the actual scraping (async)
        logger.info("📡 Starting HunterService scraping...")
        scrape_result = _run_scraping(
            session_id=session_id,
            city=city,
            state=state,
            category=category,
            country=country,
            limit_per_zone=limit_per_zone,
            zone_id=zone_id,
            strategy_id=strategy_id,
            publisher=publisher
        )
        
        # Update session with results
        logger.info(f"📊 Scrape result: {scrape_result}")
        
        with get_db_session_sync() as db:
            session = db.query(ScrapeSession).filter(
                ScrapeSession.id == session_id
            ).first()
            
            if not session:
                logger.error(f"❌ Session {session_id} not found for update!")
                return {"error": "Session not found", "status": "failed"}
            
            # Update metrics from scrape result
            session.total_businesses = scrape_result.get("businesses_found", 0)
            session.scraped_businesses = scrape_result.get("businesses_found", 0)
            session.validated_businesses = scrape_result.get("businesses_with_websites", 0)
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(
                f"✅ Session {session_id} completed: "
                f"{session.scraped_businesses} businesses, "
                f"{session.validated_businesses} with websites"
            )
        
        # Publish completion event
        publisher.publish_scrape_complete(
            session_id=session_id,
            summary={
                "total": scrape_result.get("businesses_found", 0),
                "valid": scrape_result.get("businesses_with_websites", 0),
                "invalid": scrape_result.get("businesses_needing_websites", 0),
                "zone_id": scrape_result.get("zone_id", zone_id)
            }
        )
        
        logger.info(f"🎉 Scrape task completed successfully: {session_id}")
        
        return {
            "session_id": session_id,
            "status": "completed",
            "result": scrape_result
        }
        
    except Exception as e:
        logger.error(f"💥 Scrape task failed: {e}", exc_info=True)
        
        # Update session with error
        try:
            with get_db_session_sync() as db:
                session = db.query(ScrapeSession).filter(
                    ScrapeSession.id == session_id
                ).first()
                
                if session:
                    session.status = "failed"
                    session.error_message = str(e)
                    session.completed_at = datetime.utcnow()
                    db.commit()
            
            # Publish error event
            redis = RedisService.get_client()
            publisher = ProgressPublisher(redis)
            publisher.publish_error(
                session_id=session_id,
                error_message=str(e),
                error_type=type(e).__name__,
                recoverable=False
            )
        except Exception as inner_e:
            logger.error(f"Failed to update session error: {inner_e}")
        
        # Retry logic
        try:
            raise self.retry(exc=e, countdown=30)  # Retry after 30 seconds
        except self.MaxRetriesExceededError:
            return {
                "session_id": session_id,
                "status": "failed",
                "error": str(e)
            }


def _run_scraping(
    session_id: str,
    city: str,
    state: str,
    category: str,
    country: str,
    limit_per_zone: int,
    zone_id: Optional[str],
    strategy_id: Optional[str],
    publisher: ProgressPublisher
) -> Dict[str, Any]:
    """
    Execute scraping logic with proper async/sync boundary.
    
    This function handles the transition from synchronous Celery task
    to asynchronous HunterService. It runs an async event loop and
    publishes progress updates.
    
    Args:
        session_id: Scrape session ID
        city: City name
        state: State code
        category: Business category
        country: Country code
        limit_per_zone: Max results per zone
        zone_id: Specific zone ID (optional)
        strategy_id: Strategy UUID (optional)
        publisher: Progress publisher instance
        
    Returns:
        Scraping result dictionary from HunterService
    """
    
    async def _async_scrape():
        """Inner async function for scraping."""
        try:
            # Create async database session using proper context manager
            # FIXED: Use async context manager instead of async for loop
            db_generator = get_db()
            db = await db_generator.__anext__()
            
            try:
                # Initialize HunterService
                hunter = HunterService(db=db)
                
                logger.info(
                    f"🔍 Calling HunterService.scrape_with_intelligent_strategy: "
                    f"city={city}, state={state}, category={category}"
                )
                
                # Run intelligent scraping
                result = await hunter.scrape_with_intelligent_strategy(
                    city=city,
                    state=state,
                    category=category,
                    country=country,
                    limit_per_zone=limit_per_zone,
                    zone_id=zone_id,
                    force_new_strategy=False
                )
                
                logger.info(
                    f"✅ HunterService completed: "
                    f"{result.get('businesses_found', 0)} businesses found"
                )
                
                return result
                
            finally:
                # Properly close the database session
                await db_generator.aclose()
                
        except Exception as e:
            logger.error(f"❌ Async scraping failed: {e}", exc_info=True)
            raise
    
    # Run async function in event loop
    try:
        # Create new event loop for this task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_async_scrape())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"❌ Event loop execution failed: {e}", exc_info=True)
        raise


# =============================================================================
# HELPER TASKS
# =============================================================================

@shared_task(
    name="tasks.scraping.update_session_progress",
    bind=False,
    max_retries=3
)
def update_session_progress(
    session_id: str,
    scraped_count: int,
    validated_count: int
):
    """
    Update scrape session progress metrics.
    
    Called by validation tasks to update progress as
    businesses are validated.
    
    Args:
        session_id: Scrape session UUID
        scraped_count: Total scraped so far
        validated_count: Total validated so far
    """
    try:
        with get_db_session_sync() as db:
            session = db.query(ScrapeSession).filter(
                ScrapeSession.id == session_id
            ).first()
            
            if session:
                session.scraped_businesses = scraped_count
                session.validated_businesses = validated_count
                session.status = "validating"
                db.commit()
                
                logger.debug(
                    f"Updated session {session_id}: "
                    f"scraped={scraped_count}, validated={validated_count}"
                )
    except Exception as e:
        logger.error(f"Failed to update session progress: {e}")
