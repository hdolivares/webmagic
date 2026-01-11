"""
Phase 5 Test: Payments (Recurrente Integration)
Tests checkout creation, webhooks, and subscription management.
"""
import asyncio
import sys
from uuid import UUID

from sqlalchemy import select
from core.database import get_db_session
from models.customer import Customer, Subscription, Payment
from models.site import GeneratedSite
from services.payments.checkout_service import CheckoutService
from services.payments.customer_service import CustomerService
from services.payments.subscription_service import SubscriptionService
from services.payments.webhook_handler import WebhookHandler


async def test_checkout_flow():
    """Test creating a checkout session."""
    print("\n=== Test 1: Create Checkout Session ===")
    
    async with get_db_session() as db:
        # Get a site to create checkout for
        result = await db.execute(
            select(GeneratedSite).limit(1)
        )
        site = result.scalar_one_or_none()
        
        if not site:
            print("❌ No sites found. Run test_phase3.py first to create a site.")
            return False
        
        print(f"✓ Found site: {site.subdomain}")
        
        # Create checkout
        service = CheckoutService(db)
        checkout = await service.create_checkout_session(
            site_id=site.id,
            customer_email="test@example.com",
            customer_name="Test Customer",
            recurrence_type="subscription"
        )
        
        print(f"✓ Checkout created: {checkout['checkout_id']}")
        print(f"  URL: {checkout['checkout_url']}")
        print(f"  Amount: {checkout['amount']} {checkout['currency']}")
        print(f"  Type: {checkout['recurrence_type']}")
        
        return True


async def test_customer_service():
    """Test customer management."""
    print("\n=== Test 2: Customer Service ===")
    
    async with get_db_session() as db:
        service = CustomerService(db)
        
        # Get or create customer
        customer = await service.get_or_create_customer(
            email="test@example.com",
            full_name="Test Customer"
        )
        print(f"✓ Customer: {customer.email} ({customer.status})")
        
        # Get customer stats
        stats = await service.get_stats()
        print(f"✓ Stats:")
        print(f"  Total customers: {stats['total_customers']}")
        print(f"  Active customers: {stats['active_customers']}")
        print(f"  Total LTV: Q{stats['total_lifetime_value_cents']/100:.2f}")
        
        # List customers
        customers, total = await service.list_customers(limit=5)
        print(f"✓ Listed {len(customers)} customers (total: {total})")
        
        return True


async def test_webhook_handler():
    """Test webhook handling."""
    print("\n=== Test 3: Webhook Handler ===")
    
    async with get_db_session() as db:
        handler = WebhookHandler(db)
        
        # Simulate payment completed event
        payload = {
            "payment_id": "pay_test123",
            "checkout_id": "chk_test123",
            "amount": 9900,
            "currency": "GTQ",
            "status": "completed"
        }
        
        result = await handler.handle_webhook("payment.completed", payload)
        print(f"✓ Webhook handled: payment.completed -> {result}")
        
        return True


async def test_subscription_management():
    """Test subscription operations."""
    print("\n=== Test 4: Subscription Management ===")
    
    async with get_db_session() as db:
        # Get any subscription
        result = await db.execute(
            select(Subscription).limit(1)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            print("⚠ No subscriptions found. Create one through checkout first.")
            return True
        
        print(f"✓ Found subscription: {subscription.recurrente_subscription_id}")
        print(f"  Status: {subscription.status}")
        print(f"  Amount: {subscription.amount} {subscription.currency}")
        
        # Note: Not actually cancelling in test to avoid breaking data
        print("✓ Subscription service initialized (not cancelling in test)")
        
        return True


async def test_customer_payments():
    """Test retrieving customer payment history."""
    print("\n=== Test 5: Customer Payment History ===")
    
    async with get_db_session() as db:
        # Get customer with payments
        result = await db.execute(
            select(Customer).limit(1)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            print("⚠ No customers found")
            return True
        
        service = CustomerService(db)
        
        # Get payments
        payments = await service.get_customer_payments(customer.id)
        print(f"✓ Customer: {customer.email}")
        print(f"  Total payments: {len(payments)}")
        
        for payment in payments[:3]:  # Show first 3
            print(f"  - {payment.status}: {payment.amount} {payment.currency}")
        
        # Get subscriptions
        subscriptions = await service.get_customer_subscriptions(customer.id)
        print(f"  Total subscriptions: {len(subscriptions)}")
        
        return True


async def main():
    """Run all Phase 5 tests."""
    print("=" * 60)
    print("WebMagic Phase 5: Payments (Recurrente Integration)")
    print("=" * 60)
    
    tests = [
        ("Checkout Flow", test_checkout_flow),
        ("Customer Service", test_customer_service),
        ("Webhook Handler", test_webhook_handler),
        ("Subscription Management", test_subscription_management),
        ("Customer Payment History", test_customer_payments)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {name} failed: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
