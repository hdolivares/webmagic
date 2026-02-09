"""
Test LLM-powered website discovery with real business data.

This script:
1. Fetches a business from the database
2. Calls ScrapingDog to get search results
3. Uses LLM to analyze and pick the best match
4. Saves all intermediate data for analysis

Usage:
    # Test with a specific business by name
    python -m scripts.test_llm_discovery --name "Mr. Rooter Plumbing of Seattle"
    
    # Test with a business ID
    python -m scripts.test_llm_discovery --id "03270d47-b76a-4ff4-a0c7-90a105d70b63"
    
    # Test with multiple random businesses
    python -m scripts.test_llm_discovery --random 5
"""
import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func
from core.database import get_db_session_sync
from models.business import Business
from services.discovery.llm_discovery_service import LLMDiscoveryService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_discovery_for_business(business: Business):
    """Test discovery for a single business."""
    logger.info(f"\n{'='*80}")
    logger.info(f"🏢 TESTING DISCOVERY FOR: {business.name}")
    logger.info(f"{'='*80}")
    logger.info(f"  ID: {business.id}")
    logger.info(f"  Phone: {business.phone or 'N/A'}")
    logger.info(f"  Address: {business.address or 'N/A'}")
    logger.info(f"  Location: {business.city}, {business.state}")
    logger.info(f"  Current URL: {business.website_url or 'None'}")
    logger.info(f"  Current Status: {business.website_validation_status}")
    
    # Initialize service
    service = LLMDiscoveryService()
    
    # Run discovery
    logger.info(f"\n🔍 Starting discovery process...")
    
    result = await service.discover_website(
        business_name=business.name,
        phone=business.phone,
        address=business.address,
        city=business.city,
        state=business.state,
        country=business.country or "US"
    )
    
    # Display results
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 DISCOVERY RESULTS")
    logger.info(f"{'='*80}")
    logger.info(f"  Found: {'✅ YES' if result['found'] else '❌ NO'}")
    logger.info(f"  URL: {result['url'] or 'None'}")
    logger.info(f"  Confidence: {result['confidence']:.2f}")
    logger.info(f"  LLM Model: {result.get('llm_model', 'N/A')}")
    logger.info(f"\n  Reasoning: {result['reasoning']}")
    
    if result.get('llm_analysis'):
        match_signals = result['llm_analysis'].get('match_signals', {})
        logger.info(f"\n  Match Signals:")
        for signal, value in match_signals.items():
            logger.info(f"    - {signal}: {value}")
    
    # Save detailed results
    output_dir = Path(__file__).parent.parent / "test_output" / "llm_discovery"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"discovery_{business.name[:30].replace(' ', '_')}_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "business": {
                "id": str(business.id),
                "name": business.name,
                "phone": business.phone,
                "address": business.address,
                "city": business.city,
                "state": business.state
            },
            "discovery_result": result
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n💾 Detailed results saved to: {output_file}")
    logger.info(f"{'='*80}\n")
    
    return result


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LLM-powered website discovery")
    parser.add_argument("--name", type=str, help="Business name to search")
    parser.add_argument("--id", type=str, help="Business ID to test")
    parser.add_argument(
        "--random",
        type=int,
        help="Test N random businesses without websites"
    )
    parser.add_argument(
        "--status",
        type=str,
        default="missing",
        help="Filter businesses by status (default: missing)"
    )
    
    args = parser.parse_args()
    
    with get_db_session_sync() as db:
        businesses = []
        
        if args.id:
            # Test specific business by ID
            business = db.query(Business).filter(Business.id == args.id).first()
            if not business:
                logger.error(f"❌ Business not found: {args.id}")
                return
            businesses = [business]
            
        elif args.name:
            # Test specific business by name
            business = db.query(Business).filter(
                func.lower(Business.name).like(f"%{args.name.lower()}%")
            ).first()
            if not business:
                logger.error(f"❌ Business not found: {args.name}")
                return
            businesses = [business]
            
        elif args.random:
            # Test random businesses without websites
            businesses = db.query(Business).filter(
                Business.website_url.is_(None),
                Business.website_validation_status == args.status
            ).order_by(
                func.random()
            ).limit(args.random).all()
            
            if not businesses:
                logger.error(f"❌ No businesses found with status '{args.status}'")
                return
        else:
            parser.print_help()
            logger.error("\n❌ Please provide --name, --id, or --random")
            return
        
        logger.info(f"🧪 Testing discovery for {len(businesses)} business(es)...\n")
        
        # Test each business
        results = []
        for i, business in enumerate(businesses, 1):
            if i > 1:
                logger.info(f"\n⏳ Waiting 2 seconds before next test...\n")
                await asyncio.sleep(2)
            
            result = await test_discovery_for_business(business)
            results.append({
                "business_name": business.name,
                "found": result['found'],
                "url": result['url'],
                "confidence": result['confidence']
            })
        
        # Summary
        logger.info(f"\n{'='*80}")
        logger.info(f"📈 SUMMARY ({len(businesses)} businesses)")
        logger.info(f"{'='*80}")
        found_count = sum(1 for r in results if r['found'])
        logger.info(f"  Found: {found_count}/{len(businesses)} ({100*found_count/len(businesses):.1f}%)")
        logger.info(f"  Not Found: {len(businesses)-found_count}/{len(businesses)}")
        
        if found_count > 0:
            logger.info(f"\n  Discovered URLs:")
            for r in results:
                if r['found']:
                    logger.info(f"    ✅ {r['business_name']}: {r['url']} (conf: {r['confidence']:.2f})")


if __name__ == "__main__":
    asyncio.run(main())
