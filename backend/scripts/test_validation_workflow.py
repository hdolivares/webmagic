"""
Test script for the validation workflow integration.
Demonstrates the flow: Scraping -> Simple Validation -> Queue Deep Validation
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.hunter.website_validator import WebsiteValidator


async def test_simple_validation():
    """Test the simple validation that runs during scraping."""
    print("🔍 Testing Simple Validation (Used During Scraping)")
    print("=" * 60)
    
    test_urls = [
        ("https://example.com", "Valid site"),
        ("https://facebook.com/somebusiness", "Social media (should reject)"),
        ("https://maps.google.com/place/xyz", "Google redirect (should reject)"),
        ("https://invalid-url", "Invalid URL"),
        ("", "No URL"),
    ]
    
    async with WebsiteValidator(timeout=5) as validator:
        for url, description in test_urls:
            try:
                result = await validator.validate_url(url)
                status = "✅ PASS" if result.is_valid and result.is_real_website else "❌ REJECT"
                print(f"\n{status} - {description}")
                print(f"  URL: {url}")
                print(f"  Valid: {result.is_valid}")
                print(f"  Real Website: {result.is_real_website}")
                if result.error_message:
                    print(f"  Reason: {result.error_message}")
            except Exception as e:
                print(f"\n❌ ERROR - {description}")
                print(f"  URL: {url}")
                print(f"  Error: {e}")
    
    print("\n" + "=" * 60)


async def test_workflow_simulation():
    """Simulate the complete workflow."""
    print("\n\n📋 Simulating Complete Validation Workflow")
    print("=" * 60)
    
    # Simulate scraped businesses
    scraped_businesses = [
        {
            "name": "Good Plumber Co",
            "website_url": "https://example.com",
            "email": "contact@goodplumber.com"
        },
        {
            "name": "Facebook Only Business",
            "website_url": "https://facebook.com/business",
            "email": "no-email@example.com"
        },
        {
            "name": "No Website Business",
            "website_url": None,
            "email": "test@business.com"
        }
    ]
    
    print(f"\n📥 Scraped {len(scraped_businesses)} businesses from Outscraper")
    
    # Step 1: Simple validation (during scraping)
    print("\n📊 Step 1: Simple Validation (Fast Filter)")
    businesses_to_deep_validate = []
    
    async with WebsiteValidator() as validator:
        for biz in scraped_businesses:
            url = biz.get("website_url")
            if not url:
                print(f"  • {biz['name']}: NO WEBSITE")
                continue
                
            result = await validator.validate_url(url)
            
            if result.is_valid and result.is_real_website:
                print(f"  ✅ {biz['name']}: PASSED SIMPLE CHECK - Queue for deep validation")
                businesses_to_deep_validate.append(biz)
            else:
                print(f"  ❌ {biz['name']}: REJECTED - {result.error_message}")
    
    # Step 2: Queue deep validation
    print(f"\n🎯 Step 2: Queue Deep Validation")
    print(f"  {len(businesses_to_deep_validate)} businesses queued for Playwright validation")
    print(f"  These will be processed asynchronously via Celery")
    
    # Step 3: Results
    print(f"\n✅ Workflow Complete!")
    print(f"  Total Scraped: {len(scraped_businesses)}")
    print(f"  Passed to Deep Validation: {len(businesses_to_deep_validate)}")
    print(f"  Filtered Out: {len(scraped_businesses) - len(businesses_to_deep_validate)}")
    
    print("\n" + "=" * 60)


def main():
    """Run the tests."""
    print("\n🧪 VALIDATION WORKFLOW TEST\n")
    
    asyncio.run(test_simple_validation())
    asyncio.run(test_workflow_simulation())
    
    print("\n\n📖 How It Works:")
    print("  1. During scraping: Fast simple validation filters bad URLs")
    print("  2. Good URLs are saved with status='pending'")
    print("  3. Playwright validation tasks are queued in batches")
    print("  4. Celery workers process validation asynchronously")
    print("  5. Results update business.website_validation_result")
    print("  6. No screenshots captured (disabled for performance)")
    print("\n✨ This keeps scraping FAST while still validating websites deeply!\n")


if __name__ == "__main__":
    main()

