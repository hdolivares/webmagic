"""
Test script for Playwright validation service.
Validates that the service can successfully load and analyze a website.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.validation.playwright_service import PlaywrightValidationService


async def test_validation():
    """Test website validation with a simple example."""
    print("🚀 Testing Playwright Validation Service...\n")
    
    # Test URL
    test_url = "https://example.com"
    
    try:
        async with PlaywrightValidationService() as validator:
            print(f"✅ Service initialized successfully\n")
            print(f"🔍 Validating: {test_url}\n")
            
            result = await validator.validate_website(
                url=test_url,
                capture_screenshot=False  # Disable screenshot for faster testing
            )
            
            print("📊 Validation Result:")
            print("=" * 60)
            print(f"  ✓ Is Valid: {result['is_valid']}")
            print(f"  ✓ Title: {result.get('title')}")
            print(f"  ✓ Status Code: {result.get('status_code')}")
            print(f"  ✓ Load Time: {result.get('load_time_ms')}ms")
            print(f"  ✓ Quality Score: {result.get('quality_score')}/100")
            print(f"  ✓ Has Contact Info: {result.get('has_contact_info')}")
            print(f"  ✓ Word Count: {result.get('word_count')}")
            print(f"  ✓ Is Placeholder: {result.get('is_placeholder')}")
            
            if result.get('content_preview'):
                print(f"\n📝 Content Preview:")
                print(f"  {result['content_preview'][:200]}...")
            
            if result.get('error'):
                print(f"\n❌ Error: {result['error']}")
            
            print("\n" + "=" * 60)
            print("\n✅ Test completed successfully!")
            
            return result['is_valid']
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the test."""
    success = asyncio.run(test_validation())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

