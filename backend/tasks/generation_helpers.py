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


def build_site_subdomain(business_name: str, business_id: str) -> str:
    """
    Generate a unique subdomain for a site.
    
    Format: {sanitized-business-name}-{business-id-prefix}
    Example: "joes-plumbing-a1b2c3d4"
    
    Args:
        business_name: Business name to sanitize
        business_id: Full business UUID
        
    Returns:
        Sanitized subdomain string
    """
    sanitized_name = business_name.lower().replace(' ', '-')
    id_prefix = business_id[:8]
    return f"{sanitized_name}-{id_prefix}"


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
    site_id: UUID
) -> str:
    """
    Create a short link for a generated site.
    
    Uses ShortLinkServiceV2 (race-condition-free).
    Falls back to full URL if shortener fails.
    
    Args:
        db: Database session
        site_url: Full site URL to shorten
        business_id: Business UUID
        site_id: Site UUID
        
    Returns:
        Short URL (e.g., "https://lvsh.cc/a1B2c3") or original URL on failure
    """
    try:
        short_url = await ShortLinkServiceV2.get_or_create_short_link(
            db=db,
            destination_url=site_url,
            link_type=LINK_TYPE_SITE_PREVIEW,
            business_id=business_id,
            site_id=site_id,
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
