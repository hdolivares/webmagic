"""
Number Lookup Service.

Single responsibility: determine a phone number's line type (mobile, landline,
VoIP, toll-free) via the Telnyx Number Lookup API.

This service is stateless and has no DB dependency — caching / persistence
is handled by the caller (CampaignService writes results back to Business).

Line-type definitions:
  mobile       → can receive SMS ✓
  voip         → uncertain, allow sending (log warning)
  landline     → cannot receive SMS ✗
  toll_free    → cannot receive SMS ✗
  premium_rate → cannot receive SMS ✗
  unknown      → uncertain, allow sending (API error or unsupported number)

Author: WebMagic Team
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)

_LOOKUP_URL = "https://api.telnyx.com/v2/number_lookup/{phone}"

# Line types that definitively cannot receive SMS
_BLOCKED_LINE_TYPES: frozenset[str] = frozenset({"landline", "toll_free", "premium_rate"})

# Line types that can receive SMS (includes voip as "uncertain but allow")
_ALLOWED_LINE_TYPES: frozenset[str] = frozenset({"mobile", "voip", "fixed_voip", "unknown"})


@dataclass(frozen=True)
class NumberLookupResult:
    """Immutable result from a Telnyx number lookup."""

    phone: str
    line_type: str           # mobile | landline | voip | toll_free | premium_rate | unknown
    carrier: Optional[str]
    is_sms_capable: bool     # False only for definitively blocked line types
    is_definitive: bool      # True when the API gave a clear mobile/landline answer
    lookup_successful: bool  # False when the API call itself failed


class NumberLookupService:
    """
    Queries Telnyx to determine whether a phone number can receive SMS.

    Usage::

        service = NumberLookupService()
        result = await service.lookup("+15551234567")
        if not result.is_sms_capable:
            raise ValidationException(f"Cannot send SMS to {result.line_type}: {phone}")
    """

    async def lookup(self, phone: str) -> NumberLookupResult:
        """
        Look up a phone number's line type via Telnyx.

        Args:
            phone: E.164 formatted phone number (e.g. '+15551234567')

        Returns:
            NumberLookupResult — never raises; falls back to 'unknown / allowed'
            on any API error so a lookup failure never silently blocks sends.
        """
        settings = get_settings()
        url = _LOOKUP_URL.format(phone=phone)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {settings.TELNYX_API_KEY}"},
                )

            if response.status_code != 200:
                logger.warning(
                    "Number lookup HTTP %s for %s — allowing send (fail-open)",
                    response.status_code,
                    phone,
                )
                return self._fallback(phone)

            data = response.json().get("data", {})
            lti = data.get("line_type_intelligence") or {}
            raw_type = (lti.get("type") or "unknown").lower().replace("-", "_")
            carrier = lti.get("name") or None

            is_blocked = raw_type in _BLOCKED_LINE_TYPES
            is_definitive = raw_type in (_BLOCKED_LINE_TYPES | frozenset({"mobile"}))

            logger.info(
                "Number lookup %s → line_type=%s carrier=%s sms_capable=%s",
                phone, raw_type, carrier, not is_blocked,
            )

            return NumberLookupResult(
                phone=phone,
                line_type=raw_type,
                carrier=carrier,
                is_sms_capable=not is_blocked,
                is_definitive=is_definitive,
                lookup_successful=True,
            )

        except Exception as exc:
            logger.error("Number lookup error for %s: %s — allowing send", phone, exc)
            return self._fallback(phone)

    @staticmethod
    def _fallback(phone: str) -> NumberLookupResult:
        """Return a permissive unknown result when the API is unreachable."""
        return NumberLookupResult(
            phone=phone,
            line_type="unknown",
            carrier=None,
            is_sms_capable=True,
            is_definitive=False,
            lookup_successful=False,
        )
