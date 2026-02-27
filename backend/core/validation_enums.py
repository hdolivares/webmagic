"""
Validation System Enums and Constants.

Centralized definitions for validation states, recommendations, and URL sources.
Follows best practices: Single source of truth, type safety, clear documentation.
"""
from enum import Enum
from typing import Set


class ValidationState(str, Enum):
    """
    Website validation status for businesses.
    
    Each state represents a clear, actionable status that determines next steps.
    States are organized by category for clarity.
    """
    
    # ============================================================================
    # INITIAL STATES - Entry points
    # ============================================================================
    PENDING = "pending"  # Not yet validated, needs processing
    
    # ============================================================================
    # SUCCESS STATES - Valid websites found
    # ============================================================================
    VALID_OUTSCRAPER = "valid_outscraper"  # Valid URL from Outscraper
    VALID_SCRAPINGDOG = "valid_scrapingdog"  # Valid URL from ScrapingDog search
    VALID_MANUAL = "valid_manual"  # Manually verified URL
    
    # ============================================================================
    # DISCOVERY PIPELINE STATES - In-progress discovery
    # ============================================================================
    NEEDS_DISCOVERY = "needs_discovery"  # URL rejected or missing, needs ScrapingDog
    DISCOVERY_QUEUED = "discovery_queued"  # ScrapingDog task queued
    DISCOVERY_IN_PROGRESS = "discovery_in_progress"  # ScrapingDog search running
    
    # ============================================================================
    # FAILURE STATES - Invalid or problematic URLs
    # ============================================================================
    INVALID_TECHNICAL = "invalid_technical"  # Technical issues (404, timeout, broken)
    INVALID_TYPE = "invalid_type"  # Wrong type (PDF, directory, aggregator)
    INVALID_MISMATCH = "invalid_mismatch"  # URL doesn't match business
    
    # ============================================================================
    # TERMINAL STATES - Final outcomes
    # ============================================================================
    CONFIRMED_NO_WEBSITE = "confirmed_no_website"  # After all discovery, no website
    GEO_MISMATCH = "geo_mismatch"  # Business confirmed to be outside target country (non-US)
    ERROR = "error"  # Validation process failed
    
    @classmethod
    def is_valid_state(cls, state: str) -> bool:
        """Check if state is a valid validation state."""
        return state in cls._value2member_map_
    
    @classmethod
    def is_success_state(cls, state: str) -> bool:
        """Check if state represents a successful validation."""
        return state in {
            cls.VALID_OUTSCRAPER.value,
            cls.VALID_SCRAPINGDOG.value,
            cls.VALID_MANUAL.value
        }
    
    @classmethod
    def needs_discovery_action(cls, state: str) -> bool:
        """Check if state requires discovery action."""
        return state in {
            cls.NEEDS_DISCOVERY.value,
            cls.DISCOVERY_QUEUED.value
        }
    
    @classmethod
    def is_terminal_state(cls, state: str) -> bool:
        """Check if state is a final state (no further action needed)."""
        return state in {
            cls.VALID_OUTSCRAPER.value,
            cls.VALID_SCRAPINGDOG.value,
            cls.VALID_MANUAL.value,
            cls.CONFIRMED_NO_WEBSITE.value,
            cls.GEO_MISMATCH.value,
            cls.ERROR.value
        }


class ValidationRecommendation(str, Enum):
    """
    Actions to take based on validation results.
    
    Recommendations drive the validation pipeline and determine next steps.
    """
    
    KEEP_URL = "keep_url"  # URL is valid, keep it
    TRIGGER_SCRAPINGDOG = "trigger_scrapingdog"  # Clear URL and queue ScrapingDog
    RETRY_VALIDATION = "retry_validation"  # Technical failure, retry later
    MARK_NO_WEBSITE = "mark_no_website"  # Confirmed no website after all attempts
    MANUAL_REVIEW = "manual_review"  # Uncertain case, needs human review
    
    @classmethod
    def requires_discovery(cls, recommendation: str) -> bool:
        """Check if recommendation requires ScrapingDog discovery."""
        return recommendation == cls.TRIGGER_SCRAPINGDOG.value


class URLSource(str, Enum):
    """
    Source of website URL.
    
    Tracks where URLs come from for audit trail and quality analysis.
    """
    
    NONE = "none"  # No URL source
    OUTSCRAPER = "outscraper"  # From Outscraper GMB scraping
    SCRAPINGDOG = "scrapingdog"  # From ScrapingDog Google search
    MANUAL = "manual"  # Manually entered/corrected
    BACKFILL = "backfill"  # From data backfill process
    
    @classmethod
    def is_automated(cls, source: str) -> bool:
        """Check if source is automated (not manual)."""
        return source in {cls.OUTSCRAPER.value, cls.SCRAPINGDOG.value}


