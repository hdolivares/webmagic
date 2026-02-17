"""
Backfill short_url field for existing generated sites.

This script creates short links for all completed sites that don't have one yet,
and stores the short link directly on the site record.

Run after deploying migration 017.

Best Practices Applied:
- Modular functions with single responsibility
- Clear error handling and logging
- Progress tracking with statistics
- Type hints for clarity
- Constants for magic values
"""
import asyncio
import logging
from typing import Tuple, List
from dataclasses import dataclass
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.site import GeneratedSite
from models.business import Business
from services.shortener.short_link_service_v2 import ShortLinkServiceV2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
SITE_BASE_URL = "https://sites.lavish.solutions"
LINK_TYPE_SITE_PREVIEW = "site_preview"
SITE_STATUS_COMPLETED = "completed"


@dataclass
class BackfillStats:
    """Statistics for backfill operation."""
    total: int = 0
    success: int = 0
    errors: int = 0
    
    def log_summary(self) -> None:
        """Log formatted summary of backfill results."""
        logger.info("\n" + "=" * 60)
        logger.info("Backfill Complete!")
        logger.info("=" * 60)
        logger.info(f"Total sites processed: {self.total}")
        logger.info(f"✅ Success: {self.success}")
        logger.info(f"❌ Errors: {self.errors}")
        logger.info("=" * 60)


async def _fetch_sites_needing_backfill(
    db: AsyncSession
) -> List[Tuple[GeneratedSite, Business]]:
    """
    Find all completed sites without short URLs.
    
    Args:
        db: Database session
        
    Returns:
        List of (GeneratedSite, Business) tuples
    """
    result = await db.execute(
        select(GeneratedSite, Business)
        .join(Business, Business.id == GeneratedSite.business_id)
        .where(
            GeneratedSite.status == SITE_STATUS_COMPLETED,
            GeneratedSite.short_url == None  # noqa: E711
        )
    )
    return result.all()


def _build_site_url(subdomain: str) -> str:
    """
    Build full site URL from subdomain.
    
    Args:
        subdomain: Site subdomain
        
    Returns:
        Full HTTPS URL
    """
    return f"{SITE_BASE_URL}/{subdomain}"


async def _create_and_save_short_link(
    db: AsyncSession,
    site: GeneratedSite,
    business: Business
) -> str:
    """
    Create short link and update site record.
    
    Args:
        db: Database session
        site: GeneratedSite instance
        business: Business instance
        
    Returns:
        Created short URL
        
    Raises:
        Exception: If short link creation or database update fails
    """
    # Build full site URL
    site_url = _build_site_url(site.subdomain)
    
    # Create short link
    short_url = await ShortLinkServiceV2.get_or_create_short_link(
        db=db,
        destination_url=site_url,
        link_type=LINK_TYPE_SITE_PREVIEW,
        business_id=business.id,
        site_id=site.id,
    )
    
    # Update site record
    await db.execute(
        update(GeneratedSite)
        .where(GeneratedSite.id == site.id)
        .values(short_url=short_url)
    )
    
    return short_url


async def backfill_short_urls() -> None:
    """
    Create short links for all completed sites missing them.
    
    This is the main orchestration function that:
    1. Fetches sites needing backfill
    2. Processes each site (create link + update DB)
    3. Tracks statistics
    4. Logs progress and summary
    
    Raises:
        Exception: On fatal errors (logged and re-raised)
    """
    stats = BackfillStats()
    
    async for db in get_db():
        try:
            # Step 1: Find sites needing backfill
            sites_to_update = await _fetch_sites_needing_backfill(db)
            stats.total = len(sites_to_update)
            
            if stats.total == 0:
                logger.info("✅ No sites need backfilling - all sites have short links!")
                return
            
            logger.info(f"Found {stats.total} sites needing short links")
            logger.info("Starting backfill process...\n")
            
            # Step 2: Process each site
            for site, business in sites_to_update:
                try:
                    short_url = await _create_and_save_short_link(db, site, business)
                    
                    stats.success += 1
                    logger.info(
                        f"[{stats.success}/{stats.total}] "
                        f"✅ {site.subdomain} → {short_url}"
                    )
                    
                except Exception as e:
                    stats.errors += 1
                    logger.error(
                        f"[{stats.errors} errors] "
                        f"❌ Failed for site {site.id} ({site.subdomain}): {e}"
                    )
                    continue
            
            # Step 3: Commit all updates
            await db.commit()
            logger.info("\nCommitted all changes to database")
            
            # Step 4: Log summary
            stats.log_summary()
            
        except Exception as e:
            logger.error(f"Fatal error during backfill: {e}", exc_info=True)
            raise
        finally:
            await db.close()
            break


if __name__ == "__main__":
    asyncio.run(backfill_short_urls())
