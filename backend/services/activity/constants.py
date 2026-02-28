"""
Thresholds and scoring modifiers for business activity signals.

All day-count values live here so they can be tuned in one place
without touching business logic.
"""
from dataclasses import dataclass
from typing import Optional


# ── Review recency thresholds ────────────────────────────────────────────────

REVIEW_SAFE_DAYS: int = 365
"""Businesses with a review within this many days are considered active."""

REVIEW_CAUTION_DAYS: int = 548
"""Reviews older than this (≈ 18 months) enter the caution zone."""

REVIEW_CUTOFF_DAYS: int = 548
"""Businesses whose last review is older than this are ineligible for
site generation.  Kept equal to REVIEW_CAUTION_DAYS so the boundary is
clear: once you're in the caution zone you're also cut off."""


# ── Facebook post recency threshold ──────────────────────────────────────────

FACEBOOK_CUTOFF_DAYS: int = 730
"""Last Facebook post older than this (≈ 2 years) is treated as an
inactivity signal.  Used only as a *secondary* signal — we do not skip
generation on Facebook alone."""


# ── Qualification score modifiers (applied by LeadQualifier) ─────────────────

REVIEW_ACTIVE_BONUS: int = 5
"""Bonus added to the qualification score when the last review is within
REVIEW_SAFE_DAYS."""

REVIEW_INACTIVE_PENALTY: int = 25
"""Penalty subtracted from the qualification score when the last review is
older than REVIEW_CAUTION_DAYS.  The business may still qualify if other
signals are strong enough."""


# ── Activity result dataclass ─────────────────────────────────────────────────

@dataclass(frozen=True)
class ActivityStatus:
    """
    Immutable result of an activity assessment for a single business.

    Consumed by:
    - ``generate_site_for_business`` — checks ``is_eligible`` before generating
    - ``LeadQualifier.qualify``       — applies ``score_modifier``
    """

    is_eligible: bool
    """False means the business should be skipped during site generation."""

    ineligibility_reason: Optional[str]
    """Machine-readable reason code when ``is_eligible`` is False,
    e.g. ``"inactive_no_recent_reviews"`` or ``"inactive_no_facebook_posts"``."""

    score_modifier: int
    """Points to add (positive) or subtract (negative) from the lead score."""

    last_review_days_ago: Optional[int]
    """Age of the most recent review in days, or None if unknown."""

    last_facebook_days_ago: Optional[int]
    """Age of the most recent Facebook post in days, or None if unknown."""

    detail: str
    """Human-readable summary for logs and the admin UI."""
