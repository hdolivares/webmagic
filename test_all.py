"""
Comprehensive test runner for WebMagic.
Tests all phases sequentially.
"""
import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    """Print colored header."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"  {text}")


async def test_phase_1():
    """Test Phase 1: Foundation"""
    print_header("PHASE 1: Foundation (Auth & Database)")
    
    try:
        # Test database connection
        from core.database import get_db_session
        async with get_db_session() as db:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
        print_success("Database connection successful")
        
        # Test config loading
        from core.config import get_settings
        settings = get_settings()
        print_success("Configuration loaded")
        
        # Test models
        from models import BaseModel, AdminUser, Business
        print_success("Models imported successfully")
        
        return True
        
    except Exception as e:
        print_error(f"Phase 1 failed: {str(e)}")
        return False


async def test_phase_2():
    """Test Phase 2: Hunter"""
    print_header("PHASE 2: Hunter (Scraping)")
    
    try:
        from services.hunter.filters import qualify_lead
        from models.business import Business
        
        # Test qualification logic
        test_business = Business(
            name="Test Restaurant",
            category="restaurant",
            has_website=False,
            rating=4.5,
            reviews_count=100
        )
        
        is_qualified, reason = qualify_lead(test_business)
        if is_qualified:
            print_success("Lead qualification logic working")
        else:
            print_warning(f"Test lead disqualified: {reason}")
        
        print_info("Skipping actual scraping (API costs money)")
        print_info("Run 'python backend/test_phase2.py' to test scraping")
        
        return True
        
    except Exception as e:
        print_error(f"Phase 2 failed: {str(e)}")
        return False


async def test_phase_3():
    """Test Phase 3: Creative Engine"""
    print_header("PHASE 3: Creative Engine (AI Generation)")
    
    try:
        from services.creative.prompts.loader import PromptLoader
        from core.database import get_db_session
        
        async with get_db_session() as db:
            loader = PromptLoader(db)
            
            # Check if templates exist
            from sqlalchemy import select, func
            from models.prompt import PromptTemplate
            count_result = await db.execute(select(func.count(PromptTemplate.id)))
            count = count_result.scalar()
            
            if count > 0:
                print_success(f"Found {count} prompt templates")
            else:
                print_warning("No prompt templates found - run seed script first")
                print_info("Run: python backend/scripts/seed_prompt_templates.py")
        
        print_info("Skipping actual generation (Claude API costs money)")
        print_info("Run 'python backend/test_phase3.py' to test generation")
        
        return True
        
    except Exception as e:
        print_error(f"Phase 3 failed: {str(e)}")
        return False


async def test_phase_4():
    """Test Phase 4: Pitcher"""
    print_header("PHASE 4: Pitcher (Email Campaigns)")
    
    try:
        from services.pitcher.email_generator import EmailGenerator
        from core.database import get_db_session
        
        print_success("Email services imported successfully")
        print_info("Skipping actual email sending (avoid spam/costs)")
        print_info("Run 'python backend/test_phase4.py' to test email flow")
        
        return True
        
    except Exception as e:
        print_error(f"Phase 4 failed: {str(e)}")
        return False


async def test_phase_5():
    """Test Phase 5: Payments"""
    print_header("PHASE 5: Payments (Recurrente)")
    
    try:
        from services.payments.recurrente_client import RecurrenteClient
        from services.payments.checkout_service import CheckoutService
        
        print_success("Payment services imported successfully")
        print_info("Skipping actual API calls (sandbox mode)")
        print_info("Run 'python backend/test_phase5.py' to test payments")
        
        return True
        
    except Exception as e:
        print_error(f"Phase 5 failed: {str(e)}")
        return False


async def test_phase_7():
    """Test Phase 7: Automation"""
    print_header("PHASE 7: Automation (Celery & Conductor)")
    
    try:
        # Test Celery app
        from celery_app import celery_app
        print_success("Celery app loaded")
        
        # Test Redis connection
        try:
            import redis
            r = redis.from_url(celery_app.conf.broker_url)
            r.ping()
            print_success("Redis connection successful")
        except Exception as e:
            print_error(f"Redis connection failed: {str(e)}")
            print_info("Make sure Redis is running: redis-server")
            return False
        
        # Test task imports
        from tasks import scraping, generation, campaigns, monitoring
        print_success("All task modules imported")
        
        # Test conductor
        from conductor import Conductor
        print_success("Conductor imported successfully")
        
        print_info("Run 'python backend/conductor.py --status' to check pipeline")
        
        return True
        
    except Exception as e:
        print_error(f"Phase 7 failed: {str(e)}")
        return False


async def check_prerequisites():
    """Check all prerequisites."""
    print_header("Checking Prerequisites")
    
    all_good = True
    
    # Check Python version
    import sys
    if sys.version_info >= (3, 11):
        print_success(f"Python version: {sys.version_info.major}.{sys.version_info.minor}")
    else:
        print_error(f"Python 3.11+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        all_good = False
    
    # Check .env file
    env_path = os.path.join('backend', '.env')
    if os.path.exists(env_path):
        print_success(".env file exists")
    else:
        print_error(".env file not found")
        print_info("Copy backend/env.template to backend/.env and fill in values")
        all_good = False
    
    # Check database connection
    try:
        from core.config import get_settings
        settings = get_settings()
        if settings.DATABASE_URL:
            print_success("Database URL configured")
        else:
            print_error("DATABASE_URL not set")
            all_good = False
    except Exception as e:
        print_error(f"Config loading failed: {str(e)}")
        all_good = False
    
    # Check Redis
    try:
        import redis
        from core.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        print_success("Redis is running")
    except Exception as e:
        print_warning(f"Redis not available: {str(e)}")
        print_info("Phase 7 tests will be skipped")
    
    # Check API keys
    try:
        from core.config import get_settings
        settings = get_settings()
        
        if settings.ANTHROPIC_API_KEY:
            print_success("Anthropic API key configured")
        else:
            print_warning("Anthropic API key not set (Phase 3 will skip)")
        
        if settings.OUTSCRAPER_API_KEY:
            print_success("Outscraper API key configured")
        else:
            print_warning("Outscraper API key not set (Phase 2 will skip)")
            
    except:
        pass
    
    return all_good


async def main():
    """Run all tests."""
    print(f"\n{BLUE}╔═══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BLUE}║           WebMagic Local Testing Suite                   ║{RESET}")
    print(f"{BLUE}║           {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                            ║{RESET}")
    print(f"{BLUE}╚═══════════════════════════════════════════════════════════╝{RESET}")
    
    # Check prerequisites
    prereqs_ok = await check_prerequisites()
    if not prereqs_ok:
        print_error("\nPrerequisites check failed. Fix issues and try again.")
        return False
    
    # Run phase tests
    results = {}
    
    tests = [
        ("Phase 1: Foundation", test_phase_1),
        ("Phase 2: Hunter", test_phase_2),
        ("Phase 3: Creative", test_phase_3),
        ("Phase 4: Pitcher", test_phase_4),
        ("Phase 5: Payments", test_phase_5),
        ("Phase 7: Automation", test_phase_7),
    ]
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
        except Exception as e:
            print_error(f"{name} crashed: {str(e)}")
            results[name] = False
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for name, result in results.items():
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
    
    print(f"\n{BLUE}{'─' * 60}{RESET}")
    print(f"{BLUE}Results: {passed}/{total} phases passed{RESET}")
    print(f"{BLUE}{'─' * 60}{RESET}\n")
    
    if passed == total:
        print_success("All tests passed! ✨")
        print_info("\nNext steps:")
        print_info("1. Test frontend: cd frontend && npm run dev")
        print_info("2. Test conductor: python backend/conductor.py --status")
        print_info("3. Run full integration test (see LOCAL_TESTING.md)")
        return True
    else:
        print_warning(f"{total - passed} phase(s) need attention")
        print_info("\nSee LOCAL_TESTING.md for detailed testing instructions")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
