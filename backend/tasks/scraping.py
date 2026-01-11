"""
Automated scraping tasks.
Handles territory scraping, cooldown management, and lead qualification.
"""
from celery import Task
from celery_app import celery_app
from sqlalchemy import select, update
from datetime import datetime, timedelta
import logging

from core.database import get_db_session
from models.coverage import CoverageGrid
from models.business import Business
from services.hunter.hunter_service import HunterService

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session handling."""
    
    _db_session = None
    
    @property
    def db_session(self):
        if self._db_session is None:
            self._db_session = get_db_session()
        return self._db_session


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
async def scrape_territory(self, grid_id: str):
    """
    Scrape a specific territory grid.
    
    Args:
        grid_id: Coverage grid UUID
    """
    logger.info(f"Starting scrape for grid: {grid_id}")
    
    try:
        async with get_db_session() as db:
            # Get grid
            result = await db.execute(
                select(CoverageGrid).where(CoverageGrid.id == grid_id)
            )
            grid = result.scalar_one_or_none()
            
            if not grid:
                logger.error(f"Grid not found: {grid_id}")
                return {"status": "error", "message": "Grid not found"}
            
            # Check if on cooldown
            if grid.cooldown_until and grid.cooldown_until > datetime.utcnow():
                logger.info(f"Grid {grid_id} is on cooldown until {grid.cooldown_until}")
                return {"status": "skipped", "message": "On cooldown"}
            
            # Update status
            await db.execute(
                update(CoverageGrid)
                .where(CoverageGrid.id == grid_id)
                .values(status="processing")
            )
            await db.commit()
            
            # Run scrape
            hunter_service = HunterService(db)
            results = await hunter_service.scrape_and_save(
                location=grid.location_query,
                category=grid.category
            )
            
            # Update grid
            await db.execute(
                update(CoverageGrid)
                .where(CoverageGrid.id == grid_id)
                .values(
                    status="completed",
                    scraped_at=datetime.utcnow(),
                    cooldown_until=datetime.utcnow() + timedelta(days=30),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            logger.info(f"Scraped {results['total_scraped']} businesses for grid {grid_id}")
            return {
                "status": "completed",
                "grid_id": grid_id,
                "results": results
            }
            
    except Exception as e:
        logger.error(f"Error scraping grid {grid_id}: {str(e)}", exc_info=True)
        
        # Mark as failed
        async with get_db_session() as db:
            await db.execute(
                update(CoverageGrid)
                .where(CoverageGrid.id == grid_id)
                .values(status="failed", updated_at=datetime.utcnow())
            )
            await db.commit()
        
        # Retry
        raise self.retry(exc=e)


@celery_app.task(bind=True, base=DatabaseTask)
async def scrape_pending_territories(self):
    """
    Scrape all pending territories that are not on cooldown.
    Scheduled task that runs periodically.
    """
    logger.info("Starting scrape_pending_territories task")
    
    try:
        async with get_db_session() as db:
            # Find pending grids not on cooldown
            result = await db.execute(
                select(CoverageGrid)
                .where(
                    CoverageGrid.status == "pending",
                    (CoverageGrid.cooldown_until == None) | 
                    (CoverageGrid.cooldown_until < datetime.utcnow())
                )
                .limit(10)  # Scrape up to 10 territories per run
            )
            grids = result.scalars().all()
            
            if not grids:
                logger.info("No pending territories to scrape")
                return {"status": "completed", "territories_queued": 0}
            
            # Queue scraping tasks
            tasks_queued = 0
            for grid in grids:
                scrape_territory.delay(str(grid.id))
                tasks_queued += 1
            
            logger.info(f"Queued {tasks_queued} territory scraping tasks")
            return {
                "status": "completed",
                "territories_queued": tasks_queued
            }
            
    except Exception as e:
        logger.error(f"Error in scrape_pending_territories: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, base=DatabaseTask)
async def cleanup_expired_cooldowns(self):
    """
    Reset cooldowns for territories that are ready to be scraped again.
    """
    logger.info("Starting cleanup_expired_cooldowns task")
    
    try:
        async with get_db_session() as db:
            # Find grids with expired cooldowns
            result = await db.execute(
                select(CoverageGrid)
                .where(
                    CoverageGrid.cooldown_until < datetime.utcnow(),
                    CoverageGrid.status == "completed"
                )
            )
            grids = result.scalars().all()
            
            # Reset to pending
            count = 0
            for grid in grids:
                await db.execute(
                    update(CoverageGrid)
                    .where(CoverageGrid.id == grid.id)
                    .values(
                        status="pending",
                        cooldown_until=None,
                        updated_at=datetime.utcnow()
                    )
                )
                count += 1
            
            await db.commit()
            
            logger.info(f"Reset {count} territories to pending status")
            return {"status": "completed", "territories_reset": count}
            
    except Exception as e:
        logger.error(f"Error in cleanup_expired_cooldowns: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, base=DatabaseTask)
async def qualify_new_leads(self):
    """
    Qualify recently scraped businesses.
    """
    logger.info("Starting qualify_new_leads task")
    
    try:
        async with get_db_session() as db:
            # Find scraped businesses
            result = await db.execute(
                select(Business)
                .where(Business.status == "scraped")
                .limit(100)
            )
            businesses = result.scalars().all()
            
            if not businesses:
                logger.info("No new leads to qualify")
                return {"status": "completed", "qualified": 0, "disqualified": 0}
            
            # Qualify each
            from services.hunter.filters import qualify_lead
            qualified = 0
            disqualified = 0
            
            for business in businesses:
                is_qualified, reason = qualify_lead(business)
                
                if is_qualified:
                    await db.execute(
                        update(Business)
                        .where(Business.id == business.id)
                        .values(status="qualified", updated_at=datetime.utcnow())
                    )
                    qualified += 1
                else:
                    await db.execute(
                        update(Business)
                        .where(Business.id == business.id)
                        .values(
                            status="disqualified",
                            disqualified_reason=reason,
                            updated_at=datetime.utcnow()
                        )
                    )
                    disqualified += 1
            
            await db.commit()
            
            logger.info(f"Qualified {qualified}, disqualified {disqualified} leads")
            return {
                "status": "completed",
                "qualified": qualified,
                "disqualified": disqualified
            }
            
    except Exception as e:
        logger.error(f"Error in qualify_new_leads: {str(e)}", exc_info=True)
        raise
