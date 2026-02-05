"""
Synchronous site generation tasks for Celery.

IMPORTANT: Celery tasks MUST be synchronous functions.
Async functions will be registered but never executed.

This module provides sync wrappers around async generation logic.
"""
from celery import Task
from celery_app import celery_app
from sqlalchemy import select, update
from datetime import datetime
import logging
import asyncio

from core.database import get_db_session_sync, AsyncSessionLocal
from models.business import Business
from models.site import GeneratedSite
from services.creative.orchestrator import CreativeOrchestrator

logger = logging.getLogger(__name__)


def run_async(coro):
    """
    Helper to run async code in sync context.
    Creates new event loop if needed.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10 minutes
    autoretry_for=(Exception,),
    retry_backoff=True
)
def generate_site_for_business(self, business_id: str):
    """
    Generate a website for a specific business (SYNC wrapper).
    
    Args:
        business_id: Business UUID string
        
    Returns:
        Dict with generation result
    """
    logger.info(f"[Celery Task] Starting site generation for business: {business_id}")
    
    async def _generate():
        """Inner async function with actual generation logic."""
        async with AsyncSessionLocal() as db:
            try:
                # Get business
                result = await db.execute(
                    select(Business).where(Business.id == business_id)
                )
                business = result.scalar_one_or_none()
                
                if not business:
                    logger.error(f"Business not found: {business_id}")
                    return {"status": "error", "message": "Business not found"}
                
                # **IDEMPOTENCY CHECK: Verify business still needs a website**
                if business.website_validation_status == 'valid':
                    logger.warning(
                        f"Business {business_id} has valid website: {business.website_url}. "
                        "Skipping generation."
                    )
                    # Update status to reflect it doesn't need generation
                    business.website_status = 'none'
                    business.generation_queued_at = None
                    await db.commit()
                    return {
                        "status": "skipped",
                        "reason": "has_valid_website",
                        "website_url": business.website_url
                    }
                
                # Mark generation as started
                business.generation_started_at = datetime.utcnow()
                business.website_status = 'generating'
                await db.flush()
                
                # Check if site already exists
                site_result = await db.execute(
                    select(GeneratedSite).where(GeneratedSite.business_id == business_id)
                )
                existing_site = site_result.scalar_one_or_none()
                
                if existing_site and existing_site.status == "completed":
                    logger.info(f"Site already exists for business {business_id}")
                    business.generation_completed_at = datetime.utcnow()
                    business.website_status = 'generated'
                    await db.commit()
                    return {
                        "status": "skipped",
                        "reason": "already_exists",
                        "site_id": str(existing_site.id)
                    }
                
                # Create or update site record
                if existing_site:
                    site = existing_site
                    site.status = "generating"
                else:
                    site = GeneratedSite(
                        business_id=business.id,
                        subdomain=f"{business.slug}-{str(business.id)[:8]}",
                        status="generating"
                    )
                    db.add(site)
                
                await db.flush()
                await db.refresh(site)
                
                # Generate site using orchestrator
                logger.info(f"Generating site content for {business.name}...")
                orchestrator = CreativeOrchestrator(db)
                result = await orchestrator.generate_complete_site(business.id)
                
                # Update site with generated content
                site.html_content = result.get("html")
                site.css_content = result.get("css")
                site.js_content = result.get("js")
                site.brand_analysis = result.get("analysis")
                site.brand_concept = result.get("concept")
                site.design_brief = result.get("brief")
                site.status = "completed"
                site.generation_completed_at = datetime.utcnow()
                
                # Update business status
                business.generation_completed_at = datetime.utcnow()
                business.website_status = 'generated'
                
                await db.commit()
                
                logger.info(f"✅ Successfully generated site for business {business_id}")
                return {
                    "status": "completed",
                    "business_id": business_id,
                    "business_name": business.name,
                    "site_id": str(site.id),
                    "subdomain": site.subdomain
                }
                
            except Exception as e:
                logger.error(f"Error generating site for business {business_id}: {str(e)}", exc_info=True)
                await db.rollback()
                
                # Mark site as failed
                if 'site' in locals() and site:
                    site.status = "failed"
                    site.error_message = str(e)
                    await db.commit()
                
                raise  # Re-raise for Celery retry
    
    # Run the async function synchronously
    try:
        return run_async(_generate())
    except Exception as e:
        logger.error(f"Task failed for business {business_id}: {str(e)}")
        raise self.retry(exc=e)


@celery_app.task(bind=True)
def generate_pending_sites(self):
    """
    Generate sites for qualified businesses that don't have sites yet.
    Scheduled task that runs periodically.
    """
    logger.info("[Celery Task] Starting generate_pending_sites")
    
    async def _generate_pending():
        async with AsyncSessionLocal() as db:
            # Find businesses that need websites
            result = await db.execute(
                select(Business)
                .where(
                    Business.website_status == 'queued',
                    Business.generation_started_at.is_(None)
                )
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
    
    return run_async(_generate_pending())


@celery_app.task(bind=True)
def publish_completed_sites(self):
    """
    Publish completed sites to production.
    """
    logger.info("[Celery Task] Starting publish_completed_sites")
    
    async def _publish():
        async with AsyncSessionLocal() as db:
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
                site.status = "published"
                published += 1
            
            await db.commit()
            
            logger.info(f"Published {published} sites")
            return {
                "status": "completed",
                "sites_published": published
            }
    
    return run_async(_publish())


@celery_app.task(bind=True)
def retry_failed_generations(self):
    """
    Retry site generation for failed sites.
    """
    logger.info("[Celery Task] Starting retry_failed_generations")
    
    async def _retry():
        async with AsyncSessionLocal() as db:
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
                site.status = "generating"
                site.error_message = None
                
                # Queue task
                generate_site_for_business.delay(str(site.business_id))
                retries_queued += 1
            
            await db.commit()
            
            logger.info(f"Queued {retries_queued} retry tasks")
            return {
                "status": "completed",
                "retries_queued": retries_queued
            }
    
    return run_async(_retry())

