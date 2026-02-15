"""
Enhanced Website Validation Tasks.

Implements complete validation flow with:
- Metadata tracking
- Discovery pipeline
- Proper ScrapingDog triggering
- Audit trail

Follows best practices: Single Responsibility, Clear Error Handling, Comprehensive Logging.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from celery import shared_task

from core.database import get_db_session_sync
from models.business import Business
from services.validation.validation_orchestrator import ValidationOrchestrator
from services.validation.validation_metadata_service import ValidationMetadataService
from core.validation_enums import (
    ValidationState,
    ValidationRecommendation,
    URLSource,
    ValidationConfig
)

logger = logging.getLogger(__name__)


@shared_task(
    name="tasks.validation.validate_business_website_v2",
    bind=True,
    max_retries=ValidationConfig.MAX_VALIDATION_RETRIES,
    time_limit=ValidationConfig.VALIDATION_TASK_TIMEOUT_SECONDS
)
def validate_business_website_v2(self, business_id: str) -> Dict[str, Any]:
    """
    Validate a business website with enhanced metadata tracking.
    
    This is the main entry point for website validation. It:
    1. Determines if validation is needed
    2. Runs the validation pipeline
    3. Updates business record with results and metadata
    4. Triggers ScrapingDog discovery if needed
    5. Maintains complete audit trail
    
    Args:
        business_id: UUID of business to validate
        
    Returns:
        Result dictionary with status and actions taken
    """
    try:
        with get_db_session_sync() as db:
            # Fetch business
            business = db.query(Business).filter(Business.id == business_id).first()
            
            if not business:
                logger.error(f"Business not found: {business_id}")
                return {"error": "Business not found", "business_id": business_id}
            
            logger.info(
                f"Starting validation for {business.name} "
                f"(status: {business.website_validation_status}, "
                f"url: {business.website_url or 'None'})"
            )
            
            # Initialize metadata service
            metadata_service = ValidationMetadataService()
            
            # Ensure metadata exists
            if not business.website_metadata:
                business.website_metadata = metadata_service.create_initial_metadata()
            
            # ================================================================
            # CASE 1: No URL at all - Queue for discovery
            # ================================================================
            if not business.website_url:
                logger.info(f"Business {business_id} has no URL - needs discovery")
                return _handle_no_url(db, business, metadata_service)
            
            # ================================================================
            # CASE 2: Already in discovery pipeline - Skip validation
            # ================================================================
            if business.website_validation_status in [
                ValidationState.DISCOVERY_QUEUED.value,
                ValidationState.DISCOVERY_IN_PROGRESS.value
            ]:
                logger.info(f"Business {business_id} already in discovery pipeline")
                return {"status": "skipped", "reason": "discovery_in_progress"}
            
            # ================================================================
            # CASE 3: Terminal state - Skip unless forced
            # ================================================================
            if business.validation_is_terminal:
                logger.info(f"Business {business_id} in terminal state: {business.website_validation_status}")
                return {"status": "skipped", "reason": "terminal_state"}
            
            # ================================================================
            # CASE 4: Run validation
            # ================================================================
            return asyncio.run(_run_website_validation(db, business, metadata_service))
            
    except Exception as e:
        logger.error(f"Validation task failed for {business_id}: {e}", exc_info=True)
        
        # Retry on failure
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            return _handle_validation_error(business_id, e)


def _handle_no_url(
    db,
    business: Business,
    metadata_service: ValidationMetadataService
) -> Dict[str, Any]:
    """
    Handle business with no URL - queue for discovery.
    
    Args:
        db: Database session
        business: Business instance
        metadata_service: Metadata service instance
        
    Returns:
        Result dictionary
    """
    # Update status
    business.website_validation_status = ValidationState.NEEDS_DISCOVERY.value
    
    # Update metadata
    business.website_metadata = metadata_service.record_discovery_attempt(
        business.website_metadata,
        method="outscraper",
        found_url=False,
        notes="No URL from Outscraper"
    )
    
    db.commit()
    
    # Queue ScrapingDog discovery
    from tasks.discovery_tasks import discover_missing_websites_v2
    discovery_task = discover_missing_websites_v2.delay(str(business.id))
    
    logger.info(f"Queued discovery for {business.id} (task: {discovery_task.id})")
    
    return {
        "business_id": str(business.id),
        "status": "discovery_queued",
        "discovery_task_id": discovery_task.id
    }


async def _run_website_validation(
    db,
    business: Business,
    metadata_service: ValidationMetadataService
) -> Dict[str, Any]:
    """
    Run the complete validation pipeline.
    
    Args:
        db: Database session
        business: Business instance
        metadata_service: Metadata service instance
        
    Returns:
        Result dictionary
    """
    url = business.website_url
    
    # Prepare business context
    business_context = {
        "name": business.name,
        "phone": business.phone,
        "email": business.email,
        "address": business.address,
        "city": business.city,
        "state": business.state,
        "country": business.country or "US",
    }
    
    # Run validation
    async def run_validation():
        orchestrator = ValidationOrchestrator(db=db)
        return await orchestrator.validate_business_website(
            url=url,
            **business_context
        )
    
    validation_result = await run_validation()
    
    # Extract key fields
    verdict = validation_result.get("verdict", "error")
    confidence = validation_result.get("confidence", 0)
    recommendation = validation_result.get("recommendation", "")
    invalid_reason = validation_result.get("invalid_reason")
    
    logger.info(
        f"Validation complete: verdict={verdict}, "
        f"confidence={confidence:.2f}, "
        f"recommendation={recommendation}, "
        f"reason={invalid_reason}"
    )
    
    # Add to validation history
    business.website_metadata = metadata_service.add_validation_entry(
        business.website_metadata,
        url,
        validation_result
    )
    
    # ====================================================================
    # PROCESS RECOMMENDATION
    # ====================================================================
    
    if recommendation == ValidationRecommendation.KEEP_URL.value:
        # SUCCESS - Valid website found
        return _handle_valid_website(db, business, validation_result, metadata_service)
    
    elif recommendation == ValidationRecommendation.TRIGGER_SCRAPINGDOG.value:
        # REJECTED - Clear URL and trigger discovery
        return _handle_rejected_url(db, business, validation_result, metadata_service)
    
    elif recommendation == ValidationRecommendation.RETRY_VALIDATION.value:
        # TECHNICAL FAILURE - Keep URL, retry later
        return _handle_technical_failure(db, business, validation_result)
    
    else:
        # UNKNOWN - Mark as error
        logger.error(f"Unknown recommendation: {recommendation}")
        business.website_validation_status = ValidationState.ERROR.value
        business.website_validation_result = validation_result
        business.website_validated_at = datetime.utcnow()
        db.commit()
        
        return {
            "business_id": str(business.id),
            "status": "error",
            "verdict": verdict,
            "recommendation": recommendation
        }


def _handle_valid_website(
    db,
    business: Business,
    validation_result: Dict[str, Any],
    metadata_service: ValidationMetadataService
) -> Dict[str, Any]:
    """
    Handle successful validation - website is valid.
    
    Args:
        db: Database session
        business: Business instance
        validation_result: Validation result
        metadata_service: Metadata service instance
        
    Returns:
        Result dictionary
    """
    # Determine status based on source
    source = business.url_source
    if source == URLSource.SCRAPINGDOG.value:
        new_status = ValidationState.VALID_SCRAPINGDOG.value
    elif source == URLSource.MANUAL.value:
        new_status = ValidationState.VALID_MANUAL.value
    else:
        new_status = ValidationState.VALID_OUTSCRAPER.value
    
    business.website_validation_status = new_status
    business.website_validation_result = validation_result
    business.website_validated_at = datetime.utcnow()
    
    # Record successful validation
    business.website_metadata = metadata_service.record_discovery_attempt(
        business.website_metadata,
        method=source,
        found_url=True,
        url_found=business.website_url,
        valid=True,
        notes=f"Validated as {new_status}"
    )
    
    db.commit()
    
    logger.info(f"✅ Valid website found: {business.website_url} (status: {new_status})")
    
    return {
        "business_id": str(business.id),
        "status": "success",
        "verdict": "valid",
        "final_status": new_status,
        "url": business.website_url
    }


def _handle_rejected_url(
    db,
    business: Business,
    validation_result: Dict[str, Any],
    metadata_service: ValidationMetadataService
) -> Dict[str, Any]:
    """
    Handle rejected URL - clear it and trigger ScrapingDog.
    
    Args:
        db: Database session
        business: Business instance
        validation_result: Validation result
        metadata_service: Metadata service instance
        
    Returns:
        Result dictionary
    """
    rejected_url = business.website_url
    invalid_reason = validation_result.get("invalid_reason", "unknown")
    
    logger.info(
        f"❌ URL rejected: {rejected_url} "
        f"(reason: {invalid_reason}) - triggering ScrapingDog"
    )
    
    # Clear the bad URL
    business.website_url = None
    business.website_validation_status = ValidationState.NEEDS_DISCOVERY.value
    business.website_validation_result = validation_result
    business.website_validated_at = datetime.utcnow()
    
    db.commit()
    
    # Check if we should trigger ScrapingDog
    if not metadata_service.should_trigger_discovery(business.website_metadata):
        logger.warning("ScrapingDog already attempted or max attempts reached")
        business.website_validation_status = ValidationState.CONFIRMED_NO_WEBSITE.value
        db.commit()
        
        return {
            "business_id": str(business.id),
            "status": "no_website",
            "reason": "max_discovery_attempts_reached"
        }
    
    # Queue ScrapingDog discovery
    from tasks.discovery_tasks import discover_missing_websites_v2
    discovery_task = discover_missing_websites_v2.delay(str(business.id))
    
    logger.info(f"Queued ScrapingDog discovery (task: {discovery_task.id})")
    
    return {
        "business_id": str(business.id),
        "status": "discovery_queued",
        "rejected_url": rejected_url,
        "invalid_reason": invalid_reason,
        "discovery_task_id": discovery_task.id
    }


def _handle_technical_failure(
    db,
    business: Business,
    validation_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle technical failure - keep URL for retry.
    
    Args:
        db: Database session
        business: Business instance
        validation_result: Validation result
        
    Returns:
        Result dictionary
    """
    invalid_reason = validation_result.get("invalid_reason", "unknown")
    
    logger.warning(
        f"⚠️ Technical failure: {business.website_url} "
        f"(reason: {invalid_reason}) - keeping URL for retry"
    )
    
    business.website_validation_status = ValidationState.INVALID_TECHNICAL.value
    business.website_validation_result = validation_result
    business.website_validated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "business_id": str(business.id),
        "status": "technical_failure",
        "verdict": "invalid",
        "invalid_reason": invalid_reason,
        "url": business.website_url
    }


