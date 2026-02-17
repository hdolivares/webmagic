"""
Automated site generation tasks.
Handles queuing and generating websites for qualified leads.

Refactored for best practices:
- Modular helper functions (generation_helpers.py)
- Clear separation of concerns
- Constants instead of magic strings
- Single responsibility per function
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
from tasks.generation_helpers import (
    build_site_subdomain,
    build_site_url,
    get_business_by_id,
    get_existing_site,
    create_short_link_for_site,
    build_site_result_dict,
    SITE_STATUS_GENERATING,
    SITE_STATUS_COMPLETED,
    SITE_STATUS_FAILED,
)

logger = logging.getLogger(__name__)


async def _validate_business(db, business_id: str) -> Business:
    """
    Validate that business exists.
    
    Args:
        db: Database session
        business_id: Business UUID string
        
    Returns:
        Business instance
        
    Raises:
        ValueError: If business not found
    """
    business = await get_business_by_id(db, business_id)
    if not business:
        logger.error(f"Business not found: {business_id}")
        raise ValueError(f"Business {business_id} not found")
    return business


async def _check_existing_site(db, business_id: str) -> bool:
    """
    Check if business already has a completed site.
    
    Args:
        db: Database session
        business_id: Business UUID string
        
    Returns:
        True if site already exists and is completed
    """
    existing_site = await get_existing_site(db, business_id)
    if existing_site and existing_site.status == SITE_STATUS_COMPLETED:
        logger.info(f"Site already exists for business {business_id}")
        return True
    return False


async def _create_site_record(db, business: Business) -> GeneratedSite:
    """
    Create initial site record in database.
    
    Args:
        db: Database session
        business: Business instance
        
    Returns:
        Created GeneratedSite instance
    """
    subdomain = build_site_subdomain(business.name, business.city, str(business.id))
    
    site = GeneratedSite(
        business_id=business.id,
        subdomain=subdomain,
        status=SITE_STATUS_GENERATING,
        generation_started_at=datetime.utcnow()
    )
    db.add(site)
    await db.flush()
    await db.refresh(site)
    
    return site


async def _generate_site_content(db, business_id: str) -> dict:
    """
    Generate site content using Creative Orchestrator.
    
    Args:
        db: Database session
        business_id: Business UUID string
        
    Returns:
        Dictionary with generated HTML, CSS, JS, and metadata
    """
    orchestrator = CreativeOrchestrator(db)
    return await orchestrator.generate_complete_site(business_id)


async def _update_site_with_content_and_url(
    db,
    site: GeneratedSite,
    content: dict,
    short_url: str
) -> None:
    """
    Update site record with generated content and short link.
    
    Args:
        db: Database session
        site: GeneratedSite instance
        content: Generated content dictionary
        short_url: Short URL for the site
    """
    await db.execute(
        update(GeneratedSite)
        .where(GeneratedSite.id == site.id)
        .values(
            html_content=content["html"],
            css_content=content.get("css"),
            js_content=content.get("js"),
            brand_analysis=content.get("analysis"),
            brand_concept=content.get("concept"),
            design_brief=content.get("brief"),
            short_url=short_url,
            status=SITE_STATUS_COMPLETED,
            generation_completed_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    )


async def _mark_site_as_failed(db, business_id: str, error_message: str) -> None:
    """
    Mark site generation as failed in database.
    
    Args:
        db: Database session
        business_id: Business UUID string
        error_message: Error description
    """
    await db.execute(
        update(GeneratedSite)
        .where(GeneratedSite.business_id == business_id)
        .values(
            status=SITE_STATUS_FAILED,
            error_message=error_message,
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=600  # 10 minutes
)
async def generate_site_for_business(self, business_id: str):
    """
    Generate a website for a specific business.
    
    Main orchestration function that coordinates all generation steps:
    1. Validate business exists
    2. Check for existing site
    3. Create site record
    4. Generate content (HTML/CSS/JS)
    5. Create short link
    6. Save everything to database
    
    Args:
        business_id: Business UUID string
        
    Returns:
        Dictionary with generation status and details
        
    Raises:
        Retries on failure (max 2 retries with 10min delay)
    """
    logger.info(f"Starting site generation for business: {business_id}")
    
    try:
        async with get_db_session() as db:
            # Step 1: Validate business exists
            try:
                business = await _validate_business(db, business_id)
            except ValueError as e:
                return {"status": "error", "message": str(e)}
            
            # Step 2: Check if site already exists
            if await _check_existing_site(db, business_id):
                return {"status": "skipped", "message": "Site already exists"}
            
            # Step 3: Create site record
            site = await _create_site_record(db, business)
            
            # Step 4: Generate site content
            content = await _generate_site_content(db, str(business.id))
            
            # Step 5: Create short link (ONCE at generation time)
            site_url = build_site_url(site.subdomain)
            short_url = await create_short_link_for_site(
                db=db,
                site_url=site_url,
                business_id=business.id,
                site_id=site.id
            )
            
            # Step 6: Update site with content and short link
            await _update_site_with_content_and_url(db, site, content, short_url)
            await db.commit()
            
            logger.info(f"Successfully generated site for business {business_id}")
            return build_site_result_dict(
                business_id=business_id,
                site_id=site.id,
                subdomain=site.subdomain,
                status=SITE_STATUS_COMPLETED
            )
            
    except Exception as e:
        logger.error(
            f"Error generating site for business {business_id}: {str(e)}",
            exc_info=True
        )
        
        # Mark as failed
        async with get_db_session() as db:
            await _mark_site_as_failed(db, business_id, str(e))
        
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
