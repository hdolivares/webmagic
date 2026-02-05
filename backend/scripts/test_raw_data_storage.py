"""
Test Raw Data Storage

Scrapes 2 businesses and verifies raw_data is saved correctly in the database.

Usage:
    python -m scripts.test_raw_data_storage
"""
import asyncio
import sys
from pathlib import Path
import logging
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.business import Business
from services.hunter.scraper import OutscraperClient
from services.hunter.business_service import BusinessService
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_raw_data_storage():
    """
    Test that raw_data is saved correctly when scraping businesses.
    """
    logger.info("="*80)
    logger.info("RAW DATA STORAGE TEST")
    logger.info("="*80)
    logger.info("")
    
    # Step 1: Scrape 2 test businesses
    logger.info("Step 1: Scraping 2 test businesses")
    logger.info("")
    
    scraper = OutscraperClient()
    
    try:
        response = await scraper.search_businesses(
            query="plumbers",
            city="Miami",
            state="FL",
            country="US",
            limit=2
        )
        
        raw_businesses = response.get("businesses", [])
        logger.info(f"✅ Scraped {len(raw_businesses)} businesses")
        logger.info("")
        
        if not raw_businesses:
            logger.error("No businesses returned")
            return
        
        # Step 2: Save to database
        logger.info("Step 2: Saving businesses to database")
        logger.info("")
        
        async with AsyncSessionLocal() as db:
            business_service = BusinessService(db)
            
            saved_ids = []
            for idx, biz_data in enumerate(raw_businesses, 1):
                logger.info(f"Processing business {idx}: {biz_data.get('name')}")
                
                # Check raw_data presence
                raw_data = biz_data.get("raw_data", {})
                logger.info(f"  Raw data keys: {len(raw_data.keys())}")
                logger.info(f"  Raw data size: {len(json.dumps(raw_data))} bytes")
                
                # Save business
                business = await business_service.create_or_update_business(
                    data=biz_data,
                    source="outscraper_gmaps",
                    discovery_city="Miami",
                    discovery_state="FL"
                )
                
                if business:
                    saved_ids.append(str(business.id))
                    logger.info(f"  ✅ Saved business ID: {business.id}")
                else:
                    logger.warning(f"  ⚠️  Failed to save business")
                
                logger.info("")
            
            await db.commit()
            logger.info(f"✅ Committed {len(saved_ids)} businesses to database")
            logger.info("")
        
        # Step 3: Verify raw_data was saved
        logger.info("Step 3: Verifying raw_data storage")
        logger.info("")
        
        async with AsyncSessionLocal() as db:
            for business_id in saved_ids:
                result = await db.execute(
                    select(Business).where(Business.id == business_id)
                )
                business = result.scalar_one_or_none()
                
                if business:
                    logger.info(f"Business: {business.name}")
                    logger.info(f"  ID: {business.id}")
                    logger.info(f"  Website URL: {business.website_url or 'None'}")
                    logger.info(f"  Website Type: {business.website_type}")
                    logger.info(f"  Quality Score: {business.quality_score}")
                    logger.info(f"  Verified: {business.verified}")
                    logger.info(f"  Operational: {business.operational}")
                    
                    if business.raw_data:
                        logger.info(f"  ✅ Raw data SAVED!")
                        logger.info(f"     Keys: {len(business.raw_data.keys())}")
                        logger.info(f"     Size: {len(json.dumps(business.raw_data))} bytes")
                        logger.info(f"     Sample keys: {list(business.raw_data.keys())[:10]}")
                    else:
                        logger.error(f"  ❌ Raw data NOT SAVED!")
                    
                    logger.info("")
        
        # Step 4: Summary
        logger.info("="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info("")
        logger.info(f"Scraped: {len(raw_businesses)} businesses")
        logger.info(f"Saved: {len(saved_ids)} businesses")
        logger.info("")
        
        # Check overall database state
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Business).where(Business.raw_data.isnot(None))
            )
            all_with_raw = result.scalars().all()
            logger.info(f"Total businesses with raw_data: {len(all_with_raw)}")
            logger.info("")
        
        logger.info("✅ Test complete!")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)


def main():
    asyncio.run(test_raw_data_storage())


if __name__ == "__main__":
    main()

