"""
Outreach channel and phone-validation constants.

Single source of truth for outreach_channel values used after triple-validation.
Used by: phone validation service, eligibility queries, queue guard.
"""
from enum import Enum
from typing import Set


class OutreachChannel(str, Enum):
    """
    Preferred outreach channel after phone validation.

    Set by the phone validation job for triple-validated (no-website) businesses.
    Determines whether the business is eligible for current site generation or
    saved for the future call-later flow (generate site + call).
    """
    SMS = "sms"           # At least one SMS-capable phone; eligible for generation
    EMAIL = "email"       # Has email (and no SMS or we prefer email); eligible for generation
    CALL_LATER = "call_later"  # No valid SMS number and no email; save for future calling

    @classmethod
    def eligible_for_generation(cls, channel: str | None) -> bool:
        """
        True if outreach_channel allows queueing for website generation.

        Excludes CALL_LATER; allows SMS, EMAIL, and None (backward compat).
        """
        if channel is None:
            return True
        return channel in {cls.SMS.value, cls.EMAIL.value}

    @classmethod
    def is_call_later(cls, channel: str | None) -> bool:
        """True if business is in the call-later queue."""
        return channel == cls.CALL_LATER.value

    @classmethod
    def valid_values(cls) -> Set[str]:
        """All valid outreach_channel values."""
        return {e.value for e in cls}
