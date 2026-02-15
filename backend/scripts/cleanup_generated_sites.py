"""
Cleanup script to handle businesses with generated sites that actually have websites.

This script ensures businesses with real websites are marked correctly so they:
1. Don't appear in the "needs generation" queue
2. Don't receive sales messages for websites they don't need
3. Are properly excluded from future generation attempts

Usage:
    python scripts/cleanup_generated_sites.py --dry-run
    python scripts/cleanup_generated_sites.py --fix
"""
import asyncio
import argparse
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.business import Business
from models.site import GeneratedSite

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def cleanup_generated_sites(dry_run: bool = True):
    """
    Clean up businesses with generated sites that actually have real websites.
    
    Fixes:
    1. Businesses with real website URLs but still have generated sites
    2. Businesses with placeholder URLs (test data)
    """
    logger.info("🔍 Starting cleanup of generated sites...")
    logger.info(f"   Dry run: {dry_run}")
    
    async for db in get_db():
        try:
            # Find businesses with generated sites
            query = select(Business, GeneratedSite).join(
                GeneratedSite,
                Business.id == GeneratedSite.business_id
            ).where(
                GeneratedSite.status == 'completed'
            )
            
            result = await db.execute(query)
            rows = result.all()
            
            logger.info(f"📊 Found {len(rows)} businesses with completed generated sites")
            
            # Categorize businesses
            has_real_website = []
            has_placeholder = []
            legitimately_no_website = []
            
            for business, gen_site in rows:
                if business.website_url and business.website_url != 'https://placeholder-valid-website.com':
                    has_real_website.append((business, gen_site))
                elif business.website_url == 'https://placeholder-valid-website.com':
                    has_placeholder.append((business, gen_site))
                else:
                    legitimately_no_website.append((business, gen_site))
            
            # Report findings
            logger.info("\n" + "="*80)
            logger.info("📊 ANALYSIS RESULTS:")
            logger.info(f"   ✅ Legitimate (no website): {len(legitimately_no_website)} ({len(legitimately_no_website)/len(rows)*100:.1f}%)")
            logger.info(f"   ⚠️  Has placeholder URL: {len(has_placeholder)} ({len(has_placeholder)/len(rows)*100:.1f}%)")
            logger.info(f"   ❌ Has REAL website: {len(has_real_website)} ({len(has_real_website)/len(rows)*100:.1f}%)")
            logger.info("="*80)
            
            # Show businesses with real websites
            if has_real_website:
                logger.info("\n❌ BUSINESSES WITH REAL WEBSITES (Should not have generated sites):")
                for business, gen_site in has_real_website:
                    logger.info(f"   • {business.name} ({business.city}, {business.state})")
                    logger.info(f"     Phone: {business.phone}")
                    logger.info(f"     Website: {business.website_url}")
                    logger.info(f"     Status: {business.website_validation_status}")
                    logger.info(f"     Generated Site: {gen_site.subdomain}.lavish.solutions")
                    logger.info("")
            
            # Show placeholder businesses
            if has_placeholder:
                logger.info("\n⚠️  BUSINESSES WITH PLACEHOLDER URLs (Test data):")
                for business, gen_site in has_placeholder[:10]:
                    logger.info(f"   • {business.name} ({business.city}, {business.state})")
                    logger.info(f"     Phone: {business.phone}")
                    logger.info(f"     Generated Site: {gen_site.subdomain}.lavish.solutions")
                if len(has_placeholder) > 10:
                    logger.info(f"   ... and {len(has_placeholder) - 10} more")
            
            # Apply fixes if not dry-run
            if not dry_run:
                logger.info("\n🔧 APPLYING FIXES...")
                
                # Fix businesses with real websites
                for business, gen_site in has_real_website:
                    logger.info(f"   Fixing: {business.name}")
                    
                    # Update business to prevent future queueing
                    # Keep the website_url and mark as validated
                    if business.website_validation_status == 'pending':
                        business.website_validation_status = 'valid'
                    
                    # Add note to raw_data
                    if not business.raw_data:
                        business.raw_data = {}
                    business.raw_data['_cleanup_note'] = (
                        "This business has a real website but was queued for generation "
                        "during early system testing. Website should be used instead of generated site."
                    )
                    
                    await db.commit()
                    logger.info(f"      ✅ Updated: website_validation_status={business.website_validation_status}")
                
                # Fix placeholder businesses
                for business, gen_site in has_placeholder:
                    logger.info(f"   Fixing placeholder: {business.name}")
                    
                    # Clear placeholder URL
                    business.website_url = None
                    business.website_validation_status = 'missing'
                    
                    # Add note
                    if not business.raw_data:
                        business.raw_data = {}
                    business.raw_data['_cleanup_note'] = (
                        "Placeholder URL removed. This business has no confirmed website."
                    )
                    
                    await db.commit()
                    logger.info(f"      ✅ Cleared placeholder URL")
                
                logger.info("\n✅ ALL FIXES APPLIED!")
            else:
                logger.info("\n🔍 DRY RUN - No changes made. Run with --fix to apply changes.")
            
        except Exception as e:
            logger.error(f"Fatal error during cleanup: {e}", exc_info=True)
        finally:
            await db.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up businesses with generated sites that actually have websites"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply fixes (default is dry-run)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(cleanup_generated_sites(dry_run=not args.fix))


if __name__ == "__main__":
    main()
