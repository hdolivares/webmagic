"""
Test what Outscraper actually returns for LA Hollywood zone.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from outscraper import ApiClient
from core.config import get_settings

async def test_hollywood_search():
    """Test Outscraper with Hollywood coordinates."""
    settings = get_settings()
    
    # Hollywood coordinates from strategy
    lat = 34.0928
    lon = -118.3287
    
    # Initialize Outscraper client
    client = ApiClient(api_key=settings.OUTSCRAPER_API_KEY)
    
    # Test 1: Geo-specific search (what we're using)
    search_query = f"plumbers near {lat},{lon}"
    print(f"\n🔍 Test 1: Geo-specific search")
    print(f"Query: {search_query}")
    print(f"Limit: 25")
    print("-" * 80)
    
    results = client.google_maps_search(
        query=[search_query],
        limit=25,
        language='en',
        region='us'
    )
    
    # Flatten nested list
    if results and isinstance(results, list) and len(results) > 0:
        results = results[0]
    
    print(f"\n📊 Results: {len(results)} businesses found\n")
    
    # Show first 10 businesses with their locations
    for i, biz in enumerate(results[:10], 1):
        name = biz.get('name', 'Unknown')
        city = biz.get('city', 'N/A')
        state = biz.get('state', biz.get('region', 'N/A'))
        website = biz.get('website', biz.get('site', 'N/A'))
        
        print(f"{i}. {name}")
        print(f"   Location: {city}, {state}")
        print(f"   Website: {website}")
        print()
    
    # Test 2: City-based search (for comparison)
    print("\n" + "=" * 80)
    print(f"\n🔍 Test 2: City-based search")
    search_query2 = "plumbers in Los Angeles, CA, US"
    print(f"Query: {search_query2}")
    print(f"Limit: 25")
    print("-" * 80)
    
    results2 = client.google_maps_search(
        query=[search_query2],
        limit=25,
        language='en',
        region='us'
    )
    
    # Flatten nested list
    if results2 and isinstance(results2, list) and len(results2) > 0:
        results2 = results2[0]
    
    print(f"\n📊 Results: {len(results2)} businesses found\n")
    
    # Show first 10 businesses with their locations
    for i, biz in enumerate(results2[:10], 1):
        name = biz.get('name', 'Unknown')
        city = biz.get('city', 'N/A')
        state = biz.get('state', biz.get('region', 'N/A'))
        website = biz.get('website', biz.get('site', 'N/A'))
        
        print(f"{i}. {name}")
        print(f"   Location: {city}, {state}")
        print(f"   Website: {website}")
        print()

if __name__ == "__main__":
    asyncio.run(test_hollywood_search())

