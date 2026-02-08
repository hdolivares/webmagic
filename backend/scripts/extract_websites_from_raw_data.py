"""
Extract website URLs from raw_data and update website_url field.
Fixes the issue where Outscraper data has 'website' field but we're looking for 'website_url'.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select, update
from core.database import AsyncSessionLocal
from models.business import Business
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def extract_and_update_websites():
    """Extract websites from raw_data and update website_url field."""
    logger.info("Starting website extraction from raw_data...")
    
    async with AsyncSessionLocal() as db:
        # Find businesses with raw_data containing website but no website_url
        result = await db.execute(
            select(Business)
            .where(Business.raw_data.isnot(None))
            .where(
                (Business.website_url.is_(None)) | (Business.website_url == '')
            )
        )
        businesses = result.scalars().all()
        
        logger.info(f"Found {len(businesses)} businesses with raw_data")
        
        updated = 0
        extracted = 0
        
        for business in businesses:
            # Try to extract website from raw_data
            raw_data = business.raw_data or {}
            website = raw_data.get('website') or raw_data.get('site')
            
            if website and website.strip():
                # Update the business
                business.website_url = website.strip()
                business.website_validation_status = 'pending'
                extracted += 1
                
                logger.info(f"✓ {business.name}: {website}")
        
        # Commit all changes
        try:
            await db.commit()
            updated = extracted
            logger.info(f"\n{'='*60}")
            logger.info(f"✅ SUCCESS: Extracted and updated {updated} websites!")
            logger.info(f"{'='*60}\n")
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Error committing changes: {e}")
            raise
        
        return {
            "total_checked": len(businesses),
            "websites_extracted": extracted,
            "websites_updated": updated
        }


async def main():
    """Main execution."""
    try:
        result = await extract_and_update_websites()
        
        print("\n" + "="*60)
        print("EXTRACTION COMPLETE")
        print("="*60)
        print(f"Total businesses checked: {result['total_checked']}")
        print(f"Websites extracted: {result['websites_extracted']}")
        print(f"Database updated: {result['websites_updated']}")
        print("="*60 + "\n")
        
        if result['websites_updated'] > 0:
            print("✨ Next steps:")
            print("  1. Run validation on these newly discovered websites")
            print("  2. Update the scraper to properly extract 'website' field")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
