"""
Rescrape specific zones and monitor progress
"""
import asyncio
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.config import get_settings
from models.business import Business
from models.coverage import CoverageGrid
from services.hunter.hunter_service import HunterService
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STRATEGY_ID = "0d58ccf7-8f10-4989-a3ba-35fcd37ccb0d"
ZONES_TO_SCRAPE = ["la_downtown", "la_koreatown"]

async def get_zone_stats(db: AsyncSession, zone_id: str):
    """Get current statistics for a zone"""
    result = await db.execute(
        select(CoverageGrid).where(CoverageGrid.zone_id == zone_id)
    )
    coverage = result.scalar_one_or_none()
    
    if not coverage:
        return None
    
    # Count businesses
    biz_result = await db.execute(
        select(func.count(Business.id))
        .where(Business.coverage_grid_id == coverage.id)
    )
    biz_count = biz_result.scalar()
    
    return {
        "zone_id": zone_id,
        "status": coverage.status,
        "lead_count": coverage.lead_count or 0,
        "qualified_count": coverage.qualified_count or 0,
        "businesses_linked": biz_count,
        "last_scraped": coverage.last_scraped_at
    }

async def scrape_zone(db: AsyncSession):
    """Trigger a zone scrape"""
    hunter_service = HunterService(db)
    
    # The scrape_with_intelligent_strategy will automatically pick the next pending zone
    result = await hunter_service.scrape_with_intelligent_strategy(
        city="Los Angeles",
        state="CA",
        category="plumbers",
        country="US",
        limit_per_zone=50
    )
    
    return result

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        logger.info("=" * 60)
        logger.info("ZONE RESCRAPE - Los Angeles Plumbers")
        logger.info("=" * 60)
        
        # Show initial stats
        logger.info("\n📊 INITIAL STATE:")
        async with AsyncSessionLocal() as db:
            for zone_id in ZONES_TO_SCRAPE:
                stats = await get_zone_stats(db, zone_id)
                if stats:
                    logger.info(f"\n  {zone_id}:")
                    logger.info(f"    Status: {stats['status']}")
                    logger.info(f"    Leads: {stats['lead_count']}")
                    logger.info(f"    Businesses: {stats['businesses_linked']}")
        
        # Scrape first zone
        logger.info(f"\n\n🎯 SCRAPING ZONE 1:")
        logger.info("-" * 60)
        async with AsyncSessionLocal() as db:
            result1 = await scrape_zone(db)
            await db.commit()
            
            logger.info(f"\n✅ Zone 1 Complete!")
            logger.info(f"   Zone: {result1['zone_scraped']['zone_id']}")
            logger.info(f"   Raw Businesses: {result1['results']['raw_businesses']}")
            logger.info(f"   Qualified Leads: {result1['results']['qualified_leads']}")
            logger.info(f"   New Businesses: {result1['results']['new_businesses']}")
            logger.info(f"   With Websites: {result1['results'].get('with_websites', 0)}")
            logger.info(f"   Without Websites: {result1['results'].get('without_websites', 0)}")
            
            # Check updated stats
            stats1 = await get_zone_stats(db, result1['zone_scraped']['zone_id'])
            logger.info(f"\n📊 Updated Stats:")
            logger.info(f"   Businesses Linked: {stats1['businesses_linked']}")
        
        # Scrape second zone
        logger.info(f"\n\n🎯 SCRAPING ZONE 2:")
        logger.info("-" * 60)
        async with AsyncSessionLocal() as db:
            result2 = await scrape_zone(db)
            await db.commit()
            
            logger.info(f"\n✅ Zone 2 Complete!")
            logger.info(f"   Zone: {result2['zone_scraped']['zone_id']}")
            logger.info(f"   Raw Businesses: {result2['results']['raw_businesses']}")
            logger.info(f"   Qualified Leads: {result2['results']['qualified_leads']}")
            logger.info(f"   New Businesses: {result2['results']['new_businesses']}")
            logger.info(f"   With Websites: {result2['results'].get('with_websites', 0)}")
            logger.info(f"   Without Websites: {result2['results'].get('without_websites', 0)}")
            
            # Check updated stats
            stats2 = await get_zone_stats(db, result2['zone_scraped']['zone_id'])
            logger.info(f"\n📊 Updated Stats:")
            logger.info(f"   Businesses Linked: {stats2['businesses_linked']}")
        
        # Show final stats
        logger.info(f"\n\n{'=' * 60}")
        logger.info("📊 FINAL RESULTS:")
        logger.info("=" * 60)
        async with AsyncSessionLocal() as db:
            for zone_id in ZONES_TO_SCRAPE:
                stats = await get_zone_stats(db, zone_id)
                if stats:
                    logger.info(f"\n  {zone_id}:")
                    logger.info(f"    Status: {stats['status']}")
                    logger.info(f"    Leads: {stats['lead_count']}")
                    logger.info(f"    Qualified: {stats['qualified_count']}")
                    logger.info(f"    Businesses Linked: {stats['businesses_linked']}")
                    logger.info(f"    Last Scraped: {stats['last_scraped']}")
        
        logger.info("\n✅ RESCRAPE COMPLETE!")
        logger.info("You can now refresh the Coverage page to see the updated data.\n")
        
    except Exception as e:
        logger.error(f"❌ Error during rescrape: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

