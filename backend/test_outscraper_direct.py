#!/usr/bin/env python3
"""
Direct test of Outscraper API to verify what data is actually returned.
Tests both REST API and Python library.
"""
import os
import sys
import json
import requests

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from outscraper import ApiClient
from core.config import get_settings

def test_rest_api():
    """Test Outscraper REST API directly"""
    settings = get_settings()
    api_key = settings.OUTSCRAPER_API_KEY
    
    print("="*80)
    print("🔍 TEST 1: Outscraper REST API (Direct HTTP)")
    print("="*80)
    
    url = "https://api.outscraper.cloud/google-maps-search"
    params = {
        "query": "Roto-Rooter Plumbing, Los Angeles, CA, USA",
        "limit": 1,
        "async": "false"
    }
    headers = {
        "X-API-KEY": api_key
    }
    
    print(f"\n📡 Making request to: {url}")
    print(f"📋 Query: {params['query']}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=60)
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n📦 Response structure:")
            print(f"  - Status: {data.get('status')}")
            print(f"  - Has data: {bool(data.get('data'))}")
            
            if data.get('data') and len(data['data']) > 0 and len(data['data'][0]) > 0:
                business = data['data'][0][0]
                print(f"\n🏢 First business:")
                print(f"  - Name: {business.get('name')}")
                print(f"  - Phone: {business.get('phone')}")
                print(f"  - Rating: {business.get('rating')}")
                print(f"  - Reviews: {business.get('reviews')}")
                print(f"\n🌐 WEBSITE FIELDS:")
                print(f"  - 'site': {business.get('site')}")
                print(f"  - 'website': {business.get('website')}")
                print(f"  - 'website_url': {business.get('website_url')}")
                
                print(f"\n📋 ALL KEYS ({len(business.keys())} total):")
                for key in sorted(business.keys()):
                    print(f"  - {key}")
                
                return business
        else:
            print(f"❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None


def test_python_library():
    """Test Outscraper Python library"""
    settings = get_settings()
    
    print("\n" + "="*80)
    print("🔍 TEST 2: Outscraper Python Library")
    print("="*80)
    
    client = ApiClient(settings.OUTSCRAPER_API_KEY)
    
    print(f"\n📡 Calling google_maps_search...")
    print(f"📋 Query: Roto-Rooter Plumbing, Los Angeles, CA, USA")
    
    try:
        results = client.google_maps_search(
            query=["Roto-Rooter Plumbing, Los Angeles, CA, USA"],
            limit=1,
            language='en'
        )
        
        print(f"✅ Got results!")
        print(f"  - Type: {type(results)}")
        print(f"  - Length: {len(results) if results else 0}")
        
        if results and len(results) > 0:
            business = results[0]
            print(f"\n🏢 First result:")
            print(f"  - Type: {type(business)}")
            print(f"  - Name: {business.get('name') if isinstance(business, dict) else 'N/A'}")
            
            if isinstance(business, dict):
                print(f"  - Phone: {business.get('phone')}")
                print(f"  - Rating: {business.get('rating')}")
                print(f"  - Reviews: {business.get('reviews')}")
                print(f"\n🌐 WEBSITE FIELDS:")
                print(f"  - 'site': {business.get('site')}")
                print(f"  - 'website': {business.get('website')}")
                print(f"  - 'website_url': {business.get('website_url')}")
                
                print(f"\n📋 ALL KEYS ({len(business.keys())} total):")
                for key in sorted(business.keys()):
                    print(f"  - {key}")
                
                return business
        else:
            print("❌ No results returned")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_results(rest_result, lib_result):
    """Compare REST API vs Python library results"""
    print("\n" + "="*80)
    print("🔬 COMPARISON: REST API vs Python Library")
    print("="*80)
    
    if not rest_result and not lib_result:
        print("❌ Both methods failed!")
        return
    
    if not rest_result:
        print("❌ REST API failed but library worked")
        return
    
    if not lib_result:
        print("❌ Library failed but REST API worked")
        return
    
    # Check 'site' field
    rest_site = rest_result.get('site')
    lib_site = lib_result.get('site')
    
    print(f"\n🌐 Website field comparison:")
    print(f"  REST API 'site': {rest_site}")
    print(f"  Library 'site':  {lib_site}")
    
    if rest_site and not lib_site:
        print("  ⚠️  REST API has 'site' but library doesn't!")
    elif not rest_site and not lib_site:
        print("  ⚠️  NEITHER has 'site' field - API may not return websites!")
    elif rest_site and lib_site:
        print("  ✅ Both have 'site' field")
    
    # Check key differences
    rest_keys = set(rest_result.keys())
    lib_keys = set(lib_result.keys())
    
    only_in_rest = rest_keys - lib_keys
    only_in_lib = lib_keys - rest_keys
    
    if only_in_rest:
        print(f"\n📋 Keys ONLY in REST API ({len(only_in_rest)}):")
        for key in sorted(only_in_rest):
            print(f"  - {key}")
    
    if only_in_lib:
        print(f"\n📋 Keys ONLY in Python library ({len(only_in_lib)}):")
        for key in sorted(only_in_lib):
            print(f"  - {key}")


if __name__ == "__main__":
    print("\n🚀 OUTSCRAPER API TEST SUITE\n")
    
    rest_result = test_rest_api()
    lib_result = test_python_library()
    compare_results(rest_result, lib_result)
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)

