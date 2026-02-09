"""
Test ScrapingDog API to understand response structure and optimize usage.

This script:
1. Makes real API calls to ScrapingDog
2. Saves raw responses for analysis
3. Tests different query formats
4. Validates response structure

Usage:
    python -m scripts.test_scrapingdog --business-name "Acme Plumbing" --city Seattle --state WA
"""
import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp
from core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


async def test_scrapingdog_search(
    business_name: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: str = "US"
):
    """
    Test ScrapingDog API with a business search.
    
    Args:
        business_name: Name of the business to search
        city: City (optional)
        state: State (optional)
        country: Country code
    """
    api_key = getattr(settings, "SCRAPINGDOG_API_KEY", None)
    
    if not api_key:
        logger.error("❌ SCRAPINGDOG_API_KEY not configured in .env")
        return None
    
    logger.info(f"🔍 Testing ScrapingDog API...")
    logger.info(f"   Business: {business_name}")
    logger.info(f"   Location: {city}, {state}")
    
    # Build query
    query_parts = [f'"{business_name}"']
    if city:
        query_parts.append(city)
    if state:
        query_parts.append(state)
    query_parts.append("website")
    
    query = " ".join(query_parts)
    logger.info(f"   Query: {query}")
    
    # API parameters
    base_url = "https://api.scrapingdog.com/google"
    params = {
        "api_key": api_key,
        "query": query,
        "results": 10,
        "country": country.lower(),
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"📡 Making API request...")
            
            async with session.get(base_url, params=params, timeout=30) as response:
                status = response.status
                logger.info(f"   Status Code: {status}")
                
                if status != 200:
                    text = await response.text()
                    logger.error(f"❌ API Error: {text}")
                    return None
                
                # Get raw response
                data = await response.json()
                
                # Save to file for analysis
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = Path(__file__).parent.parent / "test_output" / "scrapingdog"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = output_dir / f"search_{timestamp}.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "query": query,
                        "business_name": business_name,
                        "city": city,
                        "state": state,
                        "timestamp": timestamp,
                        "response": data
                    }, f, indent=2, ensure_ascii=False)
                
                logger.info(f"💾 Saved response to: {output_file}")
                
                # Analyze response
                analyze_response(data, business_name)
                
                return data
                
    except aiohttp.ClientTimeout:
        logger.error("❌ Request timeout")
        return None
    except Exception as e:
        logger.error(f"❌ Error: {type(e).__name__}: {e}")
        return None


def analyze_response(data: dict, business_name: str):
    """Analyze ScrapingDog response structure."""
    logger.info("\n" + "="*80)
    logger.info("📊 RESPONSE ANALYSIS")
    logger.info("="*80)
    
    # Top-level keys
    logger.info(f"\n🔑 Response Keys: {list(data.keys())}")
    
    # Organic results
    organic_results = data.get("organic_results", [])
    logger.info(f"\n📋 Found {len(organic_results)} organic results")
    
    if organic_results:
        logger.info("\n🔍 First 5 Results:")
        for i, result in enumerate(organic_results[:5], 1):
            logger.info(f"\n  Result #{i}:")
            logger.info(f"    Keys: {list(result.keys())}")
            logger.info(f"    Title: {result.get('title', 'N/A')[:80]}")
            logger.info(f"    URL: {result.get('link') or result.get('url', 'N/A')}")
            snippet = result.get('snippet', 'N/A')
            logger.info(f"    Snippet: {snippet[:120]}{'...' if len(snippet) > 120 else ''}")
            
            # Check for business name in result
            title_lower = result.get('title', '').lower()
            snippet_lower = snippet.lower()
            business_lower = business_name.lower()
            
            name_in_title = business_lower in title_lower
            name_in_snippet = business_lower in snippet_lower
            
            logger.info(f"    Business name in title: {'✅' if name_in_title else '❌'}")
            logger.info(f"    Business name in snippet: {'✅' if name_in_snippet else '❌'}")
    
    # Other sections
    if "knowledge_graph" in data:
        logger.info(f"\n📚 Knowledge Graph: {data['knowledge_graph'].get('title', 'N/A')}")
    
    if "related_searches" in data:
        related = data.get("related_searches", [])
        logger.info(f"\n🔗 Related Searches: {len(related)} items")
        if related:
            logger.info(f"    Examples: {[r.get('query', 'N/A') for r in related[:3]]}")
    
    if "ads" in data:
        ads = data.get("ads", [])
        logger.info(f"\n💰 Ads: {len(ads)} results")
    
    logger.info("\n" + "="*80 + "\n")


async def test_multiple_businesses():
    """Test with multiple real businesses to understand patterns."""
    
    test_cases = [
        {
            "name": "Mr. Rooter Plumbing of Seattle",
            "city": "Seattle",
            "state": "WA"
        },
        {
            "name": "Pimlico Plumbers",
            "city": "London",
            "state": None
        },
        {
            "name": "ABC Plumbing Services",
            "city": "Los Angeles",
            "state": "CA"
        }
    ]
    
    logger.info("🧪 Testing multiple businesses...\n")
    
    for i, test in enumerate(test_cases, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST CASE {i}/{len(test_cases)}")
        logger.info(f"{'='*80}")
        
        await test_scrapingdog_search(
            business_name=test["name"],
            city=test["city"],
            state=test["state"]
        )
        
        if i < len(test_cases):
            logger.info("\n⏳ Waiting 2 seconds before next test...")
            await asyncio.sleep(2)


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test ScrapingDog API integration"
    )
    parser.add_argument(
        "--business-name",
        type=str,
        help="Business name to search"
    )
    parser.add_argument(
        "--city",
        type=str,
        help="City location"
    )
    parser.add_argument(
        "--state",
        type=str,
        help="State location"
    )
    parser.add_argument(
        "--test-suite",
        action="store_true",
        help="Run test suite with multiple businesses"
    )
    
    args = parser.parse_args()
    
    if args.test_suite:
        await test_multiple_businesses()
    elif args.business_name:
        await test_scrapingdog_search(
            business_name=args.business_name,
            city=args.city,
            state=args.state
        )
    else:
        parser.print_help()
        logger.error("\n❌ Please provide --business-name or --test-suite")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
