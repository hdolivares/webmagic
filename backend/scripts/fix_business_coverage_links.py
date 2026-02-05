"""
Fix Business Coverage Links

This script fixes the missing coverage_grid_id links on existing businesses.
Run this after deploying the hunter_service fix to link existing businesses to their zones.

The issue: Businesses were created before coverage grids, so coverage_grid_id was never set.
The fix: Match businesses to coverage grids based on city, state, industry, and zone location.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import get_settings
from models.business import Business
from models.coverage import CoverageGrid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_business_coverage_links():
    """
    Link businesses to their coverage grids based on location and category.
    """
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.begin() as conn:
            # Get all businesses without coverage_grid_id
            result = await conn.execute(
                select(Business).where(Business.coverage_grid_id.is_(None))
            )
            businesses = result.scalars().all()
            
            logger.info(f"Found {len(businesses)} businesses without coverage_grid_id")
            
            if len(businesses) == 0:
                logger.info("✅ All businesses already linked to coverage grids!")
                return
            
            fixed_count = 0
            no_match_count = 0
            
            for business in businesses:
                # Skip None or invalid businesses
                if business is None or not isinstance(business, Business):
                    logger.warning(f"Skipping invalid business object: {type(business)}")
                    no_match_count += 1
                    continue
                
                # Skip businesses without required fields
                if not business.city or not business.state or not business.category:
                    logger.warning(
                        f"Skipping business {business.name} - missing city, state, or category"
                    )
                    no_match_count += 1
                    continue
                
                # Try to find matching coverage grid
                # Match by city, state, and industry
                coverage_query = select(CoverageGrid).where(
                    CoverageGrid.city == business.city,
                    CoverageGrid.state == business.state,
                    CoverageGrid.industry.ilike(f"%{business.category}%")
                )
                
                coverage_result = await conn.execute(coverage_query)
                coverages = coverage_result.scalars().all()
                
                if len(coverages) == 0:
                    logger.warning(
                        f"No coverage grid found for business: {business.name} "
                        f"({business.city}, {business.state}, {business.category})"
                    )
                    no_match_count += 1
                    continue
                
                # If multiple matches, prefer zones over non-zones
                # Or just take the first match
                coverage = coverages[0]
                if len(coverages) > 1:
                    zone_coverage = [c for c in coverages if c.zone_id is not None]
                    if zone_coverage:
                        coverage = zone_coverage[0]
                
                # Update business with coverage_grid_id
                await conn.execute(
                    update(Business)
                    .where(Business.id == business.id)
                    .values(coverage_grid_id=coverage.id)
                )
                
                logger.info(
                    f"Linked business '{business.name}' to coverage grid "
                    f"'{coverage.city}, {coverage.state}, {coverage.industry}' "
                    f"(zone: {coverage.zone_id or 'N/A'})"
                )
                fixed_count += 1
            
            logger.info(f"\n✅ Fixed {fixed_count} businesses")
            logger.info(f"⚠️  Could not find coverage grids for {no_match_count} businesses")
            
            # Print summary statistics
            result = await conn.execute(
                select(
                    func.count(Business.id).label("total"),
                    func.count(Business.coverage_grid_id).label("with_coverage")
                )
            )
            stats = result.first()
            
            coverage_percentage = (stats.with_coverage / stats.total * 100) if stats.total > 0 else 0
            
            logger.info(f"\n📊 Summary:")
            logger.info(f"   Total businesses: {stats.total}")
            logger.info(f"   With coverage_grid_id: {stats.with_coverage}")
            logger.info(f"   Coverage: {coverage_percentage:.1f}%")
            
    except Exception as e:
        logger.error(f"Error fixing coverage links: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        await engine.dispose()


async def verify_coverage_stats():
    """
    Verify that zone statistics will now show data correctly.
    """
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    try:
        async with engine.begin() as conn:
            # Check la_downtown and la_koreatown zones
            for zone_id in ["la_downtown", "la_koreatown"]:
                result = await conn.execute(
                    select(CoverageGrid).where(CoverageGrid.zone_id == zone_id)
                )
                coverage = result.scalar_one_or_none()
                
                if not coverage:
                    logger.warning(f"Zone {zone_id} not found")
                    continue
                
                # Count businesses for this zone
                result = await conn.execute(
                    select(func.count(Business.id))
                    .where(Business.coverage_grid_id == coverage.id)
                )
                business_count = result.scalar()
                
                logger.info(f"\n📊 Zone: {zone_id}")
                logger.info(f"   Coverage Grid ID: {coverage.id}")
                logger.info(f"   Status: {coverage.status}")
                logger.info(f"   Lead Count: {coverage.lead_count}")
                logger.info(f"   Businesses Linked: {business_count}")
                logger.info(f"   Last Scraped: {coverage.last_scraped_at}")
                
    except Exception as e:
        logger.error(f"Error verifying stats: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await engine.dispose()


async def main():
    logger.info("="*60)
    logger.info("BUSINESS COVERAGE LINK FIX")
    logger.info("="*60)
    
    await fix_business_coverage_links()
    
    logger.info("\n" + "="*60)
    logger.info("VERIFYING ZONE STATISTICS")
    logger.info("="*60)
    
    await verify_coverage_stats()
    
    logger.info("\n✅ Fix complete!")
    logger.info("You can now refresh the Coverage page to see updated statistics.")


if __name__ == "__main__":
    asyncio.run(main())

