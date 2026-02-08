"""
Simple validation test - tests prescreener and model configuration.
Does not require database or Playwright.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("\n" + "="*70)
print("SIMPLE VALIDATION TEST")
print("="*70 + "\n")

# Test 1: URL Prescreener
print("1. Testing URL Prescreener...")
from services.validation.url_prescreener import URLPrescreener

prescreener = URLPrescreener()

test_urls = [
    ("https://example.com/document.pdf", "should skip"),
    ("https://drive.google.com/file/d/123", "should skip"),
    ("https://www.google.com", "should proceed"),
    ("https://business.cantonchamber.org/member/test", "should proceed"),
]

for url, expected in test_urls:
    result = prescreener.prescreen_url(url)
    status = "✓" if ("skip" in expected and not result["should_validate"]) or ("proceed" in expected and result["should_validate"]) else "✗"
    print(f"  {status} {url}")
    print(f"     -> {result['recommendation']}: {result.get('skip_reason', 'OK')}")

print("\n2. Testing Configuration...")
from core.config import get_settings

settings = get_settings()
llm_model = getattr(settings, 'LLM_MODEL', 'NOT_SET')
print(f"  ✓ Config LLM_MODEL: {llm_model}")

print("\n3. Testing LLM Validator initialization...")
from services.validation.llm_validator import LLMWebsiteValidator

try:
    validator = LLMWebsiteValidator()
    print(f"  ✓ LLM Validator initialized with model: {validator.model}")
    print(f"  ✓ API key configured: {'Yes' if validator.api_key else 'No'}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "="*70)
print("✅ SIMPLE TEST COMPLETE")
print("="*70 + "\n")
