"""
Phase 2 Services Test Suite

Tests all Phase 2 functionality:
- CustomerAuthService
- SitePurchaseService
- Database models
- Site creation and purchase flow

Run: python backend/test_phase2_services.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import get_settings
from models.site_models import Site, CustomerUser, SiteVersion
from services.customer_auth_service import CustomerAuthService
from services.site_purchase_service import get_site_purchase_service

settings = get_settings()


class TestResult:
    """Test result container."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_pass(self, name: str):
        """Record a passing test."""
        self.passed += 1
        self.tests.append((name, True, None))
        print(f"  ✅ {name}")
    
    def add_fail(self, name: str, error: str):
        """Record a failing test."""
        self.failed += 1
        self.tests.append((name, False, error))
        print(f"  ❌ {name}: {error}")
    
    def summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print()
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Total:  {total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} {'❌' if self.failed > 0 else ''}")
        print()
        
        if self.failed > 0:
            print("Failed Tests:")
            for name, passed, error in self.tests:
                if not passed:
                    print(f"  - {name}: {error}")
        
        return self.failed == 0


async def test_database_connection():
    """Test 1: Database connection."""
    print("\n📋 Test 1: Database Connection")
    result = TestResult()
    
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.begin() as conn:
            await conn.execute(select(1))
        await engine.dispose()
        result.add_pass("Database connection successful")
    except Exception as e:
        result.add_fail("Database connection", str(e))
    
    return result


