"""
Test Outscraper API Response Structure

This script makes a real Outscraper API call and logs the complete
response structure to verify field names we should be parsing.

CRITICAL: This helps us validate our assumptions about field names
before running re-validation on all 457 businesses.

Usage:
    python -m scripts.test_outscraper_payload
"""
import asyncio
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_settings
from services.hunter.scraper import OutscraperClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


def analyze_business_structure(business: Dict[str, Any], index: int):
    """
    Analyze a single business result and log its structure.
    """
    logger.info("="*80)
    logger.info(f"BUSINESS #{index + 1}")
    logger.info("="*80)
    
    # Log business name first
    name = business.get("name", "UNKNOWN")
    logger.info(f"Name: {name}")
    logger.info("")
    
    # Log ALL available keys
    logger.info("📋 ALL AVAILABLE KEYS:")
    all_keys = list(business.keys())
    for i, key in enumerate(sorted(all_keys), 1):
        value_type = type(business[key]).__name__
        value_preview = str(business[key])[:100] if business[key] else "None"
        logger.info(f"  {i:2d}. {key:30s} ({value_type:10s}) = {value_preview}")
    logger.info("")
    
    # Check for website-related fields specifically
    logger.info("🌐 WEBSITE-RELATED FIELDS:")
    website_fields = [
        "website", "site", "url", "domain", "website_url", 
        "business_url", "web", "homepage", "link", "web_site"
    ]
    
    found_website_fields = []
    for field in website_fields:
        value = business.get(field)
        if value is not None:
            logger.info(f"  ✅ {field:20s} = {value}")
            found_website_fields.append(field)
        else:
            logger.info(f"  ❌ {field:20s} = NOT FOUND")
    
    logger.info("")
    logger.info(f"Found {len(found_website_fields)} website-related fields: {', '.join(found_website_fields)}")
    logger.info("")
    
    # Check raw_data suitability
    logger.info("💾 RAW DATA ANALYSIS:")
    logger.info(f"  Total keys: {len(all_keys)}")
    logger.info(f"  JSON size: {len(json.dumps(business))} bytes")
    logger.info(f"  Suitable for raw_data storage: {'✅ YES' if len(json.dumps(business)) < 100000 else '⚠️  LARGE'}")
    logger.info("")
    
    # Check for Google Maps specific fields
    logger.info("📍 GOOGLE MAPS FIELDS:")
    gmap_fields = ["google_id", "place_id", "cid", "google_url", "maps_url"]
    for field in gmap_fields:
        value = business.get(field)
        if value:
            logger.info(f"  ✅ {field:20s} = {str(value)[:80]}")
    logger.info("")
    
    # Check for contact fields
    logger.info("📞 CONTACT FIELDS:")
    contact_fields = ["phone", "email", "full_address", "city", "state", "postal_code"]
    for field in contact_fields:
        value = business.get(field)
        if value:
            logger.info(f"  ✅ {field:20s} = {value}")
    logger.info("")
    
    # Check for business info fields
    logger.info("ℹ️  BUSINESS INFO FIELDS:")
    info_fields = ["type", "category", "subtypes", "rating", "reviews", "review_count"]
    for field in info_fields:
        value = business.get(field)
        if value is not None:
            logger.info(f"  ✅ {field:20s} = {value}")
    logger.info("")


async def test_outscraper_structure():
    """
    Make a test Outscraper API call and analyze the response structure.
    """
    logger.info("="*80)
    logger.info("OUTSCRAPER API RESPONSE STRUCTURE TEST")
    logger.info("="*80)
    logger.info("")
    
    # Check if API key is configured
    outscraper_api_key = getattr(settings, "OUTSCRAPER_API_KEY", None)
    if not outscraper_api_key:
        logger.error("❌ OUTSCRAPER_API_KEY not configured in .env")
        logger.error("Cannot test without API key")
        return
    
    logger.info(f"✅ API Key configured: {outscraper_api_key[:10]}...{outscraper_api_key[-4:]}")
    logger.info("")
    
    # Initialize client
    client = OutscraperClient(api_key=outscraper_api_key)
    
    # Make a small test query (2 businesses only to save API credits)
    query = "plumbers"
    city = "Houston"
    state = "TX"
    country = "US"
    limit = 2
    
    logger.info(f"📡 Making test query: '{query} in {city}, {state}'")
    logger.info(f"   Limit: {limit} businesses")
    logger.info("")
    
    try:
        response = await client.search_businesses(
            query=query,
            city=city,
            state=state,
            country=country,
            limit=limit,
            language="en"
        )
        
        results = response.get("businesses", [])
        
        if not results:
            logger.error("❌ No results returned from Outscraper")
            return
        
        logger.info(f"✅ Received {len(results)} business(es)")
        logger.info("")
        
        # Analyze each business
        for idx, business in enumerate(results):
            analyze_business_structure(business, idx)
            
            # Save first business to file for detailed inspection
            if idx == 0:
                output_file = Path(__file__).parent / "outscraper_sample_response.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(business, f, indent=2, ensure_ascii=False)
                logger.info(f"💾 Saved first business to: {output_file}")
                logger.info("")
        
        # Summary
        logger.info("="*80)
        logger.info("SUMMARY & RECOMMENDATIONS")
        logger.info("="*80)
        
        # Check if our assumed field names are correct
        first_business = results[0]
        
        logger.info("🔍 Field Name Validation:")
        logger.info("")
        
        # Website field
        website_value = None
        website_field_used = None
        for field in ["website", "site", "url", "domain", "website_url", "business_url"]:
            if first_business.get(field):
                website_value = first_business.get(field)
                website_field_used = field
                break
        
        if website_value:
            logger.info(f"  ✅ Website field found: '{website_field_used}' = {website_value}")
        else:
            logger.info(f"  ⚠️  No website field found in any expected names")
        logger.info("")
        
        # Place ID field
        place_id = first_business.get("place_id")
        if place_id:
            logger.info(f"  ✅ Place ID found: {place_id}")
        else:
            logger.info(f"  ⚠️  No 'place_id' field found")
        logger.info("")
        
        # Rating field
        rating = first_business.get("rating")
        reviews = first_business.get("reviews")
        if rating is not None:
            logger.info(f"  ✅ Rating found: {rating} ({reviews} reviews)")
        else:
            logger.info(f"  ⚠️  No 'rating' field found")
        logger.info("")
        
        logger.info("📝 Recommendations:")
        logger.info("")
        
        if website_field_used:
            logger.info(f"  1. ✅ Our scraper should look for '{website_field_used}' field")
        else:
            logger.info(f"  1. ⚠️  Need to investigate why no website field is present")
        
        logger.info(f"  2. ✅ Store complete response in 'raw_data' field")
        logger.info(f"  3. ✅ Verify field names in scraper.py match this output")
        logger.info("")
        
        logger.info("="*80)
        logger.info("✅ Test complete! Review output above.")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"❌ Error during test: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    asyncio.run(test_outscraper_structure())


if __name__ == "__main__":
    main()

