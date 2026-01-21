"""
Edit Processing Tasks

Celery tasks for asynchronous processing of AI-powered edit requests.
Handles the complete workflow from request to preview generation.

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
from uuid import UUID
from typing import Optional
from datetime import datetime

from celery_app import celery_app
from core.database import AsyncSession, get_async_db
from services.edit_service import get_edit_service, EditRequestStatus
from services.creative.agents.editor import get_editor_agent
from services.site_service import get_site_service
from models.site_models import EditRequest, Site, SiteVersion

logger = logging.getLogger(__name__)


# ============================================================================
# MAIN PROCESSING TASK
# ============================================================================

@celery_app.task(
    name="tasks.edit_processing.process_edit_request",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def process_edit_request_task(self, edit_request_id: str):
    """
    Process an edit request asynchronously.
    
    Workflow:
    1. Update status to processing
    2. Get current site content
    3. Call EditorAgent to generate changes
    4. Create preview version
    5. Update status to ready_for_review
    6. Send notification email
    
    Args:
        edit_request_id: UUID of the edit request
    """
    import asyncio
    
    try:
        # Run async processing
        asyncio.run(process_edit_request_async(
            edit_request_id=UUID(edit_request_id)
        ))
        
        logger.info(f"Successfully processed edit request {edit_request_id}")
        
    except Exception as e:
        logger.error(
            f"Error processing edit request {edit_request_id}: {e}",
            exc_info=True
        )
        
        # Update status to failed
        try:
            asyncio.run(mark_request_failed(
                edit_request_id=UUID(edit_request_id),
                error_message=str(e)
            ))
        except Exception as update_error:
            logger.error(f"Failed to update error status: {update_error}")
        
        # Retry with exponential backoff
        raise self.retry(exc=e)


async def process_edit_request_async(edit_request_id: UUID):
    """
    Async implementation of edit request processing.
    
    Args:
        edit_request_id: UUID of the edit request
    """
    # Get database session
    async for db in get_async_db():
        try:
            edit_service = get_edit_service(db)
            editor_agent = get_editor_agent()
            site_service = get_site_service()
            
            # Step 1: Get the edit request
            edit_request = await edit_service.get_edit_request(edit_request_id)
            
            logger.info(
                f"Processing edit request {edit_request_id}",
                extra={
                    "site_id": str(edit_request.site_id),
                    "request_type": edit_request.request_type,
                    "request_text": edit_request.request_text[:100]
                }
            )
            
            # Step 2: Update status to processing
            await edit_service.update_status(
                request_id=edit_request_id,
                new_status=EditRequestStatus.PROCESSING
            )
            
            # Step 3: Get current site content
            from sqlalchemy import select
            site_query = (
                select(Site)
                .where(Site.id == edit_request.site_id)
            )
            result = await db.execute(site_query)
            site = result.scalar_one()
            
            # Get current version
            if site.current_version_id:
                version_query = (
                    select(SiteVersion)
                    .where(SiteVersion.id == site.current_version_id)
                )
                result = await db.execute(version_query)
                current_version = result.scalar_one()
                
                current_html = current_version.html_content
                current_css = current_version.css_content
                current_js = current_version.js_content
            else:
                # Fallback: read from file system
                site_path = site_service.get_site_path(site.slug)
                index_file = site_path / "index.html"
                
                if index_file.exists():
                    current_html = index_file.read_text(encoding='utf-8')
                    
                    # Try to find CSS
                    css_file = site_path / "assets" / "css" / "main.css"
                    current_css = (
                        css_file.read_text(encoding='utf-8')
                        if css_file.exists() else None
                    )
                    
                    # Try to find JS
                    js_file = site_path / "assets" / "js" / "main.js"
                    current_js = (
                        js_file.read_text(encoding='utf-8')
                        if js_file.exists() else None
                    )
                else:
                    raise ValueError(f"No content found for site {site.slug}")
            
            # Step 4: Process with AI
            logger.info(f"Calling EditorAgent for edit request {edit_request_id}")
            
            ai_result = await editor_agent.process_edit_request(
                request_text=edit_request.request_text,
                request_type=edit_request.request_type,
                current_html=current_html,
                current_css=current_css,
                current_js=current_js,
                target_section=edit_request.target_section,
                site_context={
                    "site_id": str(site.id),
                    "site_slug": site.slug,
                    "site_title": site.site_title
                }
            )
            
            if not ai_result.get("success"):
                # AI processing failed
                error_message = ai_result.get("error", "AI processing failed")
                logger.warning(
                    f"AI processing failed for edit request {edit_request_id}: {error_message}"
                )
                
                await edit_service.update_status(
                    request_id=edit_request_id,
                    new_status=EditRequestStatus.FAILED,
                    ai_interpretation={
                        "error": error_message,
                        "suggestions": ai_result.get("suggestions", [])
                    },
                    ai_confidence=ai_result.get("confidence", 0.0)
                )
                
                # TODO: Send notification email
                return
            
            # Step 5: Create preview version
            logger.info(f"Creating preview version for edit request {edit_request_id}")
            
            # Get next version number
            from sqlalchemy import func
            version_count_query = select(func.count()).where(
                SiteVersion.site_id == site.id
            )
            result = await db.execute(version_count_query)
            version_count = result.scalar_one()
            next_version = version_count + 1
            
            # Create preview version
            preview_version = SiteVersion(
                site_id=site.id,
                version_number=next_version,
                html_content=ai_result["modified_html"],
                css_content=ai_result.get("modified_css"),
                js_content=ai_result.get("modified_js"),
                change_description=f"Edit request: {edit_request.request_text[:100]}",
                change_type="edit",
                created_by_type="ai",
                is_current=False,
                is_preview=True
            )
            
            db.add(preview_version)
            await db.commit()
            await db.refresh(preview_version)
            
            # Step 6: Generate preview URL
            # For now, we'll use a special preview route
            # TODO: Implement actual preview system
            preview_url = f"https://sites.lavish.solutions/{site.slug}/preview/{preview_version.id}"
            
            # Step 7: Update edit request with results
            await edit_service.update_status(
                request_id=edit_request_id,
                new_status=EditRequestStatus.READY_FOR_REVIEW,
                ai_interpretation=ai_result.get("analysis", {}),
                ai_confidence=ai_result.get("confidence", 0.8),
                changes_made=ai_result.get("changes_made", {}),
                preview_version_id=preview_version.id,
                preview_url=preview_url
            )
            
            logger.info(
                f"Edit request {edit_request_id} ready for review",
                extra={
                    "preview_version_id": str(preview_version.id),
                    "preview_url": preview_url,
                    "confidence": ai_result.get("confidence")
                }
            )
            
            # Step 8: Send notification email
            # TODO: Implement email notification
            # await send_preview_ready_email(
            #     edit_request=edit_request,
            #     preview_url=preview_url
            # )
            
        except Exception as e:
            logger.error(f"Error in async processing: {e}", exc_info=True)
            raise
        
        finally:
            await db.close()


async def mark_request_failed(
    edit_request_id: UUID,
    error_message: str
):
    """
    Mark an edit request as failed.
    
    Args:
        edit_request_id: UUID of the edit request
        error_message: Error message
    """
    async for db in get_async_db():
        try:
            edit_service = get_edit_service(db)
            
            await edit_service.update_status(
                request_id=edit_request_id,
                new_status=EditRequestStatus.FAILED,
                ai_interpretation={
                    "error": error_message,
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
        
        finally:
            await db.close()


# ============================================================================
# DEPLOYMENT TASK
# ============================================================================

@celery_app.task(
    name="tasks.edit_processing.deploy_approved_edit",
    bind=True,
    max_retries=2
)
def deploy_approved_edit_task(self, edit_request_id: str):
    """
    Deploy an approved edit to the live site.
    
    Workflow:
    1. Verify request is approved
    2. Create backup of current version
    3. Deploy changes to file system
    4. Update database records
    5. Update status to deployed
    6. Send confirmation email
    
    Args:
        edit_request_id: UUID of the approved edit request
    """
    import asyncio
    
    try:
        asyncio.run(deploy_approved_edit_async(
            edit_request_id=UUID(edit_request_id)
        ))
        
        logger.info(f"Successfully deployed edit request {edit_request_id}")
        
    except Exception as e:
        logger.error(
            f"Error deploying edit request {edit_request_id}: {e}",
            exc_info=True
        )
        raise self.retry(exc=e)


async def deploy_approved_edit_async(edit_request_id: UUID):
    """
    Async implementation of edit deployment.
    
    Args:
        edit_request_id: UUID of the edit request
    """
    from sqlalchemy import select
    
    async for db in get_async_db():
        try:
            edit_service = get_edit_service(db)
            site_service = get_site_service()
            
            # Get edit request
            edit_request = await edit_service.get_edit_request(edit_request_id)
            
            # Verify it's approved
            if edit_request.status != EditRequestStatus.APPROVED:
                raise ValueError(
                    f"Edit request {edit_request_id} is not approved (status: {edit_request.status})"
                )
            
            if not edit_request.preview_version_id:
                raise ValueError(
                    f"Edit request {edit_request_id} has no preview version"
                )
            
            logger.info(
                f"Deploying approved edit request {edit_request_id}",
                extra={
                    "site_id": str(edit_request.site_id),
                    "preview_version_id": str(edit_request.preview_version_id)
                }
            )
            
            # Get site and preview version
            site_query = select(Site).where(Site.id == edit_request.site_id)
            result = await db.execute(site_query)
            site = result.scalar_one()
            
            version_query = select(SiteVersion).where(
                SiteVersion.id == edit_request.preview_version_id
            )
            result = await db.execute(version_query)
            preview_version = result.scalar_one()
            
            # Create backup version if current version exists
            if site.current_version_id:
                logger.info("Creating backup of current version")
                site_service.create_version_backup(
                    slug=site.slug,
                    version_number=preview_version.version_number - 1
                )
            
            # Deploy to file system
            logger.info("Deploying changes to file system")
            
            site_service.deploy_site(
                slug=site.slug,
                html_content=preview_version.html_content,
                css_content=preview_version.css_content,
                js_content=preview_version.js_content,
                overwrite=True
            )
            
            # Update preview version to be current
            preview_version.is_preview = False
            preview_version.is_current = True
            
            # Mark old version as not current
            if site.current_version_id:
                old_version_query = select(SiteVersion).where(
                    SiteVersion.id == site.current_version_id
                )
                result = await db.execute(old_version_query)
                old_version = result.scalar_one_or_none()
                if old_version:
                    old_version.is_current = False
            
            # Update site current version
            site.current_version_id = preview_version.id
            
            # Update edit request status
            await edit_service.update_status(
                request_id=edit_request_id,
                new_status=EditRequestStatus.DEPLOYED,
                deployed_version_id=preview_version.id
            )
            
            await db.commit()
            
            logger.info(
                f"Successfully deployed edit request {edit_request_id}",
                extra={
                    "site_slug": site.slug,
                    "version_number": preview_version.version_number
                }
            )
            
            # TODO: Send confirmation email
            # await send_edit_deployed_email(
            #     edit_request=edit_request,
            #     site=site
            # )
        
        except Exception as e:
            logger.error(f"Error in deployment: {e}", exc_info=True)
            raise
        
        finally:
            await db.close()


# ============================================================================
# HELPER TASKS
# ============================================================================

@celery_app.task(name="tasks.edit_processing.cleanup_old_previews")
def cleanup_old_previews_task():
    """
    Cleanup old preview versions (older than 7 days).
    
    This task should be run periodically (e.g., daily).
    """
    import asyncio
    asyncio.run(cleanup_old_previews_async())


async def cleanup_old_previews_async():
    """Async implementation of preview cleanup."""
    from datetime import timedelta
    from sqlalchemy import select, and_
    
    async for db in get_async_db():
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            # Find old preview versions
            query = select(SiteVersion).where(
                and_(
                    SiteVersion.is_preview == True,
                    SiteVersion.created_at < cutoff_date
                )
            )
            
            result = await db.execute(query)
            old_previews = result.scalars().all()
            
            logger.info(f"Found {len(old_previews)} old preview versions to cleanup")
            
            for preview in old_previews:
                await db.delete(preview)
            
            await db.commit()
            
            logger.info(f"Cleaned up {len(old_previews)} old preview versions")
        
        finally:
            await db.close()

