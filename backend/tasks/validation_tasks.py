"""
Celery tasks for website validation.
Handles asynchronous website validation using Playwright.
"""
import asyncio
from celery import shared_task
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from core.database import get_db_session_sync
from core.config import get_settings
from services.validation.playwright_service import PlaywrightValidationService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="tasks.validation.validate_business_website",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    time_limit=120,  # 2 minutes hard limit
    soft_time_limit=90  # 90 seconds soft limit
)
def validate_business_website(self, business_id: str):
    """
    Validate a business website using Playwright.
    
    This task:
    1. Fetches business from database
    2. Validates the website URL
    3. Extracts business information
    4. Updates business record with results
    
    Args:
        business_id: UUID of the business to validate
        
    Returns:
        Dict with validation results
    """
    try:
        logger.info(f"Starting validation for business {business_id}")
        
        # Get database session
        with get_db_session_sync() as db:
            # Import here to avoid circular imports
            from models.business import Business
            
            # Get business
            business = db.query(Business).filter(Business.id == business_id).first()
            
            if not business:
                logger.error(f"Business not found: {business_id}")
                return {"error": "Business not found", "business_id": business_id}
            
            if not business.website_url:
                logger.warning(f"Business {business_id} has no website URL")
                business.website_validation_status = "no_website"
                business.website_validated_at = datetime.utcnow()
                # db.commit() is handled by context manager
                return {"error": "No website URL", "business_id": business_id}
            
            # Run validation (sync wrapper for async code)
            result = asyncio.run(_run_validation(business.website_url))
            
            # Update business record
            business.website_validation_status = "valid" if result["is_valid"] else "invalid"
            business.website_validation_result = result
            business.website_validated_at = datetime.utcnow()
            
            # Optionally store screenshot URL (if implemented)
            if result.get("screenshot_base64"):
                # TODO: Upload to S3 and store URL
                # business.website_screenshot_url = await upload_screenshot(...)
                pass
            
            # db.commit() is handled by context manager
            
            logger.info(
                f"Validation completed for business {business_id}: "
                f"is_valid={result['is_valid']}, "
                f"quality_score={result.get('quality_score', 0)}"
            )
            
            return {
                "business_id": business_id,
                "status": "success",
                "is_valid": result["is_valid"],
                "quality_score": result.get("quality_score", 0)
            }
            
    except Exception as e:
        logger.error(f"Validation task failed for business {business_id}: {e}", exc_info=True)
        
        # Retry on failure
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for business {business_id}")
            
            # Mark as failed in database
            with get_db_session_sync() as db:
                from models.business import Business
                business = db.query(Business).filter(Business.id == business_id).first()
                if business:
                    business.website_validation_status = "error"
                    business.website_validation_result = {
                        "error": str(e),
                        "is_valid": False
                    }
                    business.website_validated_at = datetime.utcnow()
                    # db.commit() is handled by context manager
            
            return {
                "business_id": business_id,
                "status": "error",
                "error": str(e)
            }


@shared_task(
    name="tasks.validation.batch_validate_websites",
    time_limit=600  # 10 minutes
)
def batch_validate_websites(business_ids: list[str]):
    """
    Trigger validation for multiple businesses.
    
    Args:
        business_ids: List of business UUIDs
        
    Returns:
        Dict with summary of queued tasks
    """
    logger.info(f"Batch validation requested for {len(business_ids)} businesses")
    
    tasks = []
    for business_id in business_ids:
        task = validate_business_website.delay(business_id)
        tasks.append({
            "business_id": business_id,
            "task_id": task.id
        })
    
    return {
        "total": len(business_ids),
        "queued": len(tasks),
        "tasks": tasks
    }


async def _run_validation(url: str) -> dict:
    """
    Run async validation.
    
    Args:
        url: Website URL to validate
        
    Returns:
        Validation result dictionary
    """
    settings = get_settings()
    async with PlaywrightValidationService() as validator:
        return await validator.validate_website(
            url,
            timeout=settings.VALIDATION_TIMEOUT_MS,
            capture_screenshot=settings.VALIDATION_CAPTURE_SCREENSHOTS
        )


@shared_task(
    name="tasks.validation.validate_all_pending",
    time_limit=3600  # 1 hour
)
def validate_all_pending():
    """
    Validate all businesses with pending website validation status.
    Useful for periodic batch processing.
    """
    with get_db_session_sync() as db:
        from models.business import Business
        
        # Find businesses with pending validation
        pending_businesses = db.query(Business).filter(
            Business.website_url.isnot(None),
            Business.website_validation_status == "pending"
        ).limit(100).all()  # Process max 100 at a time
        
        logger.info(f"Found {len(pending_businesses)} businesses with pending validation")
        
        # Queue validation tasks
        tasks = []
        for business in pending_businesses:
            task = validate_business_website.delay(str(business.id))
            tasks.append({
                "business_id": str(business.id),
                "task_id": task.id
            })
        
        return {
            "total_pending": len(pending_businesses),
            "queued": len(tasks),
            "tasks": tasks
        }

