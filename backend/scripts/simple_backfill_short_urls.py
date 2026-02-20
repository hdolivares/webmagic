"""
Simple backfill script for legacy site short URLs.

Gets all sites without short_url, builds their full URL,
creates a short link, and updates the record.

Simple, clean, one site at a time.
"""
import asyncio
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.site import GeneratedSite
from models.business import Business
from services.shortener.short_link_service_v2 import ShortLinkServiceV2
from sqlalchemy.future import select as sa_select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
SITE_BASE_URL = "https://sites.lavish.solutions"


def build_full_url(subdomain: str) -> str:
    """Build full site URL from subdomain."""
    return f"{SITE_BASE_URL}/{subdomain}"


async def backfill_one_site(db: AsyncSession, site: GeneratedSite) -> bool:
    """
    Backfill short URL for a single site.

    Args:
        db: Database session
        site: GeneratedSite instance

    Returns:
        True if successful, False if failed
    """
    try:
        # Resolve business name for readable slug (e.g. "redwx7k")
        business_name = None
        if site.business_id:
            biz_result = await db.execute(
                sa_select(Business.name).where(Business.id == site.business_id)
            )
            business_name = biz_result.scalar_one_or_none()

        # Build full URL
        full_url = build_full_url(site.subdomain)

        # Create short link with business-name prefix
        short_url = await ShortLinkServiceV2.get_or_create_short_link(
            db=db,
            destination_url=full_url,
            link_type="site_preview",
            business_id=site.business_id,
            site_id=site.id,
            business_name=business_name,
        )
        
        # Update site record
        await db.execute(
            update(GeneratedSite)
            .where(GeneratedSite.id == site.id)
            .values(short_url=short_url)
        )
        
        # Commit immediately
        await db.commit()
        
        logger.info(f"✅ {site.subdomain} → {short_url}")
        return True
        
    except Exception as e:
        # Rollback on error
        await db.rollback()
        logger.error(f"❌ {site.subdomain}: {str(e)}")
        return False


async def main():
    """Main backfill process."""
    logger.info("Starting simple backfill for legacy sites...")
    logger.info("=" * 60)
    
    success_count = 0
    error_count = 0
    
    # Get database session properly
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # Get all sites without short_url
        result = await db.execute(
            select(GeneratedSite)
            .where(
                GeneratedSite.status == 'completed',
                GeneratedSite.short_url == None  # noqa: E711
            )
            .order_by(GeneratedSite.created_at.asc())
        )
        
        sites = result.scalars().all()
        total = len(sites)
        
        if total == 0:
            logger.info("✅ No sites need backfilling!")
            return
        
        logger.info(f"Found {total} sites needing short links\n")
        
        # Process each site
        for i, site in enumerate(sites, 1):
            logger.info(f"[{i}/{total}] Processing {site.subdomain}...")
            
            if await backfill_one_site(db, site):
                success_count += 1
            else:
                error_count += 1
        
        # Summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("Backfill Complete!")
        logger.info("=" * 60)
        logger.info(f"Total sites: {total}")
        logger.info(f"✅ Success: {success_count}")
        logger.info(f"❌ Errors: {error_count}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    asyncio.run(main())