class InvalidURLReason(str, Enum):
    """
    Specific reasons why a URL is invalid.
    
    Provides granular categorization for analytics and decision-making.
    """
    
    # Type Issues
    DIRECTORY = "directory"  # Yelp, Yellow Pages, etc.
    AGGREGATOR = "aggregator"  # Review sites, listing sites
    SOCIAL_MEDIA = "social_media"  # Facebook, LinkedIn, Instagram
    FILE = "file"  # PDF, ZIP, etc.
    FILE_STORAGE = "file_storage"  # Google Drive, Dropbox
    
    # Technical Issues
    NOT_FOUND = "not_found"  # 404 error
    TIMEOUT = "timeout"  # Page load timeout
    SERVER_ERROR = "server_error"  # 5xx errors
    SSL_ERROR = "ssl_error"  # Certificate issues
    
    # Content Issues
    PLACEHOLDER = "placeholder"  # Under construction, coming soon
    PARKING = "parking"  # Domain parking page
    EMPTY = "empty"  # No content
    
    # Matching Issues
    WRONG_BUSINESS = "wrong_business"  # Different business name
    WRONG_LOCATION = "wrong_location"  # Different city/state
    NO_CONTACT = "no_contact"  # No contact information
    
    @classmethod
    def is_type_issue(cls, reason: str) -> bool:
        """Check if reason is a type-related issue."""
        return reason in {
            cls.DIRECTORY.value,
            cls.AGGREGATOR.value,
            cls.SOCIAL_MEDIA.value,
            cls.FILE.value,
            cls.FILE_STORAGE.value
        }
    
    @classmethod
    def is_technical_issue(cls, reason: str) -> bool:
        """Check if reason is a technical issue."""
        return reason in {
            cls.NOT_FOUND.value,
            cls.TIMEOUT.value,
            cls.SERVER_ERROR.value,
            cls.SSL_ERROR.value
        }


# ============================================================================
# DOMAIN CATEGORIZATION - For intelligent decision-making
# ============================================================================

DIRECTORY_DOMAINS: Set[str] = {
    'yelp.com',
    'yellowpages.com',
    'whitepages.com',
    'superpages.com',
    'manta.com',
    'citysearch.com',
    'local.com',
    'mapquest.com',
    'dexknows.com',
    # Generic plumber/contractor aggregator directories
    '1001plumbers.com',
    '411locals.com',
    'chamberofcommerce.com',
    'merchantcircle.com',
    'brownbook.net',
    'n49.com',
    'hotfrog.com',
    'cylex.us',
    'find-us-here.com',
    'tupalo.com',
    'wheree.com',       # Business listing aggregator
    'bizapedia.com',
    'bizguru.us',
    'localstar.com',
    'showmelocal.com',
}

AGGREGATOR_DOMAINS: Set[str] = {
    'bbb.org',
    'tripadvisor.com',
    'foursquare.com',
    'zomato.com',
    'opentable.com',
    'angieslist.com',
    'checkbook.org',
    'expertise.com',
    'bark.com',
    'networx.com',
    'buildzoom.com',
    'contractortalk.com',
}

SOCIAL_MEDIA_DOMAINS: Set[str] = {
    'facebook.com',
    'instagram.com',
    'twitter.com',
    'x.com',
    'linkedin.com',
    'youtube.com',
    'tiktok.com',
    'pinterest.com',
    'nextdoor.com',     # Community social network, not a business website
    'snapchat.com',
    'threads.net',
    'reddit.com',
    'tumblr.com',
    'blogger.com',      # Free blog host — usually not a real business site
}

SERVICE_PLATFORMS: Set[str] = {
    'angi.com',
    'homeadvisor.com',
    'thumbtack.com',
    'houzz.com',
    'porch.com',
    'taskrabbit.com',
    'fiverr.com',
    'upwork.com',
    'hireahelper.com',
    'servicemagic.com',
    'improveit360.com',
    'contractor.com',
    'prolocal.com',
    'servicetitan.com',
}

FILE_STORAGE_DOMAINS: Set[str] = {
    'drive.google.com',
    'docs.google.com',
    'dropbox.com',
    'onedrive.live.com',
    '1drv.ms',
    'box.com',
    'icloud.com',
    'mediafire.com',
    'mega.nz',
    'wetransfer.com',
}

# Combined set of all non-business domains
NON_BUSINESS_DOMAINS: Set[str] = (
    DIRECTORY_DOMAINS |
    AGGREGATOR_DOMAINS |
    SOCIAL_MEDIA_DOMAINS |
    SERVICE_PLATFORMS |
    FILE_STORAGE_DOMAINS
)


def categorize_url_domain(url: str) -> str | None:
    """
    Categorize a URL's domain.
    
    Args:
        url: URL to categorize
        
    Returns:
        Category string or None if not in known categories
    """
    from urllib.parse import urlparse
    
    try:
        domain = urlparse(url).netloc.lower()
        # Remove www. prefix
        domain = domain.replace('www.', '')
        
        if domain in DIRECTORY_DOMAINS:
            return InvalidURLReason.DIRECTORY.value
        elif domain in AGGREGATOR_DOMAINS:
            return InvalidURLReason.AGGREGATOR.value
        elif domain in SOCIAL_MEDIA_DOMAINS:
            return InvalidURLReason.SOCIAL_MEDIA.value
        elif domain in SERVICE_PLATFORMS:
            return InvalidURLReason.AGGREGATOR.value
        elif domain in FILE_STORAGE_DOMAINS:
            return InvalidURLReason.FILE_STORAGE.value
        
        return None
    except Exception:
        return None


# ============================================================================
# VALIDATION CONFIGURATION
# ============================================================================

class ValidationConfig:
    """Configuration constants for validation system."""
    
    # Retry configuration
    MAX_VALIDATION_RETRIES = 3
    RETRY_BACKOFF_HOURS = [1, 6, 24]  # Exponential backoff
    
    # Discovery configuration
    MAX_SCRAPINGDOG_ATTEMPTS = 1  # Only try ScrapingDog once per business
    
    # Timeouts
    PLAYWRIGHT_TIMEOUT_SECONDS = 30
    VALIDATION_TASK_TIMEOUT_SECONDS = 300  # 5 minutes
    
    # Confidence thresholds
    MIN_CONFIDENCE_FOR_VALID = 0.7
    MIN_CONFIDENCE_FOR_DISCOVERY = 0.5  # Lower threshold before giving up
