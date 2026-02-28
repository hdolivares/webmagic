"""
Business activity analysis services.

Determines whether a business is currently active based on review recency
and social media signals, and gates site generation accordingly.
"""
from .constants import (
    REVIEW_SAFE_DAYS,
    REVIEW_CAUTION_DAYS,
    REVIEW_CUTOFF_DAYS,
    FACEBOOK_CUTOFF_DAYS,
    REVIEW_ACTIVE_BONUS,
    REVIEW_INACTIVE_PENALTY,
    ActivityStatus,
)
from .analyzer import (
    extract_last_review_date,
    score_modifier_from_review_date,
    compute_activity_status,
)
from .facebook_scraper import extract_facebook_url_from_raw

__all__ = [
    # Constants
    "REVIEW_SAFE_DAYS",
    "REVIEW_CAUTION_DAYS",
    "REVIEW_CUTOFF_DAYS",
    "FACEBOOK_CUTOFF_DAYS",
    "REVIEW_ACTIVE_BONUS",
    "REVIEW_INACTIVE_PENALTY",
    "ActivityStatus",
    # Functions
    "extract_last_review_date",
    "score_modifier_from_review_date",
    "compute_activity_status",
    "extract_facebook_url_from_raw",
]
