"""
Automated site generation tasks.
Handles queuing and generating websites for qualified leads.
"""
from celery import Task
from celery_app import celery_app
from sqlalchemy import select, update
from datetime import datetime
import logging

from core.database import get_db_session
from models.business import Business
from models.site import GeneratedSite
from services.creative.orchestrator import CreativeOrchestrator

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=600  # 10 minutes
)
async def generate_site_for_business(self, business_id: str):
    """
    Generate a website for a specific business.
    
    Args:
        business_id: Business UUID
    """
    logger.info(f"Starting site generation for business: {business_id}")
    
    try:
        async with get_db_session() as db:
            # Get business
            result = await db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                logger.error(f"Business not found: {business_id}")
                return {"status": "error", "message": "Business not found"}
            
            # Check if site already exists
            site_result = await db.execute(
                select(GeneratedSite).where(GeneratedSite.business_id == business_id)
            )
            existing_site = site_result.scalar_one_or_none()
            
            if existing_site and existing_site.status == "completed":
                logger.info(f"Site already exists for business {business_id}")
                return {"status": "skipped", "message": "Site already exists"}
            
            # Create site record
            site = GeneratedSite(
                business_id=business.id,
                subdomain=f"{business.name.lower().replace(' ', '-')}-{business.id[:8]}",
                status="generating",
                generation_started_at=datetime.utcnow()
            )
            db.add(site)
            await db.flush()
            await db.refresh(site)
            
            # Generate site
            orchestrator = CreativeOrchestrator(db)
            result = await orchestrator.generate_complete_site(business.id)
            
            # Update site
            await db.execute(
                update(GeneratedSite)
                .where(GeneratedSite.id == site.id)
                .values(
                    html_content=result["html"],
                    css_content=result.get("css"),
                    js_content=result.get("js"),
                    brand_analysis=result.get("analysis"),
                    brand_concept=result.get("concept"),
                    design_brief=result.get("brief"),
                    status="completed",
                    generation_completed_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            logger.info(f"Successfully generated site for business {business_id}")
            return {
                "status": "completed",
                "business_id": business_id,
                "site_id": str(site.id),
                "subdomain": site.subdomain
            }
            
    except Exception as e:
        logger.error(f"Error generating site for business {business_id}: {str(e)}", exc_info=True)
        
        # Mark as failed
        async with get_db_session() as db:
            await db.execute(
                update(GeneratedSite)
                .where(GeneratedSite.business_id == business_id)
                .values(
                    status="failed",
                    error_message=str(e),
                    updated_at=datetime.utcnow()
                )
            )
            await db.commit()
        
        # Retry
        raise self.retry(exc=e)


@celery_app.task(bind=True)
async def generate_pending_sites(self):
    """
    Generate sites for qualified businesses that don't have sites yet.
    Scheduled task that runs periodically.
    """
    logger.info("Starting generate_pending_sites task")
    
    try:
        async with get_db_session() as db:
            # Find qualified businesses without sites
            result = await db.execute(
                select(Business)
                .where(Business.status == "qualified")
                .outerjoin(GeneratedSite, Business.id == GeneratedSite.business_id)
                .where(GeneratedSite.id == None)
                .limit(5)  # Generate up to 5 sites per run
            )
            businesses = result.scalars().all()
            
            if not businesses:
                logger.info("No pending sites to generate")
                return {"status": "completed", "sites_queued": 0}
            
            # Queue generation tasks
            tasks_queued = 0
            for business in businesses:
                generate_site_for_business.delay(str(business.id))
                tasks_queued += 1
            
            logger.info(f"Queued {tasks_queued} site generation tasks")
            return {
                "status": "completed",
                "sites_queued": tasks_queued
            }
            
    except Exception as e:
        logger.error(f"Error in generate_pending_sites: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True)
async def publish_completed_sites(self):
    """
    Publish completed sites to production.
    """
    logger.info("Starting publish_completed_sites task")
    
    try:
        async with get_db_session() as db:
            # Find completed sites
            result = await db.execute(
                select(GeneratedSite)
                .where(GeneratedSite.status == "completed")
                .limit(10)
            )
            sites = result.scalars().all()
            
            if not sites:
                logger.info("No completed sites to publish")
                return {"status": "completed", "sites_published": 0}
            
            # Publish each (in real implementation, write to filesystem/CDN)
            published = 0
            for site in sites:
                # TODO: Write to filesystem or CDN
                # For now, just mark as published
                await db.execute(
                    update(GeneratedSite)
                    .where(GeneratedSite.id == site.id)
                    .values(status="published", updated_at=datetime.utcnow())
                )
                published += 1
            
            await db.commit()
            
            logger.info(f"Published {published} sites")
            return {
                "status": "completed",
                "sites_published": published
            }
            
    except Exception as e:
        logger.error(f"Error in publish_completed_sites: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True)
async def retry_failed_generations(self):
    """
    Retry site generation for failed sites.
    """
    logger.info("Starting retry_failed_generations task")
    
    try:
        async with get_db_session() as db:
            # Find failed sites
            result = await db.execute(
                select(GeneratedSite)
                .where(GeneratedSite.status == "failed")
                .limit(3)  # Retry up to 3 per run
            )
            sites = result.scalars().all()
            
            if not sites:
                logger.info("No failed generations to retry")
                return {"status": "completed", "retries_queued": 0}
            
            # Queue retry tasks
            retries_queued = 0
            for site in sites:
                # Reset status
                await db.execute(
                    update(GeneratedSite)
                    .where(GeneratedSite.id == site.id)
                    .values(
                        status="generating",
                        error_message=None,
                        updated_at=datetime.utcnow()
                    )
                )
                
                # Queue task
                generate_site_for_business.delay(str(site.business_id))
                retries_queued += 1
            
            await db.commit()
            
            logger.info(f"Queued {retries_queued} retry tasks")
            return {
                "status": "completed",
                "retries_queued": retries_queued
            }
            
    except Exception as e:
        logger.error(f"Error in retry_failed_generations: {str(e)}", exc_info=True)
        raise
