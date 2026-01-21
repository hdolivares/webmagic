"""
Phase 3: Subscription System Tests

Tests subscription activation, billing, cancellation, and reactivation.

Run: python backend/test_phase3.py

Author: WebMagic Team
Date: January 21, 2026
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from core.config import get_settings
from models.site_models import Site, CustomerUser
from services.subscription_service import SubscriptionService
from services.customer_auth_service import CustomerAuthService

settings = get_settings()


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print test header."""
    print()
    print("=" * 70)
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print("=" * 70)


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")


async def run_tests():
    """Run all Phase 3 subscription tests."""
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print_header("PHASE 3: SUBSCRIPTION SYSTEM TESTS")
    print()
    
    test_results = []
    test_customer_id = None
    test_site_id = None
    
    async with AsyncSessionLocal() as session:
        try:
            # TEST 1: Create Test Customer
            print_info("Test 1: Creating test customer...")
            try:
                test_customer = await CustomerAuthService.create_customer_user(
                    db=session,
                    email=f"test_sub_{datetime.now().timestamp()}@example.com",
                    password="TestPass123!",
                    full_name="Subscription Test User"
                )
                test_customer_id = test_customer.id
                print_success(f"Test customer created: {test_customer.email}")
                test_results.append(("Create test customer", True))
            except Exception as e:
                print_error(f"Failed to create test customer: {e}")
                test_results.append(("Create test customer", False))
                return test_results
            
            # TEST 2: Create Test Site
            print_info("Test 2: Creating test site...")
            try:
                test_site = Site(
                    slug=f"test-site-{int(datetime.now().timestamp())}",
                    site_title="Test Site",
                    site_description="Test site for subscription",
                    status="owned",  # Must be owned to activate subscription
                    purchase_amount=Decimal("495.00"),
                    purchased_at=datetime.now()
                )
                session.add(test_site)
                await session.commit()
                await session.refresh(test_site)
                test_site_id = test_site.id
                
                # Link customer to site (customer has site_id, not site has customer_id)
                test_customer.site_id = test_site_id
                await session.commit()
                await session.refresh(test_customer)
                
                print_success(f"Test site created: {test_site.slug}, status: {test_site.status}")
                test_results.append(("Create test site", True))
            except Exception as e:
                print_error(f"Failed to create test site: {e}")
                test_results.append(("Create test site", False))
                return test_results
            
            # TEST 3: Get Subscription Status (Before Activation)
            print_info("Test 3: Getting subscription status (should be none)...")
            try:
                status = await SubscriptionService.get_subscription_status(
                    db=session,
                    site_id=test_site_id
                )
                assert status["status"] == "none", f"Expected 'none', got '{status['status']}'"
                assert not status["is_active"], "Subscription should not be active"
                print_success(f"Subscription status correct: {status['status']}")
                test_results.append(("Get subscription status (none)", True))
            except Exception as e:
                print_error(f"Failed subscription status test: {e}")
                test_results.append(("Get subscription status (none)", False))
            
            # TEST 4: Simulate Subscription Activation
            print_info("Test 4: Simulating subscription activation...")
            try:
                # Simulate webhook data
                subscription_data = {
                    "id": f"sub_test_{int(datetime.now().timestamp())}",
                    "metadata": {
                        "site_id": str(test_site_id),
                        "customer_id": str(test_customer_id)
                    },
                    "status": "active"
                }
                
                activated_site = await SubscriptionService.activate_subscription(
                    db=session,
                    subscription_id=subscription_data["id"],
                    subscription_data=subscription_data
                )
                
                assert activated_site.status == "active", f"Expected status 'active', got '{activated_site.status}'"
                assert activated_site.subscription_status == "active"
                assert activated_site.subscription_id == subscription_data["id"]
                assert activated_site.monthly_amount == Decimal("95.00")
                assert activated_site.next_billing_date is not None
                
                print_success(f"Subscription activated: status={activated_site.status}")
                print_success(f"  Next billing: {activated_site.next_billing_date}")
                print_success(f"  Monthly amount: ${activated_site.monthly_amount}")
                test_results.append(("Activate subscription", True))
            except Exception as e:
                print_error(f"Failed activation test: {e}")
                test_results.append(("Activate subscription", False))
            
            # TEST 5: Get Subscription Status (After Activation)
            print_info("Test 5: Getting subscription status (should be active)...")
            try:
                await session.refresh(test_site)
                status = await SubscriptionService.get_subscription_status(
                    db=session,
                    site_id=test_site_id
                )
                assert status["status"] == "active"
                assert status["is_active"]
                assert not status["is_cancelled"]
                print_success(f"Subscription status correct: active, MRR: ${status['monthly_amount']}")
                test_results.append(("Get subscription status (active)", True))
            except Exception as e:
                print_error(f"Failed status check: {e}")
                test_results.append(("Get subscription status (active)", False))
            
            # TEST 6: Simulate Payment Success
            print_info("Test 6: Simulating successful payment (billing extension)...")
            try:
                old_billing_date = test_site.next_billing_date
                
                payment_data = {
                    "id": f"pay_test_{int(datetime.now().timestamp())}",
                    "subscription_id": test_site.subscription_id
                }
                
                updated_site = await SubscriptionService.handle_payment_success(
                    db=session,
                    subscription_id=test_site.subscription_id,
                    payment_data=payment_data
                )
                
                assert updated_site.status == "active"
                assert updated_site.next_billing_date > old_billing_date
                print_success(f"Payment processed: next billing extended to {updated_site.next_billing_date}")
                test_results.append(("Handle payment success", True))
            except Exception as e:
                print_error(f"Failed payment success test: {e}")
                test_results.append(("Handle payment success", False))
            
            # TEST 7: Simulate Payment Failure
            print_info("Test 7: Simulating payment failure (grace period)...")
            try:
                failure_data = {
                    "id": f"fail_test_{int(datetime.now().timestamp())}",
                    "subscription_id": test_site.subscription_id,
                    "failure_reason": "Insufficient funds"
                }
                
                failed_site = await SubscriptionService.handle_payment_failure(
                    db=session,
                    subscription_id=test_site.subscription_id,
                    failure_data=failure_data
                )
                
                assert failed_site.subscription_status == "past_due"
                assert failed_site.grace_period_ends is not None
                # Use timezone-aware datetime
                now = datetime.now(timezone.utc)
                grace_days = (failed_site.grace_period_ends - now).days
                assert 6 <= grace_days <= 7, f"Grace period should be ~7 days, got {grace_days}"
                print_success(f"Grace period started: ends {failed_site.grace_period_ends}")
                test_results.append(("Handle payment failure", True))
            except Exception as e:
                print_error(f"Failed payment failure test: {e}")
                test_results.append(("Handle payment failure", False))
            
            # TEST 8: Cancel Subscription (Period End)
            print_info("Test 8: Testing subscription cancellation (period end)...")
            try:
                # First, reactivate to test cancellation
                await session.refresh(test_site)
                test_site.subscription_status = "active"
                test_site.status = "active"
                test_site.grace_period_ends = None
                await session.commit()
                
                cancelled_site = await SubscriptionService.cancel_subscription(
                    db=session,
                    site_id=test_site_id,
                    immediate=False,
                    reason="Testing cancellation"
                )
                
                assert cancelled_site.subscription_status == "cancelled"
                assert cancelled_site.subscription_ends_at is not None
                assert cancelled_site.status == "active"  # Still active until period end
                print_success(f"Cancelled at period end: {cancelled_site.subscription_ends_at}")
                test_results.append(("Cancel subscription (period end)", True))
            except Exception as e:
                print_error(f"Failed cancellation test: {e}")
                test_results.append(("Cancel subscription (period end)", False))
            
            # TEST 9: Cancel Subscription (Immediate)
            print_info("Test 9: Testing immediate cancellation...")
            try:
                # Reactivate first
                await session.refresh(test_site)
                test_site.subscription_status = "active"
                test_site.status = "active"
                test_site.subscription_ends_at = None
                await session.commit()
                
                cancelled_site = await SubscriptionService.cancel_subscription(
                    db=session,
                    site_id=test_site_id,
                    immediate=True,
                    reason="Testing immediate cancellation"
                )
                
                assert cancelled_site.subscription_status == "cancelled"
                assert cancelled_site.status == "owned"  # Immediately downgraded
                print_success(f"Immediately cancelled: status={cancelled_site.status}")
                test_results.append(("Cancel subscription (immediate)", True))
            except Exception as e:
                print_error(f"Failed immediate cancellation: {e}")
                test_results.append(("Cancel subscription (immediate)", False))
            
            # CLEANUP: Delete Test Data
            print_info("Cleanup: Deleting test data...")
            try:
                await session.delete(test_site)
                await session.delete(test_customer)
                await session.commit()
                print_success("Test data cleaned up")
            except Exception as e:
                print_error(f"Cleanup error: {e}")
        
        except Exception as e:
            print_error(f"Test suite error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await session.close()
    
    await engine.dispose()
    
    # Print Results
    print()
    print_header("TEST RESULTS")
    print()
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    print()
    print("=" * 70)
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}ALL TESTS PASSED! {passed}/{total} ✅{Colors.END}")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}PASSED: {passed}/{total}{Colors.END}")
    print("=" * 70)
    print()
    
    return test_results


async def main():
    """Main execution."""
    print()
    print("=" * 70)
    print(f"{Colors.BOLD}Phase 3: Subscription System Test Suite{Colors.END}")
    print("=" * 70)
    print()
    
    try:
        results = await run_tests()
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        if passed == total:
            print_success(f"Phase 3 subscription service is working perfectly!")
            return 0
        else:
            print_info(f"Some tests need attention: {passed}/{total} passed")
            return 1
    
    except Exception as e:
        print_error(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
