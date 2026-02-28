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

# Countries we support for SMS outreach. Businesses confirmed outside these
# countries are marked as geo_mismatch and excluded from generation.
_SUPPORTED_COUNTRIES = {"US"}


def _apply_detected_country(
    business: "Business",
    discovery_result: Dict[str, Any]
) -> bool:
    """
    Apply detected_country from a discovery result to the business record.

    Updates business.country when:
    - The discovery result contains a high-confidence detected_country, AND
    - The current business.country is null/empty OR is less specific.

    Returns True if the business country is (or remains) US-compatible.
    Returns False if the business was detected to be outside _SUPPORTED_COUNTRIES.
    """
    detected_country = discovery_result.get("detected_country")
    country_confidence = discovery_result.get("country_confidence", 0.0)
    country_signals = discovery_result.get("country_signals", [])

    if detected_country and country_confidence >= 0.7:
        old_country = business.country
        if not old_country or old_country != detected_country:
            logger.info(
                f"🌍 Updating business {business.name!r} country: "
                f"{old_country!r} → {detected_country!r} "
                f"(confidence={country_confidence:.0%}, signals={country_signals})"
            )
            business.country = detected_country

        if detected_country not in _SUPPORTED_COUNTRIES:
            logger.warning(
                f"🚫 Business {business.name!r} detected as non-US country "
                f"({detected_country}). Blocking from generation queue."
            )
            return False

    elif not business.country:
        # No detection signal and no existing country — default to US
        # (the business passed geo-validation during scraping so it's likely US)
        business.country = "US"

    current_country = business.country or "US"
    return current_country in _SUPPORTED_COUNTRIES


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
            # RAW DATA CHECK - Use Outscraper URL before spending ScrapingDog credits
            # ================================================================
            # Outscraper saves raw GMB data with a 'website' field. If it's present
            # we should validate that URL directly instead of running a new search.
            raw_data_url = _extract_website_from_raw_data(business.raw_data)
            if raw_data_url:
                logger.info(
                    f"✅ Found URL in Outscraper raw_data for {business.name}: {raw_data_url} "
                    f"— skipping ScrapingDog, queuing for direct validation"
                )
                business.website_url = raw_data_url
                business.website_metadata = metadata_service.record_discovery_attempt(
                    business.website_metadata,
                    method="outscraper",
                    found_url=True,
                    url_found=raw_data_url,
                    valid=False,  # Not yet validated by Playwright+LLM
                    notes=f"Recovered URL from Outscraper raw_data: {raw_data_url}"
                )
                business.website_validation_status = ValidationState.NEEDS_DISCOVERY.value
                db.commit()

                # Queue for full Playwright + LLM validation
                from tasks.validation_tasks_enhanced import validate_business_website_v2
                validation_task = validate_business_website_v2.delay(str(business.id))
                logger.info(f"Queued validation for raw_data URL (task: {validation_task.id})")
                return {
                    "business_id": business_id,
                    "status": "raw_data_url_found",
                    "url": raw_data_url,
                    "validation_task_id": validation_task.id
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


_RAW_DATA_WEBSITE_FIELDS = ["website", "site", "url", "domain", "website_url", "business_url", "web", "homepage"]
_SOCIAL_MEDIA_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
    "youtube.com", "tiktok.com", "pinterest.com"
}