def _handle_validation_error(business_id: str, error: Exception) -> Dict[str, Any]:
    """
    Handle validation error after max retries.
    
    Args:
        business_id: Business UUID
        error: Exception that caused failure
        
    Returns:
        Result dictionary
    """
    logger.error(f"Max retries exceeded for {business_id}")
    
    try:
        with get_db_session_sync() as db:
            business = db.query(Business).filter(Business.id == business_id).first()
            if business:
                business.website_validation_status = ValidationState.ERROR.value
                business.website_validation_result = {
                    "error": str(error),
                    "verdict": "error",
                    "timestamp": datetime.utcnow().isoformat()
                }
                business.website_validated_at = datetime.utcnow()
                db.commit()
    except Exception as e:
        logger.error(f"Failed to update error state: {e}")
    
    return {
        "business_id": business_id,
        "status": "error",
        "error": str(error)
    }


# ============================================================================
# BATCH VALIDATION TASK
# ============================================================================

@shared_task(
    name="tasks.validation.batch_validate_websites_v2",
    time_limit=600  # 10 minutes
)
def batch_validate_websites_v2(business_ids: list[str]) -> Dict[str, Any]:
    """
    Validate multiple business websites in batch.
    
    Args:
        business_ids: List of business UUIDs
        
    Returns:
        Summary of batch validation
    """
    logger.info(f"Starting batch validation for {len(business_ids)} businesses")
    
    results = {
        "total": len(business_ids),
        "queued": 0,
        "failed": 0
    }
    
    for business_id in business_ids:
        try:
            validate_business_website_v2.delay(business_id)
            results["queued"] += 1
        except Exception as e:
            logger.error(f"Failed to queue {business_id}: {e}")
            results["failed"] += 1
    
    logger.info(f"Batch validation queued: {results}")
    return results
