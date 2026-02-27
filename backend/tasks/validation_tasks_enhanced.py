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

# Countries we support for SMS outreach
_SUPPORTED_COUNTRIES = {"US"}


def _apply_detected_country_from_validation(
    business: Business,
    validation_result: Dict[str, Any]
) -> None:
    """
    Apply detected_country from the LLM website validator to the business record.

    The validator inspects the actual website content (phone numbers, postal codes,
    domain TLDs) and returns a detected_country alongside the standard verdict.
    We use this to correct or populate business.country when Outscraper omitted it.

    Only updates country when confidence >= 0.7 to avoid false positives.
    """
    detected_country = validation_result.get("detected_country")
    country_confidence = validation_result.get("country_confidence", 0.0)
    country_signals = validation_result.get("country_signals", [])

    if not detected_country or country_confidence < 0.7:
        return

    old_country = business.country
    if not old_country or old_country != detected_country:
        logger.info(
            f"🌍 Updating business {business.name!r} country from validation: "
            f"{old_country!r} → {detected_country!r} "
            f"(confidence={country_confidence:.0%}, signals={country_signals})"
        )
        business.country = detected_country

    if detected_country not in _SUPPORTED_COUNTRIES:
        logger.warning(
            f"🚫 Business {business.name!r} detected as non-US ({detected_country}) "
            f"during website validation."
        )


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


_RAW_DATA_WEBSITE_FIELDS = ["website", "site", "url", "domain", "website_url", "business_url", "web", "homepage"]
_SOCIAL_MEDIA_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
    "youtube.com", "tiktok.com", "pinterest.com"
}


def _extract_website_from_raw_data(raw_data: dict) -> "str | None":
    """Extract a real business website URL from Outscraper raw_data."""
    if not raw_data or not isinstance(raw_data, dict):
        return None
    for field in _RAW_DATA_WEBSITE_FIELDS:
        val = raw_data.get(field)
        if not val or not isinstance(val, str):
            continue
        url = val.strip()
        if len(url) < 7 or url.lower() in ("", "null", "none", "n/a"):
            continue
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower().lstrip("www.")
            if any(host == d or host.endswith("." + d) for d in _SOCIAL_MEDIA_DOMAINS):
                logger.info(f"Skipping social media URL from raw_data: {url}")
                continue
        except Exception:
            pass
        return url
    return None


def _handle_no_url(
    db,
    business: Business,
    metadata_service: ValidationMetadataService
) -> Dict[str, Any]:
    """
    Handle business with no URL - check raw_data first, then queue for discovery.
    
    Args:
        db: Database session
        business: Business instance
        metadata_service: Metadata service instance
        
    Returns:
        Result dictionary
    """
    # ----------------------------------------------------------------
    # FIRST: Check if Outscraper already gave us a URL in raw_data.
    # This happens when old code failed to parse the website field.
    # ----------------------------------------------------------------
    raw_data_url = _extract_website_from_raw_data(business.raw_data)
    if raw_data_url:
        logger.info(
            f"✅ Found URL in Outscraper raw_data for {business.name}: {raw_data_url} "
            f"— queuing for direct validation instead of ScrapingDog"
        )
        business.website_url = raw_data_url
        business.website_metadata = metadata_service.record_discovery_attempt(
            business.website_metadata,
            method="outscraper",
            found_url=True,
            url_found=raw_data_url,
            valid=False,
            notes=f"Recovered URL from Outscraper raw_data: {raw_data_url}"
        )
        business.website_validation_status = ValidationState.NEEDS_DISCOVERY.value
        db.commit()

        # Re-run this task with the URL now set — will go to CASE 4 (validation)
        from tasks.validation_tasks_enhanced import validate_business_website_v2
        validation_task = validate_business_website_v2.delay(str(business.id))
        logger.info(f"Queued validation for raw_data URL (task: {validation_task.id})")
        return {
            "business_id": str(business.id),
            "status": "raw_data_url_found",
            "url": raw_data_url,
            "validation_task_id": validation_task.id
        }

    # No URL anywhere — proceed to ScrapingDog discovery
    business.website_validation_status = ValidationState.NEEDS_DISCOVERY.value
    business.website_metadata = metadata_service.record_discovery_attempt(
        business.website_metadata,
        method="outscraper",
        found_url=False,
        notes="No URL from Outscraper raw_data or website_url"
    )
    db.commit()
    
    # Queue ScrapingDog discovery
    from tasks.discovery_tasks import discover_missing_websites_v2
    discovery_task = discover_missing_websites_v2.delay(str(business.id))
    
    logger.info(f"Queued ScrapingDog discovery for {business.id} (task: {discovery_task.id})")
    
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
            business=business_context,
            url=url
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

    # Apply detected country from the LLM validator's website analysis
    _apply_detected_country_from_validation(business, validation_result)
    
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
        # CONTENT REJECTION - check whether a human should review this before re-discovery.
        # Borderline cases (wrong_business / no_contact on a real, loaded site) benefit more
        # from a 30-second admin check than bouncing through the ScrapingDog loop again.
        if _is_content_mismatch_needing_review(validation_result):
            return _handle_needs_human_review(db, business, validation_result)

        # Clear-cut rejection (directory, aggregator, low-quality page) → re-run discovery
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