async def test_tables_exist():
    """Test 2: Phase 2 tables exist."""
    print("\n📋 Test 2: Phase 2 Tables")
    result = TestResult()
    
    engine = create_async_engine(settings.DATABASE_URL)
    
    tables = [
        "sites",
        "customer_users",
        "site_versions",
        "edit_requests",
        "domain_verification_records"
    ]
    
    try:
        async with engine.begin() as conn:
            for table in tables:
                from sqlalchemy import text
                query = text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """)
                exists = await conn.execute(query)
                if exists.scalar():
                    result.add_pass(f"Table '{table}' exists")
                else:
                    result.add_fail(f"Table '{table}'", "Table does not exist")
    except Exception as e:
        result.add_fail("Table check", str(e))
    finally:
        await engine.dispose()
    
    return result


async def test_customer_auth_service():
    """Test 3: Customer authentication service."""
    print("\n📋 Test 3: Customer Authentication Service")
    result = TestResult()
    
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    test_email = "test_phase2@webmagic.com"
    test_password = "SecurePassword123!"
    
    try:
        async with AsyncSessionLocal() as session:
            # Test 3.1: Password hashing
            try:
                hashed = CustomerAuthService.hash_password(test_password)
                if len(hashed) > 50:  # Bcrypt hashes are ~60 chars
                    result.add_pass("Password hashing works")
                else:
                    result.add_fail("Password hashing", "Hash too short")
            except Exception as e:
                result.add_fail("Password hashing", str(e))
            
            # Test 3.2: Password verification
            try:
                is_valid = CustomerAuthService.verify_password(test_password, hashed)
                if is_valid:
                    result.add_pass("Password verification works")
                else:
                    result.add_fail("Password verification", "Valid password not verified")
            except Exception as e:
                result.add_fail("Password verification", str(e))
            
            # Test 3.3: Token generation
            try:
                token = CustomerAuthService.generate_token()
                if len(token) > 30:
                    result.add_pass("Token generation works")
                else:
                    result.add_fail("Token generation", "Token too short")
            except Exception as e:
                result.add_fail("Token generation", str(e))
            
            # Clean up existing test user
            existing = await session.execute(
                select(CustomerUser).where(CustomerUser.email == test_email)
            )
            existing_user = existing.scalar_one_or_none()
            if existing_user:
                await session.delete(existing_user)
                await session.commit()
            
            # Test 3.4: Create customer user
            try:
                user = await CustomerAuthService.create_customer_user(
                    db=session,
                    email=test_email,
                    password=test_password,
                    full_name="Test User"
                )
                if user and user.email == test_email:
                    result.add_pass("Customer user creation works")
                else:
                    result.add_fail("Customer user creation", "User not created properly")
            except Exception as e:
                result.add_fail("Customer user creation", str(e))
            
            # Test 3.5: Authenticate customer
            try:
                auth_user, verified = await CustomerAuthService.authenticate_customer(
                    db=session,
                    email=test_email,
                    password=test_password
                )
                if auth_user and auth_user.email == test_email:
                    result.add_pass("Customer authentication works")
                else:
                    result.add_fail("Customer authentication", "Authentication failed")
            except Exception as e:
                result.add_fail("Customer authentication", str(e))
            
            # Test 3.6: Get customer by email
            try:
                found_user = await CustomerAuthService.get_customer_by_email(
                    db=session,
                    email=test_email
                )
                if found_user and found_user.email == test_email:
                    result.add_pass("Get customer by email works")
                else:
                    result.add_fail("Get customer by email", "User not found")
            except Exception as e:
                result.add_fail("Get customer by email", str(e))
            
            # Cleanup
            if user:
                await session.delete(user)
                await session.commit()
    
    except Exception as e:
        result.add_fail("Customer auth service setup", str(e))
    finally:
        await engine.dispose()
    
    return result


async def test_site_purchase_service():
    """Test 4: Site purchase service."""
    print("\n📋 Test 4: Site Purchase Service")
    result = TestResult()
    
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    test_slug = "test-site-phase2"
    test_email = "test_buyer@webmagic.com"
    
    try:
        async with AsyncSessionLocal() as session:
            purchase_service = get_site_purchase_service()
            
            # Clean up existing test data
            existing_site = await session.execute(
                select(Site).where(Site.slug == test_slug)
            )
            site_to_delete = existing_site.scalar_one_or_none()
            if site_to_delete:
                await session.delete(site_to_delete)
                await session.commit()
            
            existing_user = await session.execute(
                select(CustomerUser).where(CustomerUser.email == test_email)
            )
            user_to_delete = existing_user.scalar_one_or_none()
            if user_to_delete:
                await session.delete(user_to_delete)
                await session.commit()
            
            # Test 4.1: Create site record
            try:
                site = await purchase_service.create_site_record(
                    db=session,
                    slug=test_slug,
                    site_title="Test Site",
                    site_description="A test site for Phase 2",
                    html_content="<h1>Test Site</h1>"
                )
                if site and site.slug == test_slug and site.status == "preview":
                    result.add_pass("Site record creation works")
                else:
                    result.add_fail("Site record creation", "Site not created properly")
            except Exception as e:
                result.add_fail("Site record creation", str(e))
                site = None
            
            # Test 4.2: Get site by slug
            try:
                found_site = await purchase_service.get_site_by_slug(
                    db=session,
                    slug=test_slug
                )
                if found_site and found_site.slug == test_slug:
                    result.add_pass("Get site by slug works")
                else:
                    result.add_fail("Get site by slug", "Site not found")
            except Exception as e:
                result.add_fail("Get site by slug", str(e))
            
            # Test 4.3: Site has initial version
            try:
                if site and site.current_version_id:
                    version_result = await session.execute(
                        select(SiteVersion).where(SiteVersion.id == site.current_version_id)
                    )
                    version = version_result.scalar_one_or_none()
                    if version and version.is_current:
                        result.add_pass("Site version creation works")
                    else:
                        result.add_fail("Site version creation", "Version not created")
                else:
                    result.add_fail("Site version creation", "No current_version_id")
            except Exception as e:
                result.add_fail("Site version creation", str(e))
            
            # Test 4.4: Site status management
            try:
                if site:
                    if site.is_preview and not site.is_owned:
                        result.add_pass("Site status properties work")
                    else:
                        result.add_fail("Site status properties", "Status check failed")
            except Exception as e:
                result.add_fail("Site status properties", str(e))
            
            # Cleanup
            if site:
                await session.delete(site)
                await session.commit()
    
    except Exception as e:
        result.add_fail("Site purchase service setup", str(e))
    finally:
        await engine.dispose()
    
    return result


async def test_site_service_integration():
    """Test 5: Site service integration."""
    print("\n📋 Test 5: Site Service Integration")
    result = TestResult()
    
    try:
        from services.site_service import get_site_service
        site_service = get_site_service()
        
        # Test 5.1: URL generation
        try:
            url = site_service.generate_site_url("test-site")
            expected = f"{settings.SITES_BASE_URL}/test-site"
            if url == expected:
                result.add_pass("URL generation works")
            else:
                result.add_fail("URL generation", f"Expected {expected}, got {url}")
        except Exception as e:
            result.add_fail("URL generation", str(e))
        
        # Test 5.2: Slug validation
        try:
            valid_slugs = ["test-site", "my-business-123", "abc"]
            invalid_slugs = ["Test-Site", "my_business", "ab", "-test", "test-"]
            
            all_valid = all(site_service.validate_slug(s) for s in valid_slugs)
            all_invalid = all(not site_service.validate_slug(s) for s in invalid_slugs)
            
            if all_valid and all_invalid:
                result.add_pass("Slug validation works")
            else:
                result.add_fail("Slug validation", "Validation logic incorrect")
        except Exception as e:
            result.add_fail("Slug validation", str(e))
        
        # Test 5.3: Path generation
        try:
            path = site_service.get_site_path("test-site")
            if str(path).endswith("test-site"):
                result.add_pass("Site path generation works")
            else:
                result.add_fail("Site path generation", f"Path incorrect: {path}")
        except Exception as e:
            result.add_fail("Site path generation", str(e))
    
    except Exception as e:
        result.add_fail("Site service integration", str(e))
    
    return result


async def main():
    """Run all tests."""
    print("=" * 70)
    print("PHASE 2 SERVICES TEST SUITE")
    print("=" * 70)
    
    all_results = []
    
    # Run tests
    all_results.append(await test_database_connection())
    all_results.append(await test_tables_exist())
    all_results.append(await test_customer_auth_service())
    all_results.append(await test_site_purchase_service())
    all_results.append(await test_site_service_integration())
    
    # Combined summary
    print()
    print("=" * 70)
    print("OVERALL TEST RESULTS")
    print("=" * 70)
    
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed:      {total_passed} ✅")
    print(f"Failed:      {total_failed} {'❌' if total_failed > 0 else '✅'}")
    print()
    
    if total_failed == 0:
        print("🎉 ALL TESTS PASSED! Phase 2 services are working correctly.")
        print()
        print("✅ Ready to build:")
        print("   - JWT authentication")
        print("   - API endpoints")
        print("   - Webhook handlers")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
