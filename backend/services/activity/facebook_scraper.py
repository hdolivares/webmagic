"""
Scrapes public Facebook business pages for activity and contact signals.

Uses ScrapingDog's General Web Scraping API with JavaScript rendering
(``dynamic=true``).  Credit cost: **5 credits per request** — the same as
a Google Search lookup already used in this codebase.

Facebook embeds structured data in ``<script>`` tags as inline JSON.  We
scan for known field names rather than parsing the full DOM so extraction
is fast and resilient to Facebook's frequent layout changes.

Extracted signals per page fetch:
    - Last post date (activity signal)
    - Phone number
    - Email address
    - Business website URL
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

import aiohttp

from core.config import get_settings

logger = logging.getLogger(__name__)

# ── ScrapingDog endpoint ──────────────────────────────────────────────────────

_SCRAPINGDOG_GWS_URL = "https://api.scrapingdog.com/scrape"

# Request timeout — ScrapingDog docs recommend 60 s for JS-rendered pages
_REQUEST_TIMEOUT_SECONDS = 60

# ── Regex patterns ────────────────────────────────────────────────────────────

# Activity: Facebook embeds post timestamps in several JSON keys depending on
# the page layout version.  We collect all matches and return the most recent.
_TIMESTAMP_PATTERNS: List[re.Pattern] = [
    re.compile(r'"creation_time"\s*:\s*(\d{10})'),
    re.compile(r'"story_create_time"\s*:\s*(\d{10})'),
    re.compile(r'"publish_time"\s*:\s*(\d{10})'),
    re.compile(r'"created_time"\s*:\s*"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'),
]

# Contact: JSON-key-targeted patterns minimise false positives.
_PHONE_PATTERNS: List[re.Pattern] = [
    re.compile(r'"phone"\s*:\s*"([+\d()\s\-\.]{7,25})"'),
    re.compile(r'"formatted_phone"\s*:\s*"([+\d()\s\-\.]{7,25})"'),
    re.compile(r'"phone_number"\s*:\s*"([+\d()\s\-\.]{7,25})"'),
]

# Match email addresses inside JSON string values.
_EMAIL_PATTERN = re.compile(
    r'"(?:email|contact_email)"\s*:\s*"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"'
)

# Website URL keys — negative lookahead strips facebook.com self-references.
_WEBSITE_PATTERNS: List[re.Pattern] = [
    re.compile(
        r'"(?:website|website_url)"\s*:\s*"(https?://(?!(?:www\.)?facebook\.com)[^"]{4,})"'
    ),
]


# ── Data container ────────────────────────────────────────────────────────────

@dataclass
class FacebookPageData:
    """
    All signals extracted from a single Facebook business page fetch.

    Fields default to ``None`` so callers can distinguish "not found" from
    "found but empty".  ``enriched_fields`` lists the names of fields that
    were successfully populated, useful for logging.
    """

    last_post_date: Optional[datetime] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None

    @property
    def enriched_fields(self) -> List[str]:
        """Return the names of all non-None fields."""
        names = []
        if self.last_post_date is not None:
            names.append("last_post_date")
        if self.phone is not None:
            names.append("phone")
        if self.email is not None:
            names.append("email")
        if self.website_url is not None:
            names.append("website_url")
        return names

    def is_empty(self) -> bool:
        return not self.enriched_fields


# ── Public utility ────────────────────────────────────────────────────────────

def extract_facebook_url_from_raw(raw_data: dict) -> Optional[str]:
    """
    Find the Facebook page URL from a Business's ``raw_data``.

    Searches two locations in priority order:

    1. ``raw_data["social_urls"]["facebook"]`` — explicit social-URL map
       populated by some scraper paths.
    2. ``raw_data["scrapingdog_discovery"]["search_results"]["organic_results"]``
       — Google Search results stored by the ScrapingDog discovery step.
       Facebook links appear here as organic results ranked by Google.

    Returns the first matching ``facebook.com`` URL found, or ``None``.
    """
    if not raw_data:
        return None

    # Path 1: explicit social_urls map
    social_urls = raw_data.get("social_urls") or {}
    url = social_urls.get("facebook") or social_urls.get("Facebook")
    if url and "facebook.com" in url:
        return url

    # Path 2: ScrapingDog organic search results
    sd = raw_data.get("scrapingdog_discovery") or {}
    organic_results = sd.get("search_results", {}).get("organic_results", [])
    for result in organic_results:
        link = result.get("link") or ""
        if "facebook.com" in link:
            return link

    return None


# ── Scraper class ─────────────────────────────────────────────────────────────

class FacebookActivityScraper:
    """
    Fetches and parses a public Facebook business page for activity and
    contact signals in a single HTTP request.

    Example::

        scraper = FacebookActivityScraper()
        data = await scraper.scrape_page("https://www.facebook.com/mybusiness/")
        print(data.last_post_date, data.phone, data.email, data.website_url)
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        settings = get_settings()
        self._api_key = api_key or getattr(settings, "SCRAPINGDOG_API_KEY", None)

    # ── Public API ────────────────────────────────────────────────────────────

    async def scrape_page(self, facebook_url: str) -> FacebookPageData:
        """
        Fetch the Facebook page and extract all available signals.

        Returns a :class:`FacebookPageData` instance.  All fields default to
        ``None`` when the page could not be fetched or the signal was absent.

        Args:
            facebook_url: Full URL of the Facebook business page.
        """
        if not self._api_key:
            logger.warning(
                "SCRAPINGDOG_API_KEY is not configured — skipping Facebook scrape"
            )
            return FacebookPageData()

        html = await self._fetch_page(facebook_url)
        if html is None:
            return FacebookPageData()

        data = FacebookPageData(
            last_post_date=self._parse_last_post_date(html),
            phone=self._parse_phone(html),
            email=self._parse_email(html),
            website_url=self._parse_website(html),
        )

        if data.enriched_fields:
            logger.debug(
                "Facebook scrape for %s found: %s",
                facebook_url,
                ", ".join(data.enriched_fields),
            )
        else:
            logger.debug("Facebook scrape for %s returned no signals", facebook_url)

        return data

    async def get_last_post_date(self, facebook_url: str) -> Optional[datetime]:
        """Convenience wrapper — returns only the last post date signal."""
        data = await self.scrape_page(facebook_url)
        return data.last_post_date

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Call ScrapingDog GWS with JS rendering and return raw HTML."""
        params = {
            "api_key": self._api_key,
            "url": url,
            "dynamic": "true",  # JavaScript rendering — required for Facebook
        }
        try:
            timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(_SCRAPINGDOG_GWS_URL, params=params) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    logger.warning(
                        "ScrapingDog returned HTTP %d for %s", resp.status, url
                    )
                    return None
        except Exception as exc:
            logger.warning(
                "Failed to fetch Facebook page %s via ScrapingDog: %s", url, exc
            )
            return None

    def _parse_last_post_date(self, html: str) -> Optional[datetime]:
        """
        Extract the newest post timestamp from the raw HTML/JS payload.

        Scans all known timestamp keys and returns the most recent hit.
        """
        latest: Optional[datetime] = None
        for pattern in _TIMESTAMP_PATTERNS:
            for match in pattern.finditer(html):
                dt = self._to_datetime(match.group(1))
                if dt and (latest is None or dt > latest):
                    latest = dt
        return latest

    @staticmethod
    def _parse_phone(html: str) -> Optional[str]:
        """
        Extract the first phone number found in the page's inline JSON.

        Returns the raw string as Facebook provides it (e.g. "+1 (281) 391-2001")
        without normalisation so the caller can decide how to store it.
        """
        for pattern in _PHONE_PATTERNS:
            match = pattern.search(html)
            if match:
                candidate = match.group(1).strip()
                # Sanity check: must contain at least 7 digits
                if sum(c.isdigit() for c in candidate) >= 7:
                    return candidate
        return None

    @staticmethod
    def _parse_email(html: str) -> Optional[str]:
        """Extract the first email address found in the page's inline JSON."""
        match = _EMAIL_PATTERN.search(html)
        return match.group(1).lower() if match else None

    @staticmethod
    def _parse_website(html: str) -> Optional[str]:
        """
        Extract the business website URL from the page's inline JSON.

        Facebook self-references (facebook.com) are excluded so we only
        return external URLs that represent the business's own web presence.
        """
        for pattern in _WEBSITE_PATTERNS:
            match = pattern.search(html)
            if match:
                url = match.group(1).strip().rstrip("/")
                return url
        return None

    @staticmethod
    def _to_datetime(raw: str) -> Optional[datetime]:
        """Convert a raw timestamp string (Unix epoch or ISO-8601) to UTC datetime."""
        if raw.isdigit() and len(raw) == 10:
            try:
                return datetime.fromtimestamp(int(raw), tz=timezone.utc)
            except (ValueError, OSError):
                return None

        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        return None
