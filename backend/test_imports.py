#!/usr/bin/env python3
"""
Import Validation Script
Tests all critical imports to catch issues before deployment.
"""

import sys

def test_imports():
    """Test all critical imports."""
    failures = []
    
    print("🧪 Testing imports...")
    
    # Test core imports
    tests = [
        ("core.database", ["get_db"]),
        ("api.deps", ["get_current_user"]),
        ("models.user", ["AdminUser"]),
        ("models.scrape_session", ["ScrapeSession"]),
        ("models.geo_strategy", ["GeoStrategy"]),
        ("services.progress.redis_service", ["RedisService"]),
        ("services.progress.progress_publisher", ["ProgressPublisher"]),
        ("tasks.scraping_tasks", ["scrape_zone_async"]),
        ("api.v1.endpoints.scrapes", ["router"]),
        ("api.v1.router", ["api_router"]),
    ]
    
    for module_name, items in tests:
        try:
            module = __import__(module_name, fromlist=items)
            for item in items:
                if not hasattr(module, item):
                    failures.append(f"❌ {module_name}.{item} not found")
                else:
                    print(f"✅ {module_name}.{item}")
        except Exception as e:
            failures.append(f"❌ {module_name}: {str(e)}")
            print(f"❌ {module_name}: {str(e)}")
    
    # Summary
    print("\n" + "="*60)
    if failures:
        print(f"❌ FAILED: {len(failures)} import(s) failed")
        for failure in failures:
            print(f"  {failure}")
        return False
    else:
        print("✅ SUCCESS: All imports validated")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
