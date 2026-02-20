"""
Site generation helper functions.

Extracted helper functions to keep generation.py clean and modular.
Following single responsibility principle and separation of concerns.
"""
from typing import Optional, Dict, Any
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.business import Business
from models.site import GeneratedSite
from services.shortener.short_link_service_v2 import ShortLinkServiceV2

logger = logging.getLogger(__name__)

# Constants for site generation
SITE_STATUS_GENERATING = "generating"
SITE_STATUS_COMPLETED = "completed"
SITE_STATUS_FAILED = "failed"
LINK_TYPE_SITE_PREVIEW = "site_preview"
SITE_BASE_URL = "https://sites.lavish.solutions"


def build_site_subdomain(business_name: str, city: str, business_id: str) -> str:
    """
    Generate a clean subdomain for a site.
    
    Format: {sanitized-business-name}-{region}
    Example: "joes-plumbing-la" or "bodycare-miami"
    
    If the business name is too long (>30 chars), it will be shortened intelligently.
    If there's a conflict, a number suffix is added.
    
    Args:
        business_name: Business name to sanitize
        city: City/region for the business
        business_id: Full business UUID (fallback if city missing)
        
    Returns:
        Clean subdomain string
    """
    import re
    
    # Sanitize business name: lowercase, remove special chars, replace spaces with hyphens
    name = business_name.lower()
    name = re.sub(r'[^\w\s-]', '', name)  # Remove special characters
    name = re.sub(r'[-\s]+', '-', name)   # Replace spaces/multiple hyphens with single hyphen
    name = name.strip('-')
    
    # Shorten if too long (keep max 30 chars for business name part)
    if len(name) > 30:
        # Try to keep meaningful words (avoid cutting mid-word)
        words = name.split('-')
        shortened = []
        current_length = 0
        for word in words:
            if current_length + len(word) + 1 <= 30:  # +1 for hyphen
                shortened.append(word)
                current_length += len(word) + 1
            else:
                break
        name = '-'.join(shortened) if shortened else name[:30]
    
    # Sanitize city/region
    if city:
        region = city.lower()
        region = re.sub(r'[^\w\s-]', '', region)
        region = re.sub(r'[-\s]+', '-', region)
        region = region.strip('-')
        # Shorten city to abbreviation or first part (max 15 chars)
        if len(region) > 15:
            region = region.split('-')[0][:15]
    else:
        # Fallback to ID prefix if no city
        region = business_id[:6]
    
    subdomain = f"{name}-{region}"
    
    # Final cleanup and length check
    subdomain = subdomain.strip('-')
    if len(subdomain) > 63:  # DNS subdomain limit
        subdomain = subdomain[:63].rstrip('-')
    
    return subdomain


def build_site_url(subdomain: str) -> str:
    """
    Build full site URL from subdomain.
    
    Args:
        subdomain: Site subdomain
        
    Returns:
        Full HTTPS URL to the site
    """
    return f"{SITE_BASE_URL}/{subdomain}"


async def get_business_by_id(
    db: AsyncSession,
    business_id: str
) -> Optional[Business]:
    """
    Fetch business from database by ID.
    
    Args:
        db: Database session
        business_id: Business UUID string
        
    Returns:
        Business instance or None if not found
    """
    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    return result.scalar_one_or_none()


async def get_existing_site(
    db: AsyncSession,
    business_id: str
) -> Optional[GeneratedSite]:
    """
    Check if business already has a generated site.
    
    Args:
        db: Database session
        business_id: Business UUID string
        
    Returns:
        GeneratedSite instance or None
    """
    result = await db.execute(
        select(GeneratedSite).where(
            GeneratedSite.business_id == business_id
        )
    )
    return result.scalar_one_or_none()


async def create_short_link_for_site(
    db: AsyncSession,
    site_url: str,
    business_id: UUID,
    site_id: UUID,
    business_name: Optional[str] = None,
) -> str:
    """
    Create a short link for a generated site.

    Uses ShortLinkServiceV2 (race-condition-free).
    Falls back to full URL if shortener fails.

    When `business_name` is provided the slug will be human-readable,
    e.g. "https://lvsh.cc/redwx7k" instead of "https://lvsh.cc/a1B2c3".

    Args:
        db:            Database session
        site_url:      Full site URL to shorten
        business_id:   Business UUID
        site_id:       Site UUID
        business_name: Business name used to build a readable slug prefix

    Returns:
        Short URL (e.g., "https://lvsh.cc/redwx7k") or original URL on failure
    """
    try:
        short_url = await ShortLinkServiceV2.get_or_create_short_link(
            db=db,
            destination_url=site_url,
            link_type=LINK_TYPE_SITE_PREVIEW,
            business_id=business_id,
            site_id=site_id,
            business_name=business_name,
        )
        logger.info(f"Created short link for site {site_id}: {short_url}")
        return short_url

    except Exception as e:
        logger.warning(
            f"Failed to create short link for site {site_id}, "
            f"using full URL: {e}"
        )
        return site_url


def build_site_result_dict(
    business_id: str,
    site_id: UUID,
    subdomain: str,
    status: str = "completed"
) -> Dict[str, Any]:
    """
    Build standardized result dictionary for site generation.
    
    Args:
        business_id: Business UUID string
        site_id: Site UUID
        subdomain: Site subdomain
        status: Generation status
        
    Returns:
        Dictionary with generation result details
    """
    return {
        "status": status,
        "business_id": business_id,
        "site_id": str(site_id),
        "subdomain": subdomain
    }
