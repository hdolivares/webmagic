"""
Demo Script: Geo-Grid Enhanced Business Discovery System

This script demonstrates the new geo-grid subdivision system that dramatically
improves business discovery coverage by breaking cities into geographic zones.

Key Features Demonstrated:
1. Automatic city subdivision based on population
2. Zone-specific searches using GPS coordinates
3. Website validation to identify businesses needing websites
4. Comprehensive duplicate prevention
5. Progress tracking per zone

Usage:
    python scripts/demo_geo_grid_scraping.py --city "Los Angeles" --state "CA" --industry "plumbers"
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_db_session
from services.hunter.hunter_service import HunterService
from services.hunter.geo_grid import (
    create_city_grid,
    get_grid_summary,
    should_subdivide_city
)
import argparse


# City data lookup (in production, this would come from database)
CITY_DATA = {
    "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "population": 3900000, "state": "CA"},
    "New York": {"lat": 40.7128, "lon": -74.0060, "population": 8300000, "state": "NY"},
    "Chicago": {"lat": 41.8781, "lon": -87.6298, "population": 2700000, "state": "IL"},
    "Houston": {"lat": 29.7604, "lon": -95.3698, "population": 2300000, "state": "TX"},
    "Phoenix": {"lat": 33.4484, "lon": -112.0740, "population": 1700000, "state": "AZ"},
    "Austin": {"lat": 30.2672, "lon": -97.7431, "population": 990000, "state": "TX"},
    "San Diego": {"lat": 32.7157, "lon": -117.1611, "population": 1400000, "state": "CA"},
    "Dallas": {"lat": 32.7767, "lon": -96.7970, "population": 1300000, "state": "TX"},
    "Seattle": {"lat": 47.6062, "lon": -122.3321, "population": 750000, "state": "WA"},
    "Denver": {"lat": 39.7392, "lon": -104.9903, "population": 730000, "state": "CO"},
}


async def demo_geo_grid_scraping(
    city: str,
    state: str,
    industry: str,
    limit_per_zone: int = 50
):
    """
    Demonstrate geo-grid based scraping for a city.
    
    Args:
        city: City name
        state: State code
        industry: Business industry/category
        limit_per_zone: Results per zone
    """
    print("\n" + "="*70)
    print("🌐 GEO-GRID ENHANCED BUSINESS DISCOVERY SYSTEM")
    print("="*70)
    
    # Get city data
    city_info = CITY_DATA.get(city)
    if not city_info:
        print(f"\n❌ City '{city}' not in demo database.")
        print(f"Available cities: {', '.join(CITY_DATA.keys())}")
        return
    
    print(f"\n📍 Target Location: {city}, {state}")
    print(f"👥 Population: {city_info['population']:,}")
    print(f"🏢 Industry: {industry}")
    print(f"📊 Results per zone: {limit_per_zone}")
    
    # Check if city should be subdivided
    should_subdivide = should_subdivide_city(city_info['population'])
    print(f"\n🗺️  Geo-Grid Subdivision: {'✅ YES' if should_subdivide else '❌ NO'}")
    
    if should_subdivide:
        # Create zones
        zones = create_city_grid(
            city=city,
            state=state,
            center_lat=city_info['lat'],
            center_lon=city_info['lon'],
            population=city_info['population']
        )
        
        summary = get_grid_summary(zones)
        print(f"\n📐 Grid Configuration:")
        print(f"   • Grid Size: {summary['grid_size']}")
        print(f"   • Total Zones: {summary['total_zones']}")
        print(f"   • Zone Radius: {summary['zone_radius_km']} km")
        print(f"   • Coverage Area: ~{summary['approx_coverage_km2']} km²")
        
        print(f"\n🔍 Sample Zone Coordinates:")
        for i, zone in enumerate(zones[:5], 1):
            print(f"   Zone {zone.zone_id}: {zone.center_lat:.4f}, {zone.center_lon:.4f}")
        if len(zones) > 5:
            print(f"   ... and {len(zones) - 5} more zones")
    
    # Confirm before scraping
    print(f"\n⚠️  This will:")
    if should_subdivide:
        print(f"   • Create {len(zones)} coverage grid entries")
        print(f"   • Make {len(zones)} API calls to Outscraper")
        print(f"   • Cost approximately ${len(zones) * 0.50:.2f}")
    else:
        print(f"   • Create 1 coverage grid entry")
        print(f"   • Make 1 API call to Outscraper")
        print(f"   • Cost approximately $0.50")
    
    response = input("\n❓ Proceed with scraping? (yes/no): ")
    if response.lower() != 'yes':
        print("\n❌ Scraping cancelled.")
        return
    
    print("\n🚀 Starting scraping operation...")
    print("-" * 70)
    
    # Execute scraping
    async with get_db_session() as db:
        hunter = HunterService(db)
        
        result = await hunter.scrape_location_with_zones(
            city=city,
            state=state,
            industry=industry,
            country="US",
            limit_per_zone=limit_per_zone,
            priority=8,
            population=city_info['population'],
            city_lat=city_info['lat'],
            city_lon=city_info['lon']
        )
        
        await db.commit()
    
    # Display results
    print("\n" + "="*70)
    print("📊 SCRAPING RESULTS")
    print("="*70)
    
    print(f"\n✅ Status: {result['status']}")
    print(f"📍 Location: {result['location']}")
    print(f"🏢 Industry: {result['industry']}")
    
    if 'zones_scraped' in result:
        print(f"\n🗺️  Zones:")
        print(f"   • Zones Scraped: {result['zones_scraped']}")
        print(f"   • Total Businesses Found: {result['total_scraped']}")
        print(f"   • Qualified Businesses: {result['total_qualified']}")
        print(f"   • New Businesses Saved: {result['total_saved']}")
        
        # Qualification rate
        if result['total_scraped'] > 0:
            qual_rate = (result['total_qualified'] / result['total_scraped']) * 100
            print(f"   • Qualification Rate: {qual_rate:.1f}%")
        
        # Zone breakdown
        print(f"\n📈 Per-Zone Breakdown:")
        print(f"   {'Zone':<8} {'Scraped':<10} {'Qualified':<12} {'Saved':<10} {'More?':<8}")
        print("   " + "-"*60)
        
        for zone_result in result.get('zone_results', [])[:10]:
            zone_id = zone_result.get('zone_id', 'N/A')
            scraped = zone_result.get('scraped', 0)
            qualified = zone_result.get('qualified', 0)
            saved = zone_result.get('saved', 0)
            has_more = '✓' if zone_result.get('has_more') else '✗'
            
            print(f"   {zone_id:<8} {scraped:<10} {qualified:<12} {saved:<10} {has_more:<8}")
        
        if len(result.get('zone_results', [])) > 10:
            print(f"   ... and {len(result['zone_results']) - 10} more zones")
    else:
        # Single zone result
        print(f"\n📊 Results:")
        print(f"   • Businesses Found: {result.get('scraped', 0)}")
        print(f"   • Qualified Businesses: {result.get('qualified', 0)}")
        print(f"   • New Businesses Saved: {result.get('saved', 0)}")
        
        if 'qualification_rate' in result:
            print(f"   • Qualification Rate: {result['qualification_rate']:.1f}%")
    
    print("\n✅ Scraping complete!")
    print("="*70)


async def compare_strategies(
    city: str,
    state: str,
    industry: str
):
    """
    Compare traditional single-zone vs geo-grid multi-zone scraping.
    """
    print("\n" + "="*70)
    print("🔬 SCRAPING STRATEGY COMPARISON")
    print("="*70)
    
    city_info = CITY_DATA.get(city)
    if not city_info:
        print(f"\n❌ City '{city}' not in demo database.")
        return
    
    print(f"\n📍 Location: {city}, {state}")
    print(f"🏢 Industry: {industry}")
    print(f"👥 Population: {city_info['population']:,}")
    
    # Calculate traditional approach
    print(f"\n📊 Strategy A: Traditional Single Search")
    print(f"   • Searches: 1")
    print(f"   • Expected Results: ~50 businesses (near city center)")
    print(f"   • Coverage: Limited to downtown/central area")
    print(f"   • Cost: $0.50")
    print(f"   • Problem: Misses outlying neighborhoods")
    
    # Calculate geo-grid approach
    zones = create_city_grid(
        city=city,
        state=state,
        center_lat=city_info['lat'],
        center_lon=city_info['lon'],
        population=city_info['population']
    )
    
    summary = get_grid_summary(zones)
    
    print(f"\n📊 Strategy B: Geo-Grid Multi-Zone Search")
    print(f"   • Grid Size: {summary['grid_size']}")
    print(f"   • Searches: {summary['total_zones']}")
    print(f"   • Expected Results: ~{summary['total_zones'] * 50} businesses")
    print(f"   • Coverage: {summary['approx_coverage_km2']} km² (entire metro area)")
    print(f"   • Cost: ${summary['total_zones'] * 0.50:.2f}")
    print(f"   • Benefit: Complete, systematic coverage")
    
    # Calculate ROI
    cost_per_business_a = 0.50 / 50
    cost_per_business_b = (summary['total_zones'] * 0.50) / (summary['total_zones'] * 50)
    
    print(f"\n💰 Cost Efficiency:")
    print(f"   • Strategy A: ${cost_per_business_a:.3f} per business")
    print(f"   • Strategy B: ${cost_per_business_b:.3f} per business")
    print(f"   • Difference: {((cost_per_business_a - cost_per_business_b) / cost_per_business_a * 100):.1f}% more efficient")
    
    print(f"\n🎯 Recommendation:")
    if city_info['population'] >= 500000:
        print(f"   ✅ Use Geo-Grid Strategy B for maximum coverage")
        print(f"   ⚡ {summary['total_zones']}x more businesses discovered")
    elif city_info['population'] >= 100000:
        print(f"   ✅ Use Geo-Grid Strategy B for complete coverage")
        print(f"   ⚡ {summary['total_zones']}x more businesses discovered")
    else:
        print(f"   ⚠️  Single search may be sufficient for small cities")


async def main():
    parser = argparse.ArgumentParser(
        description="Demo geo-grid enhanced business scraping system"
    )
    parser.add_argument(
        "--city",
        type=str,
        required=True,
        help="City name (e.g., 'Los Angeles')"
    )
    parser.add_argument(
        "--state",
        type=str,
        required=True,
        help="State code (e.g., 'CA')"
    )
    parser.add_argument(
        "--industry",
        type=str,
        required=True,
        help="Business industry (e.g., 'plumbers')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Results per zone (default: 50)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Show comparison of strategies (no actual scraping)"
    )
    
    args = parser.parse_args()
    
    if args.compare:
        await compare_strategies(args.city, args.state, args.industry)
    else:
        await demo_geo_grid_scraping(
            args.city,
            args.state,
            args.industry,
            args.limit
        )


if __name__ == "__main__":
    asyncio.run(main())

