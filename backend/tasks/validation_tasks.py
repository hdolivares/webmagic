"""
Celery tasks for website validation.
Handles asynchronous website validation using LLM-powered orchestrator.
"""
import asyncio
from celery import shared_task
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from core.database import get_db_session_sync
from core.config import get_settings
from services.validation.validation_orchestrator import ValidationOrchestrator

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
    Validate a business website using LLM-powered orchestrator.
    
    Pipeline:
    1. Fetches business from database
    2. URL Prescreener (fast checks)
    3. Playwright (content extraction)
    4. LLM (intelligent cross-referencing)
    5. Updates business record with verdict
    
    Args:
        business_id: UUID of the business to validate
        
    Returns:
        Dict with validation results
    """
    try:
        logger.info(f"Starting LLM validation for business {business_id}")
        
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
                logger.info(f"Business {business_id} has no URL - triggering website discovery")
                
                # Auto-trigger Google Search discovery (Stage 4)
                # This integrates website discovery into the validation pipeline
                discovery_task = discover_missing_websites.delay(str(business_id))
                
                return {
                    "business_id": business_id,
                    "status": "discovery_queued",
                    "discovery_task_id": discovery_task.id,
                    "message": "No URL found - queued for Google Search discovery"
                }
            
            # Prepare business context for LLM
            business_context = {
                "name": business.name,
                "phone": business.phone,
                "email": business.email,
                "address": business.address,
                "city": business.city,
                "state": business.state,
                "country": business.country or "US",
            }
            
            # Run validation through orchestrator (sync wrapper for async code)
            result = asyncio.run(_run_validation(
                business_context=business_context,
                url=business.website_url
            ))
            
            # Extract verdict
            verdict = result.get("verdict", "error")
            confidence = result.get("confidence", 0)
            recommendation = result.get("recommendation", "")
            
            # Update business record
            business.website_validation_status = verdict
            business.website_validation_result = result
            business.website_validated_at = datetime.utcnow()
            
            # Clear URL if recommendation says so (directory/aggregator)
            if "clear_url" in recommendation:
                logger.info(f"Clearing URL for {business_id} (not business's actual website)")
                business.website_url = None
            
            # db.commit() is handled by context manager
            
            logger.info(
                f"LLM validation completed for business {business_id}: "
                f"verdict={verdict}, confidence={confidence:.2f}"
            )
            
            return {
                "business_id": business_id,
                "status": "success",
                "verdict": verdict,
                "confidence": confidence
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
                        "verdict": "error"
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


async def _run_validation(business_context: dict, url: str) -> dict:
    """
    Run async LLM-powered validation through orchestrator.
    
    Args:
        business_context: Business data for cross-referencing
        url: Website URL to validate
        
    Returns:
        Validation result dictionary with verdict, confidence, reasoning
    """
    from core.database import AsyncSessionLocal
    
    settings = get_settings()
    
    # Create async DB session for loading system settings
    async with AsyncSessionLocal() as db:
        async with ValidationOrchestrator(db=db) as orchestrator:
            return await orchestrator.validate_business_website(
                business=business_context,
                url=url,
                timeout=settings.VALIDATION_TIMEOUT_MS,
                capture_screenshot=settings.VALIDATION_CAPTURE_SCREENSHOTS
            )


@shared_task(
    bind=True,
    name="tasks.validation.discover_missing_websites",
    max_retries=2,
    default_retry_delay=60,  # 1 minute
    time_limit=300,  # 5 minutes (increased from 3 to prevent timeouts)
    soft_time_limit=270  # 4.5 minutes soft limit
)
def discover_missing_websites(self, business_id: str):
    """
    Stage 4: Use Google Search (ScrapingDog) to discover websites for businesses without URLs.
    
    This task handles the "missing website" scenario by:
    1. Performing Google Search for the business
    2. If website found: Updates URL and queues for validation
    3. If no website found: Marks as "missing" (triple-verified)
    
    Args:
        business_id: UUID of the business to search for
        
    Returns:
        Dict with discovery results
        
    Best Practices:
        - Rate limited (handled by Celery task spacing)
        - Idempotent (safe to retry)
        - Updates database atomically
        - Proper error handling and logging
    """
    try:
        logger.info(f"Starting website discovery for business {business_id}")
        
        with get_db_session_sync() as db:
            from models.business import Business
            
            # Get business
            business = db.query(Business).filter(Business.id == business_id).first()
            
            if not business:
                logger.error(f"Business not found: {business_id}")
                return {"error": "Business not found", "business_id": business_id}
            
            # Skip if already has URL (idempotency check)
            if business.website_url:
                logger.info(f"Business {business_id} already has URL: {business.website_url}")
                return {
                    "business_id": business_id,
                    "status": "skipped",
                    "reason": "already_has_url"
                }
            
            # Run LLM-powered Google Search discovery
            from services.discovery.llm_discovery_service import LLMDiscoveryService
            
            discovery_service = LLMDiscoveryService()
            
            # Proper async event loop management to prevent "Event loop is closed" errors
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
            finally:
                loop.close()  # Ensure proper cleanup
            
            found_url = result.get("url")
            
            if found_url:
                # Website found! Update and queue for validation
                logger.info(f"✅ Found website for {business.name}: {found_url} (confidence: {result.get('confidence', 0)})")
                business.website_url = found_url
                business.website_validation_status = "pending"
                business.website_validated_at = None
                
                # Save full discovery result in validation_result
                business.website_validation_result = {
                    "stages": {
                        "google_search": {
                            "searched": True,
                            "found": True,
                            "url": found_url,
                            "query": result.get("query", ""),
                            "confidence": result.get("confidence", 0),
                            "reasoning": result.get("reasoning", ""),
                            "match_signals": result.get("llm_analysis", {}).get("match_signals", {}),
                            "llm_model": result.get("llm_model", ""),
                            "search_results_count": len(result.get("search_results", {}).get("organic_results", [])),
                            # Save ALL ScrapingDog data for debugging
                            "scrapingdog_response": result.get("search_results", {})
                        }
                    }
                }
                
                # Queue for validation
                validate_business_website.delay(str(business.id))
                
                return {
                    "business_id": business_id,
                    "status": "found",
                    "url": found_url,
                    "confidence": result.get("confidence", 0),
                    "queued_for_validation": True
                }
            else:
                # No website found - mark as triple-verified missing
                logger.info(f"❌ No website found for {business.name} (triple-verified)")
                business.website_validation_status = "missing"
                business.website_validation_result = {
                    "verdict": "missing",
                    "stages": {
                        "google_search": {
                            "searched": True,
                            "found": False,
                            "query": result.get("query", ""),
                            "confidence": result.get("confidence", 0),
                            "reasoning": result.get("reasoning", "No valid website found"),
                            "llm_model": result.get("llm_model", ""),
                            "search_results_count": len(result.get("search_results", {}).get("organic_results", [])),
                            # Save ALL ScrapingDog data for debugging
                            "scrapingdog_response": result.get("search_results", {})
                        }
                    },
                    "reasoning": "No website found via Outscraper, raw_data check, or Google Search",
                    "confidence": result.get("confidence", 0.95)
                }
                business.website_validated_at = datetime.utcnow()
                
                return {
                    "business_id": business_id,
                    "status": "confirmed_missing",
                    "triple_verified": True
                }
                
    except Exception as e:
        logger.error(f"Discovery task failed for business {business_id}: {e}", exc_info=True)
        
        # Retry on failure
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for discovery {business_id}")
            
            # Mark as error in database
            with get_db_session_sync() as db:
                from models.business import Business
                business = db.query(Business).filter(Business.id == business_id).first()
                if business:
                    business.website_validation_status = "error"
                    business.website_validation_result = {
                        "error": f"Discovery failed: {str(e)}",
                        "verdict": "error"
                    }
                    business.website_validated_at = datetime.utcnow()
            
            return {
                "business_id": business_id,
                "status": "error",
                "error": str(e)
            }


@shared_task(
    name="tasks.validation.discover_all_missing",
    time_limit=7200  # 2 hours (for up to 400 businesses at 1/sec)
)
def discover_all_missing(limit: int = 100, delay_seconds: float = 1.0):
    """
    Batch discover websites for all businesses without URLs.
    
    This task queues discovery tasks with proper rate limiting to respect
    ScrapingDog API limits (typically 1 request/second).
    
    Args:
        limit: Maximum number of businesses to process
        delay_seconds: Delay between queuing tasks (rate limiting)
        
    Returns:
        Dict with summary of queued tasks
        
    Best Practices:
        - Respects API rate limits via countdown parameter
        - Processes only businesses that need discovery
        - Provides progress tracking
        - Safe to run multiple times (idempotent)
    """
    import time
    
    with get_db_session_sync() as db:
        from models.business import Business
        from sqlalchemy import or_, func, cast
        from sqlalchemy.dialects.postgresql import JSONB
        
        # Find businesses without URLs that need Google Search discovery
        # Include both:
        # 1. New businesses (pending/None status)
        # 2. Businesses marked as 'missing' but haven't been searched via Google yet
        businesses = db.query(Business).filter(
            Business.website_url.is_(None),
            or_(
                Business.website_validation_status.in_(['pending', None]),
                # Include 'missing' businesses that haven't been searched via Google
                (Business.website_validation_status == 'missing') & 
                ~func.jsonb_exists(
                    cast(Business.website_validation_result['stages'], JSONB),
                    'google_search'
                )
            )
        ).order_by(
            Business.qualification_score.desc()  # Prioritize high-quality leads
        ).limit(limit).all()
        
        logger.info(f"Found {len(businesses)} businesses needing website discovery")
        
        if not businesses:
            logger.info("No businesses need discovery - all done!")
            return {"total": 0, "queued": 0}
        
        # Queue discovery tasks with countdown for rate limiting
        tasks = []
        for idx, business in enumerate(businesses):
            # Calculate countdown to space out tasks (rate limiting)
            countdown = int(idx * delay_seconds)
            
            task = discover_missing_websites.apply_async(
                args=[str(business.id)],
                countdown=countdown  # Delay this task by N seconds
            )
            
            tasks.append({
                "business_id": str(business.id),
                "business_name": business.name,
                "task_id": task.id,
                "starts_in_seconds": countdown
            })
            
            # Log every 10th business for progress tracking
            if (idx + 1) % 10 == 0:
                logger.info(f"Queued {idx + 1}/{len(businesses)} discovery tasks")
        
        total_time_minutes = (len(businesses) * delay_seconds) / 60
        logger.info(
            f"✅ Queued {len(tasks)} discovery tasks. "
            f"Will complete in approximately {total_time_minutes:.1f} minutes"
        )
        
        return {
            "total": len(businesses),
            "queued": len(tasks),
            "estimated_completion_minutes": total_time_minutes,
            "tasks": tasks[:10]  # Return first 10 for reference
        }


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


# Removed: _run_google_search - replaced by LLMDiscoveryService
# The new LLM-powered discovery provides:
# - Intelligent cross-referencing (phone, address, name)
# - Better accuracy through context understanding
# - Full data persistence (ScrapingDog responses saved)
# - No hardcoded regex patterns

