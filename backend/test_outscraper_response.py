"""
Quick test to see what Outscraper actually returns.
"""
import asyncio
import sys
sys.path.insert(0, '/var/www/webmagic/backend')

from services.hunter.scraper import OutscraperClient
from core.config import get_settings

async def test_outscraper():
    settings = get_settings()
    client = OutscraperClient(settings.OUTSCRAPER_API_KEY)
    
    # Test with a simple query
    results = await client.search_businesses(
        query="Roto-Rooter",
        city="Los Angeles",
        state="CA",
        country="US",
        limit=3
    )
    
    print("\n" + "="*80)
    print("OUTSCRAPER TEST RESULTS")
    print("="*80)
    
    businesses = results.get("businesses", [])
    print(f"\nTotal businesses returned: {len(businesses)}")
    
    if businesses:
        first_biz = businesses[0]
        print(f"\nFirst business name: {first_biz.get('name')}")
        print(f"\nAll keys in first business:")
        print(sorted(first_biz.keys()))
        
        # Check for website fields
        print(f"\n'site' field: {first_biz.get('site')}")
        print(f"'website_url' field: {first_biz.get('website_url')}")
        print(f"'website' field: {first_biz.get('website')}")
        
        # Show first business structure (truncated)
        import json
        print(f"\nFirst business (full):")
        print(json.dumps(first_biz, indent=2, default=str)[:2000])
    
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(test_outscraper())

