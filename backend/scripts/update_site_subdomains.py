"""
Update existing sites with new subdomain format and regenerate short URLs.

This script:
1. Fetches all existing sites with old subdomain format
2. Generates new clean subdomains (business-name + region)
3. Updates the subdomain in generated_sites table
4. Deactivates old short URLs
5. Creates new short URLs pointing to new subdomains
6. Updates the short_url column in generated_sites

Run from backend directory:
PYTHONPATH=/var/www/webmagic/backend python scripts/update_site_subdomains.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from models.site import GeneratedSite
from models.business import Business
from models.short_link import ShortLink
from tasks.generation_helpers import build_site_subdomain, build_site_url
from services.shortener.short_link_service_v2 import ShortLinkServiceV2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def update_site_subdomains():
    """Update all existing sites with new subdomain format."""
    db_gen = get_db()
    db: AsyncSession = await db_gen.__anext__()
    
    try:
        # Fetch all sites with their businesses
        query = (
            select(GeneratedSite, Business)
            .join(Business, GeneratedSite.business_id == Business.id)
            .where(GeneratedSite.status.in_(["completed", "published", "live"]))
        )
        result = await db.execute(query)
        sites_with_businesses = result.all()
        
        total_sites = len(sites_with_businesses)
        logger.info(f"Found {total_sites} sites to update")
        
        if total_sites == 0:
            logger.info("No sites to update")
            return
        
        updated_count = 0
        failed_count = 0
        
        for site, business in sites_with_businesses:
            try:
                # Generate new subdomain
                new_subdomain = build_site_subdomain(
                    business.name, 
                    business.city, 
                    str(business.id)
                )
                
                # Check if subdomain would change
                if site.subdomain == new_subdomain:
                    logger.info(f"Skipping {business.name} - subdomain unchanged: {new_subdomain}")
                    continue
                
                old_subdomain = site.subdomain
                old_url = build_site_url(old_subdomain)
                new_url = build_site_url(new_subdomain)
                
                logger.info(f"Updating {business.name}:")
                logger.info(f"  Old: {old_subdomain} -> {old_url}")
                logger.info(f"  New: {new_subdomain} -> {new_url}")
                
                # Check if new subdomain already exists (conflict)
                existing_check = await db.execute(
                    select(GeneratedSite)
                    .where(GeneratedSite.subdomain == new_subdomain)
                    .where(GeneratedSite.id != site.id)
                )
                if existing_check.scalar_one_or_none():
                    # Add number suffix to avoid conflict
                    counter = 2
                    while True:
                        test_subdomain = f"{new_subdomain}-{counter}"
                        test_check = await db.execute(
                            select(GeneratedSite)
                            .where(GeneratedSite.subdomain == test_subdomain)
                        )
                        if not test_check.scalar_one_or_none():
                            new_subdomain = test_subdomain
                            new_url = build_site_url(new_subdomain)
                            logger.info(f"  Conflict resolved: {new_subdomain}")
                            break
                        counter += 1
                        if counter > 100:
                            raise Exception("Could not find unique subdomain")
                
                # 1. Deactivate old short links pointing to old URL
                await db.execute(
                    update(ShortLink)
                    .where(ShortLink.destination_url == old_url)
                    .where(ShortLink.is_active == True)
                    .values(is_active=False)
                )
                
                # 2. Create new short link for new URL
                new_short_link = await ShortLinkServiceV2.get_or_create_short_link(
                    db=db,
                    destination_url=new_url,
                    link_type="site_preview",
                    campaign_id=None,
                    business_id=business.id,
                    site_id=site.id
                )
                
                # 3. Update site with new subdomain and short_url
                await db.execute(
                    update(GeneratedSite)
                    .where(GeneratedSite.id == site.id)
                    .values(
                        subdomain=new_subdomain,
                        short_url=new_short_link.short_url
                    )
                )
                
                await db.commit()
                updated_count += 1
                logger.info(f"  ✓ Updated successfully (short: {new_short_link.short_url})")
                
            except Exception as e:
                logger.error(f"  ✗ Failed to update {business.name}: {str(e)}")
                await db.rollback()
                failed_count += 1
                continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Update complete!")
        logger.info(f"  Total sites: {total_sites}")
        logger.info(f"  Updated: {updated_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info(f"  Skipped: {total_sites - updated_count - failed_count}")
        logger.info(f"{'='*60}")
        
    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    asyncio.run(update_site_subdomains())
