"""
Retrieves the most-recent post date from a public Facebook business page.

Uses ScrapingDog's General Web Scraping API with JavaScript rendering
(``dynamic=true``).  Credit cost: **5 credits per request** — the same as
a Google Search lookup already used in this codebase.

Facebook embeds structured data in ``<script>`` tags as inline JSON
containing Unix timestamps for each post.  We look for known timestamp
keys rather than parsing the full DOM so the extraction is fast and
resilient to layout changes.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from core.config import get_settings

logger = logging.getLogger(__name__)

# ScrapingDog General Web Scraping endpoint
_SCRAPINGDOG_GWS_URL = "https://api.scrapingdog.com/scrape"

# Facebook places Unix timestamps in several JSON keys depending on the
# page layout version.  We try all of them and take the most recent.
_TIMESTAMP_PATTERNS = [
    re.compile(r'"creation_time"\s*:\s*(\d{10})'),
    re.compile(r'"story_create_time"\s*:\s*(\d{10})'),
    re.compile(r'"publish_time"\s*:\s*(\d{10})'),
    re.compile(r'"created_time"\s*:\s*"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'),
]

# Request timeout — ScrapingDog docs recommend 60 s for JS-rendered pages
_REQUEST_TIMEOUT_SECONDS = 60


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


class FacebookActivityScraper:
    """
    Fetches the last post date for a public Facebook page.

    Designed to be instantiated once and reused across multiple calls
    (shares the aiohttp session lifespan with the caller, or creates
    a short-lived session per-call if used standalone).

    Example::

        scraper = FacebookActivityScraper()
        last_post = await scraper.get_last_post_date(
            "https://www.facebook.com/mybusiness/"
        )
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        settings = get_settings()
        self._api_key = api_key or getattr(settings, "SCRAPINGDOG_API_KEY", None)

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_last_post_date(self, facebook_url: str) -> Optional[datetime]:
        """
        Fetch and parse the Facebook page to find the most recent post date.

        Args:
            facebook_url: Full URL of the Facebook business page,
                e.g. ``"https://www.facebook.com/mybusiness/"``

        Returns:
            UTC datetime of the most recent post, or ``None`` when the page
            could not be fetched or no timestamps were found.
        """
        if not self._api_key:
            logger.warning(
                "SCRAPINGDOG_API_KEY is not configured — skipping Facebook activity check"
            )
            return None

        html = await self._fetch_page(facebook_url)
        if html is None:
            return None

        last_post_date = self._parse_last_post_date(html)

        if last_post_date:
            logger.debug(
                "Facebook last post for %s: %s", facebook_url, last_post_date.date()
            )
        else:
            logger.debug("No post timestamps found for %s", facebook_url)

        return last_post_date

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Call ScrapingDog GWS with JS rendering and return raw HTML."""
        params = {
            "api_key": self._api_key,
            "url": url,
            "dynamic": "true",   # JavaScript rendering — required for Facebook
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

        Facebook inlines JSON data in ``<script>`` tags.  We scan for
        known timestamp field names and return the most recent hit.
        """
        latest: Optional[datetime] = None

        for pattern in _TIMESTAMP_PATTERNS:
            for match in pattern.finditer(html):
                dt = self._to_datetime(match.group(1))
                if dt and (latest is None or dt > latest):
                    latest = dt

        return latest

    @staticmethod
    def _to_datetime(raw: str) -> Optional[datetime]:
        """
        Convert a raw timestamp string (Unix epoch or ISO-8601) to UTC datetime.
        """
        # 10-digit Unix epoch
        if raw.isdigit() and len(raw) == 10:
            try:
                return datetime.fromtimestamp(int(raw), tz=timezone.utc)
            except (ValueError, OSError):
                return None

        # ISO-8601 partial string
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue

        return None
