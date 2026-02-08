"""
Test script for LLM-powered validation pipeline.

Quick sanity check to verify the pipeline works before running on production data.
Tests all three stages: Prescreener -> Playwright -> LLM.

Usage:
    python -m scripts.test_llm_validation
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.validation.url_prescreener import URLPrescreener
from services.validation.validation_orchestrator import ValidationOrchestrator
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Test cases covering different scenarios
TEST_CASES = [
    {
        "name": "Test 1: PDF URL (should fail prescreen)",
        "business": {
            "name": "Test Plumbing",
            "phone": "555-123-4567",
            "email": "test@test.com",
            "address": "123 Main St",
            "city": "Canton",
            "state": "OH",
            "country": "US",
        },
        "url": "https://example.com/document.pdf",
        "expected_verdict": "missing"
    },
    {
        "name": "Test 2: Google Drive link (should fail prescreen)",
        "business": {
            "name": "Test Services",
            "phone": "555-999-8888",
            "email": "test@example.com",
            "address": "456 Oak Ave",
            "city": "Cleveland",
            "state": "OH",
            "country": "US",
        },
        "url": "https://drive.google.com/file/d/abc123/view",
        "expected_verdict": "missing"
    },
    {
        "name": "Test 3: Real business website (should pass all stages)",
        "business": {
            "name": "Google",
            "phone": "650-253-0000",
            "email": "info@google.com",
            "address": "1600 Amphitheatre Parkway",
            "city": "Mountain View",
            "state": "CA",
            "country": "US",
        },
        "url": "https://www.google.com",
        "expected_verdict": "valid"
    }
]


async def run_test_case(test_case: dict, orchestrator: ValidationOrchestrator):
    """Run a single test case."""
    logger.info("=" * 80)
    logger.info(test_case["name"])
    logger.info("=" * 80)
    
    try:
        result = await orchestrator.validate_business_website(
            business=test_case["business"],
            url=test_case["url"],
            timeout=30000,
            capture_screenshot=False
        )
        
        verdict = result.get("verdict")
        confidence = result.get("confidence", 0)
        reasoning = result.get("reasoning", "")
        expected = test_case.get("expected_verdict", "unknown")
        
        # Check if verdict matches expectation
        passed = "✅ PASS" if verdict == expected else "❌ FAIL"
        
        logger.info(f"\nURL: {test_case['url']}")
        logger.info(f"Business: {test_case['business']['name']}")
        logger.info(f"Expected: {expected}")
        logger.info(f"Got: {verdict} (confidence={confidence:.2f})")
        logger.info(f"Reasoning: {reasoning}")
        logger.info(f"Result: {passed}")
        
        # Show which stages ran
        stages = result.get("stages", {})
        logger.info(f"\nStages executed:")
        logger.info(f"  - Prescreen: {'✓' if stages.get('prescreen') else '✗'}")
        logger.info(f"  - Playwright: {'✓' if stages.get('playwright') else '✗'}")
        logger.info(f"  - LLM: {'✓' if stages.get('llm') else '✗'}")
        
        return verdict == expected
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        return False


async def main():
    """Run all test cases."""
    logger.info("\n" + "=" * 80)
    logger.info("LLM VALIDATION PIPELINE TEST SUITE")
    logger.info("=" * 80 + "\n")
    
    # First, test the prescreener in isolation
    logger.info("Testing URL Prescreener in isolation...")
    prescreener = URLPrescreener()
    
    test_urls = [
        ("https://example.com/doc.pdf", False),
        ("https://drive.google.com/file/d/123", False),
        ("https://www.google.com", True),
    ]
    
    for url, should_pass in test_urls:
        result = prescreener.prescreen_url(url)
        passed = result["should_validate"] == should_pass
        status = "✅" if passed else "❌"
        logger.info(f"  {status} {url}: {result['recommendation']}")
    
    logger.info("\n" + "-" * 80 + "\n")
    
    # Now test the complete pipeline
    logger.info("Testing complete validation pipeline...\n")
    
    passed = 0
    failed = 0
    
    async with ValidationOrchestrator() as orchestrator:
        for test_case in TEST_CASES:
            success = await run_test_case(test_case, orchestrator)
            if success:
                passed += 1
            else:
                failed += 1
            
            # Brief pause between tests
            await asyncio.sleep(1)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total tests: {len(TEST_CASES)}")
    logger.info(f"Passed: {passed} ✅")
    logger.info(f"Failed: {failed} ❌")
    logger.info("=" * 80 + "\n")
    
    if failed > 0:
        logger.error("Some tests failed! Review the output above.")
        sys.exit(1)
    else:
        logger.info("All tests passed! Pipeline is ready for production.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
