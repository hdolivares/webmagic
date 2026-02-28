"""
Pure functions for evaluating business activity signals.

All functions are stateless and side-effect free — they operate entirely
on in-memory data and never touch the database or any external service.
This makes them trivial to unit-test and safe to call from any context.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .constants import (
    REVIEW_SAFE_DAYS,
    REVIEW_CAUTION_DAYS,
    REVIEW_CUTOFF_DAYS,
    FACEBOOK_CUTOFF_DAYS,
    REVIEW_ACTIVE_BONUS,
    REVIEW_INACTIVE_PENALTY,
    ActivityStatus,
)

logger = logging.getLogger(__name__)


# ── Date extraction ──────────────────────────────────────────────────────────

def extract_last_review_date(reviews_data: list[dict[str, Any]]) -> Optional[datetime]:
    """
    Return the UTC datetime of the most recent review in *reviews_data*.

    The scraper normalises individual review timestamps into the ``date``
    field of each review dict (sourced from ``review_datetime_utc`` in the
    raw Outscraper response).  This function finds the maximum.

    Args:
        reviews_data: Normalised review list, e.g.
            ``[{"text": "...", "rating": 5, "date": "2024-01-15T10:30:00Z"}]``

    Returns:
        Timezone-aware UTC datetime of the newest review, or ``None`` when
        the list is empty or no parseable dates are found.
    """
    if not reviews_data:
        return None

    latest: Optional[datetime] = None

    for review in reviews_data:
        raw_date = review.get("date")
        if not raw_date:
            continue

        parsed = _parse_date_string(raw_date)
        if parsed and (latest is None or parsed > latest):
            latest = parsed

    return latest


def _parse_date_string(raw: str) -> Optional[datetime]:
    """
    Parse an ISO-8601 date string into a timezone-aware UTC datetime.

    Handles the two formats produced by the Outscraper scraper:
    - Full ISO-8601: ``"2024-01-15T10:30:00Z"``
    - Date-only:     ``"2024-01-15"``
    """
    if not raw:
        return None

    formats = (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(raw[:len(fmt)], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    logger.debug("Could not parse review date string: %r", raw)
    return None


# ── Score modifier ───────────────────────────────────────────────────────────

def score_modifier_from_review_date(last_review_date: Optional[datetime]) -> int:
    """
    Compute the qualification score modifier driven by review recency.

    Returns:
        ``+REVIEW_ACTIVE_BONUS``   when the last review is within REVIEW_SAFE_DAYS.
        ``-REVIEW_INACTIVE_PENALTY`` when older than REVIEW_CAUTION_DAYS.
        ``0``                       when there is no date (no signal → no penalty).
    """
    if last_review_date is None:
        return 0

    days_ago = _days_since(last_review_date)

    if days_ago <= REVIEW_SAFE_DAYS:
        return REVIEW_ACTIVE_BONUS
    if days_ago > REVIEW_CAUTION_DAYS:
        return -REVIEW_INACTIVE_PENALTY
    return 0


# ── Activity assessment ──────────────────────────────────────────────────────

_CLOSED_STATUSES = {"CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY"}


def is_business_closed(business: Any) -> bool:
    """
    Return True if the business is explicitly marked closed on Google Maps.

    Checks the dedicated ``business_status`` model column first, then falls
    back to ``raw_data['business_status']`` for records scraped before the
    column was backfilled.  Both sources are compared case-insensitively.

    This is the single canonical check used to short-circuit upstream tasks
    (ScrapingDog discovery, Facebook enrichment) so we don't spend API credits
    on businesses we will never generate a site for.
    """
    status = (
        getattr(business, "business_status", None)
        or (getattr(business, "raw_data", None) or {}).get("business_status")
        or ""
    ).upper().strip()
    return status in _CLOSED_STATUSES


def compute_activity_status(
    last_review_date: Optional[datetime],
    last_facebook_post_date: Optional[datetime] = None,
    business_status: Optional[str] = None,
    review_count: Optional[int] = None,
) -> ActivityStatus:
    """
    Determine whether a business is eligible for site generation, and what
    qualification score modifier to apply.

    Rules (evaluated in priority order):

    0. **business_status is CLOSED_TEMPORARILY or CLOSED_PERMANENTLY** → ineligible.
       Google explicitly marks the business as closed — do not generate.

    1. **review_count == 0 AND last_facebook_post_date is None** → ineligible.
       Zero Google reviews with no verifiable Facebook activity means we cannot
       confirm the business is real or still operating.

    2. **Last review > REVIEW_CUTOFF_DAYS** → ineligible.
       This is the primary and most reliable activity signal.

    3. **No review date AND last Facebook post > FACEBOOK_CUTOFF_DAYS** → ineligible.
       Facebook is used only as a secondary signal.  When review data exists
       we trust it over Facebook activity.

    4. **Otherwise** → eligible.  The score modifier from review recency is
       still applied so the lead scorer can prioritise active businesses.

    Args:
        last_review_date:         Most recent Google review date (UTC), or None.
        last_facebook_post_date:  Most recent Facebook post date (UTC), or None.
        business_status:          Raw Outscraper status string, e.g. "OPERATIONAL",
                                  "CLOSED_TEMPORARILY", "CLOSED_PERMANENTLY".
        review_count:             Total number of Google reviews (0 = no reviews).

    Returns:
        An :class:`ActivityStatus` instance summarising the decision.
    """
    review_days = _days_since(last_review_date)
    facebook_days = _days_since(last_facebook_post_date)
    modifier = score_modifier_from_review_date(last_review_date)
    normalised_status = (business_status or "").upper().strip()

    # ── Rule 0: business explicitly marked as closed ──────────────────────────
    if normalised_status in _CLOSED_STATUSES:
        return ActivityStatus(
            is_eligible=False,
            ineligibility_reason="business_closed",
            score_modifier=0,
            last_review_days_ago=review_days,
            last_facebook_days_ago=facebook_days,
            detail=f"Business is marked as {normalised_status} on Google Maps",
        )

    # ── Rule 1: zero reviews + no Facebook activity ───────────────────────────
    # Only applies when review_count is explicitly 0 (not None/unknown).
    if review_count == 0 and last_facebook_post_date is None:
        return ActivityStatus(
            is_eligible=False,
            ineligibility_reason="unverifiable_no_reviews_no_facebook",
            score_modifier=0,
            last_review_days_ago=review_days,
            last_facebook_days_ago=facebook_days,
            detail=(
                "Business has 0 Google reviews and no verifiable Facebook activity — "
                "cannot confirm the business is real or still operating"
            ),
        )

    # ── Rule 2: stale review data ─────────────────────────────────────────────
    if review_days is not None and review_days > REVIEW_CUTOFF_DAYS:
        return ActivityStatus(
            is_eligible=False,
            ineligibility_reason="inactive_no_recent_reviews",
            score_modifier=modifier,
            last_review_days_ago=review_days,
            last_facebook_days_ago=facebook_days,
            detail=(
                f"Last review was {review_days} days ago "
                f"(cutoff: {REVIEW_CUTOFF_DAYS} days)"
            ),
        )

    # ── Rule 3: no review signal + stale Facebook ─────────────────────────────
    if (
        review_days is None
        and facebook_days is not None
        and facebook_days > FACEBOOK_CUTOFF_DAYS
    ):
        return ActivityStatus(
            is_eligible=False,
            ineligibility_reason="inactive_no_facebook_posts",
            score_modifier=0,
            last_review_days_ago=None,
            last_facebook_days_ago=facebook_days,
            detail=(
                f"No review data and last Facebook post was {facebook_days} days ago "
                f"(cutoff: {FACEBOOK_CUTOFF_DAYS} days)"
            ),
        )

    # ── Rule 4: eligible ──────────────────────────────────────────────────────
    if review_days is not None:
        detail = f"Last review {review_days} days ago — eligible (modifier: {modifier:+d})"
    elif facebook_days is not None:
        detail = f"No review data; last Facebook post {facebook_days} days ago — eligible"
    else:
        detail = "No activity signals available — eligible by default"

    return ActivityStatus(
        is_eligible=True,
        ineligibility_reason=None,
        score_modifier=modifier,
        last_review_days_ago=review_days,
        last_facebook_days_ago=facebook_days,
        detail=detail,
    )


# ── Internal helpers ─────────────────────────────────────────────────────────

def _days_since(dt: Optional[datetime]) -> Optional[int]:
    """Return the number of whole days between *dt* and now (UTC), or None."""
    if dt is None:
        return None
    now = datetime.now(tz=timezone.utc)
    # Ensure dt is timezone-aware for comparison
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    return max(0, delta.days)
