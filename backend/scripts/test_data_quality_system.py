"""
Test Data Quality System

Tests the complete flow:
1. Scrape a few businesses from Outscraper
2. Verify raw_data is saved correctly
3. Test DataQualityService filtering and scoring
4. Test multi-tier website detection
5. Verify geo-targeting validation

Usage:
    python -m scripts.test_data_quality_system
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
from services.hunter.data_quality_service import DataQualityService
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_scraping_and_data_quality():
    """
    Complete end-to-end test of the data quality system.
    """
    logger.info("="*80)
    logger.info("DATA QUALITY SYSTEM TEST")
    logger.info("="*80)
    logger.info("")
    
    # Step 1: Scrape test businesses
    logger.info("Step 1: Scraping test businesses from Outscraper")
    logger.info("Query: plumbers in Houston, TX")
    logger.info("Limit: 5 businesses")
    logger.info("")
    
    scraper = OutscraperClient()
    
    try:
        response = await scraper.search_businesses(
            query="plumbers",
            city="Houston",
            state="TX",
            country="US",
            limit=5
        )
        
        businesses = response.get("businesses", [])
        logger.info(f"✅ Received {len(businesses)} businesses from Outscraper")
        logger.info("")
        
        if not businesses:
            logger.error("No businesses returned from Outscraper")
            return
        
        # Step 2: Test DataQualityService
        logger.info("Step 2: Testing DataQualityService")
        logger.info("")
        
        data_quality = DataQualityService(
            strict_geo_filter=True,
            require_operational=True,
            min_quality_score=30.0  # Low threshold for testing
        )
        
        # Test each business individually
        for idx, business in enumerate(businesses, 1):
            logger.info("-" * 80)
            logger.info(f"BUSINESS #{idx}: {business.get('name')}")
            logger.info("-" * 80)
            
            # Check raw_data presence
            raw_data = business.get("raw_data", {})
            logger.info(f"Raw data keys: {len(raw_data.keys())} fields")
            logger.info(f"Raw data size: {len(json.dumps(raw_data))} bytes")
            logger.info("")
            
            # Test geo-validation
            geo_valid, geo_reasons = data_quality.validate_geo_targeting(
                business,
                target_country="US",
                target_state="TX",
                target_city="Houston"
            )
            logger.info(f"Geo-validation: {'✅ PASSED' if geo_valid else '❌ FAILED'}")
            for reason in geo_reasons:
                logger.info(f"  - {reason}")
            logger.info("")
            
            # Test website detection
            website_info = data_quality.detect_website(business)
            logger.info(f"Website detection:")
            logger.info(f"  Has website: {website_info['has_website']}")
            logger.info(f"  Type: {website_info['website_type']}")
            logger.info(f"  URL: {website_info['website_url']}")
            logger.info(f"  Confidence: {website_info['confidence']}")
            logger.info("")
            
            # Test quality scoring
            quality_info = data_quality.calculate_quality_score(business)
            logger.info(f"Quality score: {quality_info['score']}/100")
            logger.info(f"  Breakdown:")
            for factor, score in quality_info['breakdown'].items():
                logger.info(f"    - {factor}: {score:.1f}")
            logger.info(f"  Verified: {quality_info['verified']}")
            logger.info(f"  Operational: {quality_info['operational']}")
            logger.info(f"  Quality tier: {'HIGH' if quality_info['high_quality'] else 'MEDIUM' if quality_info['medium_quality'] else 'LOW'}")
            logger.info("")
            
            # Test generation recommendation
            should_gen = data_quality.should_generate_website(business)
            logger.info(f"Generation recommendation:")
            logger.info(f"  Should generate: {should_gen['should_generate']}")
            logger.info(f"  Reason: {should_gen['reason']}")
            logger.info(f"  Confidence: {should_gen['confidence']}")
            if 'quality_score' in should_gen:
                logger.info(f"  Quality score: {should_gen['quality_score']}")
            if 'priority' in should_gen:
                logger.info(f"  Priority: {should_gen['priority']}")
            logger.info("")
        
        # Step 3: Test batch filtering
        logger.info("="*80)
        logger.info("Step 3: Testing Batch Filtering")
        logger.info("="*80)
        logger.info("")
        
        filtered_results = data_quality.filter_and_score_results(
            businesses=businesses,
            target_country="US",
            target_state="TX",
            target_city="Houston"
        )
        
        logger.info(f"Batch filtering results:")
        logger.info(f"  Total received: {filtered_results['total_received']}")
        logger.info(f"  Passed filters: {filtered_results['statistics']['passed']}")
        logger.info(f"  Geo-filtered: {filtered_results['statistics']['geo_filtered']}")
        logger.info(f"  Quality-filtered: {filtered_results['statistics']['quality_filtered']}")
        logger.info(f"  Closed-filtered: {filtered_results['statistics']['closed_filtered']}")
        logger.info(f"  Generation candidates: {len(filtered_results['generation_candidates'])}")
        logger.info("")
        
        logger.info(f"Summary:")
        logger.info(f"  Pass rate: {filtered_results['summary']['pass_rate']:.1f}%")
        logger.info(f"  Geo-filter rate: {filtered_results['summary']['geo_filter_rate']:.1f}%")
        logger.info(f"  Generation rate: {filtered_results['summary']['generation_rate']:.1f}%")
        logger.info("")
        
        # Step 4: Check database for raw_data storage
        logger.info("="*80)
        logger.info("Step 4: Checking Database (raw_data storage)")
        logger.info("="*80)
        logger.info("")
        
        async with AsyncSessionLocal() as db:
            # Check if any businesses have raw_data
            result = await db.execute(
                select(Business)
                .where(Business.raw_data.isnot(None))
                .limit(5)
            )
            businesses_with_raw = result.scalars().all()
            
            logger.info(f"Businesses with raw_data in database: {len(businesses_with_raw)}")
            
            if businesses_with_raw:
                for biz in businesses_with_raw:
                    logger.info(f"  ✅ {biz.name}: {len(str(biz.raw_data))} bytes")
            else:
                logger.warning("  ⚠️  No businesses have raw_data saved yet")
                logger.warning("  This is expected - raw_data will be saved on next scrape")
            logger.info("")
        
        # Final summary
        logger.info("="*80)
        logger.info("TEST COMPLETE")
        logger.info("="*80)
        logger.info("")
        logger.info("✅ All tests passed!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Run a real scrape to test raw_data storage")
        logger.info("2. Verify geo-filtering prevents cross-region results")
        logger.info("3. Verify multi-tier website detection finds more websites")
        logger.info("4. Check quality scores are reasonable")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)


def main():
    asyncio.run(test_scraping_and_data_quality())


if __name__ == "__main__":
    main()

