"""
Phone validation service for triple-validated businesses.

Runs after a business is confirmed eligible for website generation (no website).
Collects all contact numbers, finds the first SMS-capable one; sets outreach_channel
(sms | email | call_later). Caller persists the result to the business.

Single responsibility: phone/SMS eligibility logic. No Celery, HTTP, or DB session.
Uses injectable NumberLookupService for testability.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional, Protocol, Tuple

from core.outreach_enums import OutreachChannel
from services.sms.phone_validator import PhoneValidator
from services.sms.number_lookup import NumberLookupService, NumberLookupResult

logger = logging.getLogger(__name__)


# Raw data keys that may contain phone number(s)
_RAW_DATA_PHONE_KEYS = ("phone", "phones")
_DEFAULT_REGION = "US"


class LookupServiceProtocol(Protocol):
    """Protocol for number lookup (allows injecting a stub in tests)."""

    async def lookup(self, phone: str) -> NumberLookupResult:
        ...


@dataclass(frozen=True)
class PhoneValidationResult:
    """
    Result of validating a business's phone(s) for outreach.

    Caller applies these to the Business record and commits.
    """

    outreach_channel: str  # OutreachChannel.SMS | EMAIL | CALL_LATER value
    chosen_phone: Optional[str]  # E.164 format; None if call_later or email-only
    phone_line_type: Optional[str]  # mobile | landline | etc.; None if no chosen phone
    phone_validated_at: datetime


def collect_phone_candidates(business: Any) -> List[str]:
    """
    Collect all phone number candidates from business.phone and raw_data.

    Normalizes and dedupes; returns only valid E.164-formatted numbers.
    Order: primary phone first, then any from raw_data.

    Args:
        business: Object with .phone (optional str) and .raw_data (optional dict).

    Returns:
        List of E.164-formatted phone strings (may be empty).
    """
    candidates: List[str] = []
    seen: set[str] = set()

    # Primary phone
    primary = getattr(business, "phone", None)
    if primary and isinstance(primary, str) and primary.strip():
        formatted = _normalize_phone(primary)
        if formatted and formatted not in seen:
            candidates.append(formatted)
            seen.add(formatted)

    # From raw_data
    raw = getattr(business, "raw_data", None) or {}
    if not isinstance(raw, dict):
        return candidates

    for key in _RAW_DATA_PHONE_KEYS:
        value = raw.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            formatted = _normalize_phone(value)
            if formatted and formatted not in seen:
                candidates.append(formatted)
                seen.add(formatted)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    formatted = _normalize_phone(item)
                    if formatted and formatted not in seen:
                        candidates.append(formatted)
                        seen.add(formatted)

    return candidates


def _normalize_phone(phone: str, region: str = _DEFAULT_REGION) -> Optional[str]:
    """Return E.164 format or None if invalid."""
    is_valid, formatted, _ = PhoneValidator.validate_and_format(phone, region)
    return formatted if is_valid else None


async def find_first_sms_capable(
    candidates: List[str],
    lookup_service: LookupServiceProtocol,
) -> Optional[Tuple[str, str]]:
    """
    Look up each candidate; return the first that is SMS-capable.

    Args:
        candidates: List of E.164 phone strings.
        lookup_service: Injectable lookup service (e.g. NumberLookupService).

    Returns:
        (phone, line_type) for first SMS-capable number, or None if none.
    """
    for phone in candidates:
        try:
            result = await lookup_service.lookup(phone)
            if result.is_sms_capable:
                return (phone, result.line_type)
            logger.debug(
                "Phone %s not SMS-capable: line_type=%s",
                phone[:6] + "...",
                result.line_type,
            )
        except Exception as e:
            logger.warning("Lookup failed for %s: %s", phone[:6] + "...", e)
            continue
    return None


def determine_outreach_channel(has_sms_capable: bool, has_email: bool) -> str:
    """
    Determine outreach_channel from phone and email availability.

    Args:
        has_sms_capable: At least one phone passed lookup as SMS-capable.
        has_email: Business has a non-empty email.

    Returns:
        OutreachChannel value: sms | email | call_later.
    """
    if has_sms_capable:
        return OutreachChannel.SMS.value
    if has_email:
        return OutreachChannel.EMAIL.value
    return OutreachChannel.CALL_LATER.value


def _has_email(business: Any) -> bool:
    """True if business has a non-empty email."""
    email = getattr(business, "email", None)
    return bool(email and isinstance(email, str) and email.strip())


async def validate_business_outreach(
    business: Any,
    lookup_service: LookupServiceProtocol,
) -> PhoneValidationResult:
    """
    Run full phone validation for a triple-validated business.

    Collects all contact numbers, finds first SMS-capable; determines
    outreach_channel. Does not mutate business or DB; caller applies result.

    Args:
        business: Object with .phone, .raw_data, .email (e.g. Business model).
        lookup_service: Injectable lookup service.

    Returns:
        PhoneValidationResult to apply to business and persist.
    """
    now = datetime.now(timezone.utc)
    candidates = collect_phone_candidates(business)
    has_email = _has_email(business)

    if not candidates:
        channel = determine_outreach_channel(False, has_email)
        return PhoneValidationResult(
            outreach_channel=channel,
            chosen_phone=None,
            phone_line_type=None,
            phone_validated_at=now,
        )

    sms_result = await find_first_sms_capable(candidates, lookup_service)
    if sms_result:
        phone, line_type = sms_result
        channel = determine_outreach_channel(True, has_email)
        return PhoneValidationResult(
            outreach_channel=channel,
            chosen_phone=phone,
            phone_line_type=line_type,
            phone_validated_at=now,
        )

    channel = determine_outreach_channel(False, has_email)
    return PhoneValidationResult(
        outreach_channel=channel,
        chosen_phone=None,
        phone_line_type=None,
        phone_validated_at=now,
    )
