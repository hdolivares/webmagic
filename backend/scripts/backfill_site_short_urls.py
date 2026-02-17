"""
Backfill short_url field for existing generated sites.

This script creates short links for all completed sites that don't have one yet,
and stores the short link directly on the site record.

Run after deploying migration 017.
"""
import asyncio
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.site import GeneratedSite
from models.business import Business
from services.shortener.short_link_service_v2 import ShortLinkServiceV2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_short_urls():
    """Create short links for all completed sites missing them."""
    async for db in get_db():
        try:
            # Find completed sites without short_url
            result = await db.execute(
                select(GeneratedSite, Business)
                .join(Business, Business.id == GeneratedSite.business_id)
                .where(
                    GeneratedSite.status == 'completed',
                    GeneratedSite.short_url == None  # noqa: E711
                )
            )
            
            sites_to_update = result.all()
            total = len(sites_to_update)
            
            if total == 0:
                logger.info("✅ No sites need backfilling - all sites have short links!")
                return
            
            logger.info(f"Found {total} sites needing short links")
            
            success_count = 0
            error_count = 0
            
            for site, business in sites_to_update:
                try:
                    # Build full site URL
                    site_url = f"https://sites.lavish.solutions/{site.subdomain}"
                    
                    # Create short link
                    short_url = await ShortLinkServiceV2.get_or_create_short_link(
                        db=db,
                        destination_url=site_url,
                        link_type="site_preview",
                        business_id=business.id,
                        site_id=site.id,
                    )
                    
                    # Update site record
                    await db.execute(
                        update(GeneratedSite)
                        .where(GeneratedSite.id == site.id)
                        .values(short_url=short_url)
                    )
                    
                    success_count += 1
                    logger.info(
                        f"[{success_count}/{total}] Created short link for {site.subdomain}: {short_url}"
                    )
                    
                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"[{error_count} errors] Failed to create short link for site {site.id}: {e}"
                    )
                    continue
            
            # Commit all updates
            await db.commit()
            
            logger.info(f"\n" + "=" * 60)
            logger.info(f"Backfill Complete!")
            logger.info(f"=" * 60)
            logger.info(f"Total sites processed: {total}")
            logger.info(f"✅ Success: {success_count}")
            logger.info(f"❌ Errors: {error_count}")
            logger.info(f"=" * 60)
            
        except Exception as e:
            logger.error(f"Fatal error during backfill: {e}", exc_info=True)
            raise
        finally:
            await db.close()
            break


if __name__ == "__main__":
    asyncio.run(backfill_short_urls())