def _is_content_mismatch_needing_review(validation_result: Dict[str, Any]) -> bool:
    """
    Returns True when the LLM rejected a URL for content reasons (wrong business or
    missing contact info) AND the page actually loaded with meaningful content.

    These borderline cases are better resolved by a human in 30 seconds than by
    bouncing through another ScrapingDog discovery cycle which typically returns
    the same result and ends in the loop-prevention path.

    Does NOT route to human review when:
    - The rejection is for a directory/aggregator/social URL (type issue, not content)
    - Playwright failed to load the page at all (technical failure)
    - The page is a parking/empty page (quality score <= 30)
    """
    from core.validation_enums import InvalidURLReason

    invalid_reason = validation_result.get("invalid_reason")
    if invalid_reason not in {
        InvalidURLReason.WRONG_BUSINESS.value,
        InvalidURLReason.NO_CONTACT.value,
    }:
        return False

    playwright = validation_result.get("stages", {}).get("playwright", {})
    if not playwright.get("is_valid", False):
        return False

    quality_score = playwright.get("quality_score", 0) or 0
    return quality_score > 30


def _handle_needs_human_review(
    db,
    business: Business,
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Route a business to the admin verification queue.

    A real website was found and successfully loaded, but the LLM could not
    confirm the page belongs to this specific business.  An admin will review
    the candidate URL, the scraped content, and the LLM's reasoning, then make
    a final call.

    The candidate website_url is intentionally preserved so the admin can open
    it directly from the verification page.
    """
    invalid_reason = validation_result.get("invalid_reason", "unknown")
    candidate_url = business.website_url

    logger.info(
        f"👤 Routing to human review: {business.name!r} → {candidate_url} "
        f"(reason: {invalid_reason})"
    )

    business.website_validation_status = ValidationState.NEEDS_HUMAN_REVIEW.value
    business.website_validation_result = validation_result
    business.website_validated_at = datetime.utcnow()
    # website_url is intentionally kept — admin needs the candidate URL to review

    db.commit()

    return {
        "business_id": str(business.id),
        "status": "needs_human_review",
        "candidate_url": candidate_url,
        "invalid_reason": invalid_reason,
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


def _domain_resolves(url: str) -> bool:
    """
    Check if a URL's domain resolves via DNS.

    Returns True if the domain has at least one DNS record, False if it's
    unregistered / NXDOMAIN / unreachable at the DNS level.
    """
    import socket
    from urllib.parse import urlparse as _urlparse
    try:
        host = _urlparse(url).netloc.split(":")[0].strip()
        if not host:
            return False
        socket.getaddrinfo(host, 80, proto=socket.IPPROTO_TCP)
        return True
    except (socket.gaierror, OSError):
        return False


def _handle_technical_failure(
    db,
    business: Business,
    validation_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle technical failure after Playwright/LLM validation fails.

    Two sub-cases:
      1. Domain doesn't resolve (NXDOMAIN / available) → the URL was wrong.
         Clear it, reset to needs_discovery, and re-queue ScrapingDog.
      2. Domain resolves but Playwright failed → bot-detection, flaky page,
         or temporary outage. Keep as invalid_technical for human review.
    """
    invalid_reason = validation_result.get("invalid_reason", "unknown")
    url = business.website_url

    # ----------------------------------------------------------------
    # DNS CHECK — is this domain even registered?
    # ----------------------------------------------------------------
    if url and not _domain_resolves(url):
        logger.warning(
            f"🚫 Domain does not resolve for {business.name}: {url} "
            f"— domain is unregistered or dead. Clearing URL and re-queuing ScrapingDog."
        )

        # Record what happened
        import copy
        meta = copy.deepcopy(business.website_metadata or {})
        history = meta.get("validation_history", [])
        history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "dead_domain_cleared",
            "url": url,
            "invalid_reason": "domain_not_found",
            "notes": "DNS lookup returned NXDOMAIN — domain is unregistered or dead. Re-queuing ScrapingDog.",
        })
        meta["validation_history"] = history

        # Reset scrapingdog attempt flag so it can run again
        attempts = meta.get("discovery_attempts", {})
        attempts["scrapingdog"] = {}
        meta["discovery_attempts"] = attempts
        business.website_metadata = meta

        # Clear the dead URL and reset status
        business.website_url = None
        business.website_validation_status = ValidationState.NEEDS_DISCOVERY.value
        business.website_validation_result = None
        business.website_validated_at = None

        db.commit()

        # Re-queue ScrapingDog discovery
        from tasks.discovery_tasks import discover_missing_websites_v2
        task = discover_missing_websites_v2.delay(str(business.id))
        logger.info(f"Re-queued ScrapingDog discovery for {business.name} (task: {task.id})")

        return {
            "business_id": str(business.id),
            "status": "dead_domain_requeued",
            "verdict": "invalid",
            "invalid_reason": "domain_not_found",
            "cleared_url": url,
            "discovery_task_id": task.id,
        }

    # ----------------------------------------------------------------
    # DOMAIN EXISTS — Playwright failed for other reasons (bot-detection,
    # slow page, temporary outage). Keep the URL, mark invalid_technical.
    # ----------------------------------------------------------------
    logger.warning(
        f"⚠️ Technical failure for {business.name}: {url} "
        f"(reason: {invalid_reason}) — domain resolves, keeping URL for human review"
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
        "url": url,
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