def _extract_website_from_raw_data(raw_data: dict) -> str | None:
    """
    Extract a real business website URL from Outscraper raw_data.

    Checks every field name Outscraper might use for the website.
    Returns None if the URL is a social media profile, directory, or looks invalid.
    """
    if not raw_data or not isinstance(raw_data, dict):
        return None

    for field in _RAW_DATA_WEBSITE_FIELDS:
        val = raw_data.get(field)
        if not val or not isinstance(val, str):
            continue
        url = val.strip()
        if len(url) < 7 or url.lower() in ("", "null", "none", "n/a"):
            continue

        # Skip social media and obvious non-business URLs
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

    # ----------------------------------------------------------------
    # DIRECTORY / AGGREGATOR GUARD
    # Reject known directory and aggregator domains immediately.
    # These are never valid business websites — saving them as website_url
    # would waste Playwright+LLM time and could pollute the DB.
    # ----------------------------------------------------------------
    from core.validation_enums import categorize_url_domain, InvalidURLReason, NON_BUSINESS_DOMAINS
    from urllib.parse import urlparse as _urlparse

    def _is_non_business_domain(url: str) -> bool:
        try:
            host = _urlparse(url).netloc.lower().lstrip("www.")
            return any(host == d or host.endswith("." + d) for d in NON_BUSINESS_DOMAINS)
        except Exception:
            return False

    domain_category = categorize_url_domain(found_url)
    is_non_business = _is_non_business_domain(found_url)

    if domain_category in (
        InvalidURLReason.DIRECTORY.value,
        InvalidURLReason.AGGREGATOR.value,
        InvalidURLReason.SOCIAL_MEDIA.value,
    ) or is_non_business:
        logger.warning(
            f"🚫 ScrapingDog returned a non-business URL for {business.name}: {found_url} "
            f"(category={domain_category or 'matched NON_BUSINESS_DOMAINS'}) — treating as no URL found"
        )
        # Record the rejected URL in raw_data for audit purposes
        current_raw_data = business.raw_data or {}
        sd_data = current_raw_data.get("scrapingdog_discovery", {})
        sd_data["rejected_non_business_url"] = found_url
        sd_data["rejection_reason"] = domain_category or "non_business_domain"
        current_raw_data["scrapingdog_discovery"] = sd_data
        business.raw_data = current_raw_data
        return _handle_no_url_found(db, business, discovery_result, metadata_service)

    # ----------------------------------------------------------------
    # LOOP GUARD
    # Check if ScrapingDog returned the SAME URL that was just rejected
    # ----------------------------------------------------------------
    validation_history = business.website_metadata.get("validation_history", [])
    if validation_history:
        last_validation = validation_history[-1]
        last_rejected_url = last_validation.get("url", "")
        
        if last_rejected_url and found_url == last_rejected_url:
            logger.warning(
                f"⚠️ ScrapingDog returned the SAME rejected URL ({found_url}). "
                f"Marking as confirmed_no_website to prevent loop."
            )
            return _handle_no_url_found(db, business, discovery_result, metadata_service)
    
    logger.info(
        f"✅ ScrapingDog found URL for {business.name}: {found_url} "
        f"(confidence: {confidence:.2f})"
    )
    
    # Apply detected country (may update business.country)
    is_supported_country = _apply_detected_country(business, discovery_result)

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
    
    # Save complete ScrapingDog response to raw_data (like Outscraper does)
    # This preserves all search results for debugging and analysis
    current_raw_data = business.raw_data or {}
    social_urls = discovery_result.get("social_urls", {})

    current_raw_data["scrapingdog_discovery"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": discovery_result.get("query", ""),
        "url_found": found_url,
        "confidence": confidence,
        "reasoning": discovery_result.get("reasoning", ""),
        "llm_model": discovery_result.get("llm_model", ""),
        "llm_analysis": discovery_result.get("llm_analysis", {}),
        "search_results": discovery_result.get("search_results", {}),  # Full raw response
        "organic_results_count": len(discovery_result.get("search_results", {}).get("organic_results", [])),
        "detected_country": discovery_result.get("detected_country"),
        "country_confidence": discovery_result.get("country_confidence", 0.0),
        "country_signals": discovery_result.get("country_signals", []),
    }

    # Save social media URLs found via phone/address match (not name match).
    # These can be used for further enrichment even when the primary URL differs.
    if social_urls:
        current_raw_data["social_urls"] = social_urls
        logger.info(
            f"💾 Saved social URLs for {business.name}: "
            + ", ".join(f"{k}={v}" for k, v in social_urls.items())
        )

    business.raw_data = current_raw_data

    db.commit()

    # Queue Facebook activity check — the organic results we just saved may
    # contain a Facebook page URL for this business.
    _queue_facebook_check(business, current_raw_data)

    # If the business is outside our supported countries, don't queue for validation
    if not is_supported_country:
        logger.warning(
            f"🚫 Skipping validation queue for {business.name!r} "
            f"— detected country {business.country!r} is not supported."
        )
        return {
            "business_id": str(business.id),
            "status": "geo_mismatch",
            "country": business.country,
            "url": found_url,
            "queued_for_validation": False
        }
    
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

    # Apply detected country (may update business.country)
    is_supported_country = _apply_detected_country(business, discovery_result)

    # Save complete ScrapingDog response to raw_data (even when no URL found)
    current_raw_data = business.raw_data or {}
    current_raw_data["scrapingdog_discovery"] = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": discovery_result.get("query", ""),
        "url_found": None,
        "confidence": confidence,
        "reasoning": discovery_result.get("reasoning", ""),
        "llm_model": discovery_result.get("llm_model", ""),
        "llm_analysis": discovery_result.get("llm_analysis", {}),
        "search_results": discovery_result.get("search_results", {}),  # Full raw response
        "organic_results_count": len(discovery_result.get("search_results", {}).get("organic_results", [])),
        "detected_country": discovery_result.get("detected_country"),
        "country_confidence": discovery_result.get("country_confidence", 0.0),
        "country_signals": discovery_result.get("country_signals", []),
    }
    social_urls = discovery_result.get("social_urls", {})
    if social_urls:
        current_raw_data["social_urls"] = social_urls
        logger.info(
            f"💾 Saved social URLs (no-website path) for {business.name}: "
            + ", ".join(f"{k}={v}" for k, v in social_urls.items())
        )
    business.raw_data = current_raw_data

    # Even when no website was found, the organic results may contain a
    # Facebook page we can use for activity enrichment.
    _queue_facebook_check(business, current_raw_data)

    # ----------------------------------------------------------------
    # GEO MISMATCH — business is confirmed non-US; do NOT mark as
    # triple_verified so it never enters the generation queue.
    # ----------------------------------------------------------------
    if not is_supported_country:
        detected_country = discovery_result.get("detected_country") or business.country
        logger.warning(
            f"🚫 Business {business.name!r} confirmed as non-US "
            f"({detected_country}). Marking as geo_mismatch — "
            f"will NOT be queued for site generation."
        )
        business.website_validation_status = ValidationState.GEO_MISMATCH.value
        business.website_validated_at = datetime.utcnow()

        business.website_metadata = metadata_service.record_discovery_attempt(
            business.website_metadata,
            method="scrapingdog",
            found_url=False,
            notes=f"Geo mismatch: business detected as {detected_country}, not US"
        )

        business.website_validation_result = {
            "verdict": "geo_mismatch",
            "detected_country": detected_country,
            "country_confidence": discovery_result.get("country_confidence", 0.0),
            "country_signals": discovery_result.get("country_signals", []),
            "reasoning": f"Business detected as {detected_country} — outside supported countries (US only)",
            "confidence": discovery_result.get("country_confidence", 0.0),
        }

        db.commit()

        return {
            "business_id": str(business.id),
            "status": "geo_mismatch",
            "country": detected_country,
            "triple_verified": False
        }

    # ----------------------------------------------------------------
    # NORMAL PATH — confirmed no website, US business
    # ----------------------------------------------------------------
    # Record discovery attempt
    business.website_metadata = metadata_service.record_discovery_attempt(
        business.website_metadata,
        method="scrapingdog",
        found_url=False,
        notes="ScrapingDog found no valid website"
    )
    
    # Mark as confirmed missing
    business.website_validation_status = ValidationState.CONFIRMED_NO_WEBSITE.value
    business.website_validated_at = datetime.utcnow()

    # Save complete result
    business.website_validation_result = {
        "verdict": "confirmed_no_website",
        "detected_country": discovery_result.get("detected_country"),
        "country_confidence": discovery_result.get("country_confidence", 0.0),
        "country_signals": discovery_result.get("country_signals", []),
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


def _queue_facebook_check(business: Business, raw_data: dict) -> None:
    """
    Queue a Facebook activity check if the ScrapingDog organic results
    contain a Facebook URL and the business hasn't been checked yet.

    Called immediately after ``scrapingdog_discovery`` is written to
    ``raw_data`` and committed, so the task worker sees the latest data.
    """
    from core.config import get_settings
    settings = get_settings()
    if not settings.ENABLE_FACEBOOK_ACTIVITY_CHECK:
        return
    if business.last_facebook_post_date is not None:
        return

    from services.activity import extract_facebook_url_from_raw
    fb_url = extract_facebook_url_from_raw(raw_data)
    if not fb_url:
        return

    try:
        from tasks.activity_tasks import fetch_facebook_activity
        fetch_facebook_activity.delay(str(business.id))
        logger.info(
            "Queued Facebook activity check for %s: %s",
            business.name,
            fb_url,
        )
    except Exception as exc:
        logger.warning(
            "Failed to queue Facebook activity check for %s: %s",
            business.name,
            exc,
        )


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
