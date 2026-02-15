"""
Website Discovery Tasks.

Handles ScrapingDog-based website discovery with:
- Metadata tracking
- Status management
- Complete audit trail

Follows best practices: Clear Error Handling, Idempotent Operations, Comprehensive Logging.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from celery import shared_task

from core.database import get_db_session_sync
from models.business import Business
from services.validation.validation_metadata_service import ValidationMetadataService
from core.validation_enums import (
    ValidationState,
    URLSource,
    ValidationConfig
)

logger = logging.getLogger(__name__)


@shared_task(
    name="tasks.discovery.discover_missing_websites_v2",
    bind=True,
    max_retries=2,
    time_limit=300,  # 5 minutes
    soft_time_limit=270  # 4.5 minutes soft limit
)
def discover_missing_websites_v2(self, business_id: str) -> Dict[str, Any]:
    """
    Discover website URL using ScrapingDog Google Search.
    
    Enhanced version with:
    - Metadata tracking
    - Proper state transitions
    - Complete audit trail
    - Validation queue integration
    
    Args:
        business_id: UUID of business to search for
        
    Returns:
        Discovery result dictionary
    """
    try:
        logger.info(f"Starting ScrapingDog discovery for business {business_id}")
        
        with get_db_session_sync() as db:
            # Fetch business
            business = db.query(Business).filter(Business.id == business_id).first()
            
            if not business:
                logger.error(f"Business not found: {business_id}")
                return {"error": "Business not found", "business_id": business_id}
            
            # Initialize metadata service
            metadata_service = ValidationMetadataService()
            
            # Ensure metadata exists
            if not business.website_metadata:
                business.website_metadata = metadata_service.create_initial_metadata()
            
            # ================================================================
            # IDEMPOTENCY CHECK - Skip if already has URL
            # ================================================================
            if business.website_url:
                logger.info(f"Business {business_id} already has URL: {business.website_url}")
                return {
                    "business_id": business_id,
                    "status": "skipped",
                    "reason": "already_has_url",
                    "url": business.website_url
                }
            
            # ================================================================
            # CHECK IF ALREADY ATTEMPTED
            # ================================================================
            if business.has_attempted_scrapingdog():
                logger.warning(f"ScrapingDog already attempted for {business_id}")
                return {
                    "business_id": business_id,
                    "status": "skipped",
                    "reason": "already_attempted"
                }
            
            # ================================================================
            # UPDATE STATUS - Mark as in progress
            # ================================================================
            business.website_validation_status = ValidationState.DISCOVERY_IN_PROGRESS.value
            db.commit()
            
            logger.info(f"Running ScrapingDog search for: {business.name} ({business.city}, {business.state})")
            
            # ================================================================
            # RUN SCRAPINGDOG DISCOVERY
            # ================================================================
            discovery_result = _run_scrapingdog_search(business)
            
            found_url = discovery_result.get("url")
            
            # ================================================================
            # PROCESS RESULTS
            # ================================================================
            if found_url:
                # SUCCESS - Website found
                return _handle_url_found(db, business, found_url, discovery_result, metadata_service)
            else:
                # NO URL FOUND - Mark as confirmed missing
                return _handle_no_url_found(db, business, discovery_result, metadata_service)
            
    except Exception as e:
        logger.error(f"Discovery task failed for {business_id}: {e}", exc_info=True)
        
        # Retry on failure
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            return _handle_discovery_error(business_id, e)


def _run_scrapingdog_search(business: Business) -> Dict[str, Any]:
    """
    Run ScrapingDog Google Search for business.
    
    Args:
        business: Business instance
        
    Returns:
        Discovery result dictionary
    """
    from services.discovery.llm_discovery_service import LLMDiscoveryService
    
    discovery_service = LLMDiscoveryService()
    
    # Proper async event loop management
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(discovery_service.discover_website(
            business_name=business.name,
            phone=business.phone,
            address=business.address,
            city=business.city,
            state=business.state,
            country=business.country or "US"
        ))
        
        if result is None:
            raise Exception("Discovery service returned None")
        
        return result
        
    except Exception as e:
        logger.error(f"ScrapingDog search failed: {e}")
        raise
    finally:
        loop.close()


def _handle_url_found(
    db,
    business: Business,
    found_url: str,
    discovery_result: Dict[str, Any],
    metadata_service: ValidationMetadataService
) -> Dict[str, Any]:
    """
    Handle successful URL discovery.
    
    Args:
        db: Database session
        business: Business instance
        found_url: URL that was discovered
        discovery_result: Full discovery result
        metadata_service: Metadata service instance
        
    Returns:
        Result dictionary
    """
    confidence = discovery_result.get("confidence", 0)
    
    logger.info(
        f"✅ ScrapingDog found URL for {business.name}: {found_url} "
        f"(confidence: {confidence:.2f})"
    )
    
    # Update business record
    business.website_url = found_url
    business.website_validation_status = ValidationState.PENDING.value
    business.website_validated_at = None
    
    # Update metadata - source and discovery attempt
    business.website_metadata = metadata_service.update_url_source(
        business.website_metadata,
        source=URLSource.SCRAPINGDOG.value,
        url=found_url
    )
    
    business.website_metadata = metadata_service.record_discovery_attempt(
        business.website_metadata,
        method="scrapingdog",
        found_url=True,
        url_found=found_url,
        valid=False,  # Not validated yet
        notes=f"Found via ScrapingDog with {confidence:.1%} confidence"
    )
    
    # Save complete ScrapingDog response
    business.website_validation_result = {
        "stages": {
            "google_search": {
                "searched": True,
                "found": True,
                "url": found_url,
                "query": discovery_result.get("query", ""),
                "confidence": confidence,
                "reasoning": discovery_result.get("reasoning", ""),
                "match_signals": discovery_result.get("llm_analysis", {}).get("match_signals", {}),
                "llm_model": discovery_result.get("llm_model", ""),
                "search_results_count": len(discovery_result.get("search_results", {}).get("organic_results", [])),
                "scrapingdog_response": discovery_result.get("search_results", {})
            }
        }
    }
    
    db.commit()
    
    # Queue for validation
    from tasks.validation_tasks_enhanced import validate_business_website_v2
    validate_business_website_v2.delay(str(business.id))
    
    logger.info(f"Queued {business.id} for validation")
    
    return {
        "business_id": str(business.id),
        "status": "found",
        "url": found_url,
        "confidence": confidence,
        "queued_for_validation": True
    }


def _handle_no_url_found(
    db,
    business: Business,
    discovery_result: Dict[str, Any],
    metadata_service: ValidationMetadataService
) -> Dict[str, Any]:
    """
    Handle case where no URL was found.
    
    Args:
        db: Database session
        business: Business instance
        discovery_result: Full discovery result
        metadata_service: Metadata service instance
        
    Returns:
        Result dictionary
    """
    confidence = discovery_result.get("confidence", 0.95)
    
    logger.info(f"❌ ScrapingDog found no URL for {business.name} (confirmed no website)")
    
    # Mark as confirmed missing
    business.website_validation_status = ValidationState.CONFIRMED_NO_WEBSITE.value
    business.website_validated_at = datetime.utcnow()
    
    # Record discovery attempt
    business.website_metadata = metadata_service.record_discovery_attempt(
        business.website_metadata,
        method="scrapingdog",
        found_url=False,
        notes="ScrapingDog found no valid website"
    )
    
    # Save complete result
    business.website_validation_result = {
        "verdict": "confirmed_no_website",
        "stages": {
            "google_search": {
                "searched": True,
                "found": False,
                "query": discovery_result.get("query", ""),
                "confidence": confidence,
                "reasoning": discovery_result.get("reasoning", "No valid website found"),
                "llm_model": discovery_result.get("llm_model", ""),
                "search_results_count": len(discovery_result.get("search_results", {}).get("organic_results", [])),
                "scrapingdog_response": discovery_result.get("search_results", {})
            }
        },
        "reasoning": "No website found via Outscraper or ScrapingDog Google Search",
        "confidence": confidence
    }
    
    db.commit()
    
    return {
        "business_id": str(business.id),
        "status": "confirmed_missing",
        "triple_verified": True
    }


def _handle_discovery_error(business_id: str, error: Exception) -> Dict[str, Any]:
    """
    Handle discovery error after max retries.
    
    Args:
        business_id: Business UUID
        error: Exception that caused failure
        
    Returns:
        Result dictionary
    """
    logger.error(f"Max retries exceeded for discovery {business_id}")
    
    try:
        with get_db_session_sync() as db:
            business = db.query(Business).filter(Business.id == business_id).first()
            if business:
                business.website_validation_status = ValidationState.ERROR.value
                business.website_validation_result = {
                    "error": str(error),
                    "verdict": "error",
                    "stage": "discovery",
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
