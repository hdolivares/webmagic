# WebMagic: Recurrente Payment Integration

## Guatemala-Focused Payment Processing

This document details the integration with Recurrente, a payment platform focused on Guatemala and LATAM markets.

---

## 🏦 Recurrente Overview

### Key Characteristics

| Feature | Value |
|---------|-------|
| **Base URL** | `https://app.recurrente.com/api/` |
| **Currencies** | GTQ (Quetzales), USD |
| **Fee** | 4.5% + Q2.00 per transaction |
| **Settlement** | T+1 (next business day) |
| **Auth Method** | API Key pair in headers |

### Authentication Headers

```http
X-PUBLIC-KEY: your_public_key
X-SECRET-KEY: your_secret_key
Content-Type: application/json
```

### Environments

| Environment | Keys | Behavior |
|-------------|------|----------|
| **TEST** | Test keys from dashboard | "PRUEBA" badge, no real charges, NO webhooks |
| **LIVE** | Live keys from dashboard | Real charges, webhooks fire |

⚠️ **Critical**: Test environment does NOT fire webhooks. You must mock them during development.

---

## 💰 Pricing Strategy

### WebMagic Pricing Model

| Item | Price (GTQ) | Price (USD) | Recurrente Charge Type |
|------|-------------|-------------|------------------------|
| Website Setup (one-time) | Q4,000 - Q6,500 | $500 - $800 | `one_time` |
| Monthly Maintenance | Q800/mo | $99/mo | `recurring` |

### Fee Calculation

For a Q5,000 (≈$600) website sale:
- Recurrente fee: 4.5% + Q2 = Q227
- You receive: Q4,773 (≈$572)

---

## 🔧 Implementation

### Service Structure

```
backend/services/payments/
├── __init__.py
├── client.py           # Base API client
├── checkout.py         # Checkout session creation
├── subscriptions.py    # Subscription management
├── webhooks.py         # Webhook handlers
└── refunds.py          # Refund processing
```

### Base Client (`client.py`)

```python
"""
Recurrente API client wrapper.
"""
import httpx
from typing import Dict, Any, Optional
from ...core.config import get_settings

class RecurrenteClient:
    """
    Low-level API client for Recurrente.
    
    Usage:
        client = RecurrenteClient()
        response = await client.post("/checkouts/", data={...})
    """
    
    def __init__(self, use_test_keys: bool = False):
        settings = get_settings()
        self.base_url = settings.RECURRENTE_BASE_URL + "/api"
        
        # Allow override for testing
        if use_test_keys:
            self.public_key = settings.RECURRENTE_TEST_PUBLIC_KEY
            self.secret_key = settings.RECURRENTE_TEST_SECRET_KEY
        else:
            self.public_key = settings.RECURRENTE_PUBLIC_KEY
            self.secret_key = settings.RECURRENTE_SECRET_KEY
    
    def _headers(self) -> Dict[str, str]:
        return {
            "X-PUBLIC-KEY": self.public_key,
            "X-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }
    
    async def get(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a GET request."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                headers=self._headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def post(self, endpoint: str, data: Dict) -> Dict:
        """Make a POST request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                headers=self._headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def patch(self, endpoint: str, data: Dict) -> Dict:
        """Make a PATCH request."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}{endpoint}",
                headers=self._headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def delete(self, endpoint: str) -> Dict:
        """Make a DELETE request."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}{endpoint}",
                headers=self._headers()
            )
            response.raise_for_status()
            return response.json()
    
    async def test_connection(self) -> bool:
        """Test API connection."""
        try:
            result = await self.get("/test")
            return "message" in result
        except Exception:
            return False
```

### Checkout Service (`checkout.py`)

```python
"""
Checkout session creation for WebMagic sales.
"""
from typing import Optional
from dataclasses import dataclass
from .client import RecurrenteClient

@dataclass
class CheckoutConfig:
    """Configuration for a checkout session."""
    business_name: str
    site_id: str
    
    # Pricing
    setup_amount_cents: int = 500000  # Q5,000 or $500
    monthly_amount_cents: int = 9900  # Q99 or $99
    currency: str = "GTQ"
    
    # URLs
    success_url: str = ""
    cancel_url: str = ""
    
    # Customer info (if known)
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None

class CheckoutService:
    """
    Creates checkout sessions for website purchases.
    
    WebMagic uses a hybrid model:
    1. One-time payment for website setup
    2. Recurring subscription for maintenance
    
    We create a checkout with BOTH items.
    """
    
    def __init__(self):
        self.client = RecurrenteClient()
    
    async def create_website_checkout(
        self,
        config: CheckoutConfig
    ) -> dict:
        """
        Create a checkout session for a website purchase.
        
        This creates a checkout with:
        - One-time setup fee
        - Monthly recurring subscription
        
        Returns:
            {"id": "ch_xxx", "checkout_url": "https://..."}
        """
        payload = {
            "items": [
                # One-time setup fee
                {
                    "name": f"Website Design for {config.business_name}",
                    "currency": config.currency,
                    "amount_in_cents": config.setup_amount_cents,
                    "quantity": 1,
                    "image_url": None  # Could add screenshot here
                },
                # Monthly subscription
                {
                    "name": f"Monthly Maintenance - {config.business_name}",
                    "currency": config.currency,
                    "amount_in_cents": config.monthly_amount_cents,
                    "charge_type": "recurring",
                    "billing_interval": "month",
                    "billing_interval_count": 1,
                    "quantity": 1
                }
            ],
            "success_url": config.success_url or self._default_success_url(config.site_id),
            "cancel_url": config.cancel_url or self._default_cancel_url(config.site_id),
            "metadata": {
                "site_id": config.site_id,
                "business_name": config.business_name,
                "source": "webmagic_autopilot"
            }
        }
        
        # Pre-fill customer info if available
        if config.customer_email:
            # Create or get user first
            user = await self._ensure_user(
                email=config.customer_email,
                name=config.customer_name
            )
            if user:
                payload["user_id"] = user["id"]
        
        response = await self.client.post("/checkouts/", payload)
        
        return {
            "checkout_id": response["id"],
            "checkout_url": response["checkout_url"]
        }
    
    async def create_setup_only_checkout(
        self,
        config: CheckoutConfig
    ) -> dict:
        """
        Create a checkout for ONLY the setup fee.
        Use when customer doesn't want subscription.
        """
        payload = {
            "items": [
                {
                    "name": f"Website Design for {config.business_name}",
                    "currency": config.currency,
                    "amount_in_cents": config.setup_amount_cents,
                    "quantity": 1
                }
            ],
            "success_url": config.success_url,
            "cancel_url": config.cancel_url,
            "metadata": {
                "site_id": config.site_id,
                "type": "setup_only"
            }
        }
        
        response = await self.client.post("/checkouts/", payload)
        return {
            "checkout_id": response["id"],
            "checkout_url": response["checkout_url"]
        }
    
    async def get_checkout_status(self, checkout_id: str) -> dict:
        """
        Get the current status of a checkout.
        
        Returns:
            {
                "id": "ch_xxx",
                "status": "unpaid" | "paid",
                "payment": {...} if paid,
                ...
            }
        """
        return await self.client.get(f"/checkouts/{checkout_id}")
    
    async def expire_checkout(self, checkout_id: str) -> dict:
        """
        Expire a checkout so it can no longer be used.
        """
        # Set expires_at to past date
        return await self.client.patch(f"/checkouts/{checkout_id}", {
            "expires_at": "2020-01-01T00:00:00Z"
        })
    
    async def _ensure_user(
        self,
        email: str,
        name: Optional[str] = None
    ) -> Optional[dict]:
        """Create or get a Recurrente user."""
        try:
            response = await self.client.post("/users/", {
                "email": email,
                "full_name": name or ""
            })
            return response
        except Exception:
            # User might already exist
            return None
    
    def _default_success_url(self, site_id: str) -> str:
        return f"https://webmagic.com/welcome?site={site_id}"
    
    def _default_cancel_url(self, site_id: str) -> str:
        return f"https://webmagic.com/preview/{site_id}"
```

### Subscription Service (`subscriptions.py`)

```python
"""
Subscription management for recurring billing.
"""
from typing import List, Optional
from .client import RecurrenteClient

class SubscriptionService:
    """
    Manages monthly maintenance subscriptions.
    """
    
    def __init__(self):
        self.client = RecurrenteClient()
    
    async def get_subscription(self, subscription_id: str) -> dict:
        """Get subscription details."""
        return await self.client.get(f"/subscriptions/{subscription_id}")
    
    async def list_subscriptions(
        self,
        page: int = 1,
        status: Optional[str] = None
    ) -> List[dict]:
        """
        List all subscriptions.
        
        Status values: active, past_due, paused, cancelled
        """
        params = {"page": page}
        if status:
            params["status"] = status
        
        return await self.client.get("/subscriptions", params=params)
    
    async def cancel_subscription(self, subscription_id: str) -> dict:
        """
        Cancel a subscription.
        
        Note: This stops future charges but doesn't refund past payments.
        """
        return await self.client.delete(f"/subscriptions/{subscription_id}")
    
    async def pause_subscription(self, subscription_id: str) -> dict:
        """
        Pause a subscription.
        
        Note: Recurrente API may not support this directly.
        Check documentation for actual implementation.
        """
        # This might need to be done via support/dashboard
        raise NotImplementedError("Pause not directly supported via API")
    
    async def get_subscription_status(self, subscription_id: str) -> str:
        """
        Get just the status of a subscription.
        
        Returns: active, past_due, paused, cancelled, unable_to_start
        """
        sub = await self.get_subscription(subscription_id)
        return sub.get("status", "unknown")
```

### Webhook Handler (`webhooks.py`)

```python
"""
Recurrente webhook handlers.

IMPORTANT: Webhooks do NOT fire in TEST mode!
You must test with LIVE keys or mock the payloads.
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum

class RecurrenteEvent(str, Enum):
    """Webhook event types from Recurrente."""
    PAYMENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_FAILED = "payment_intent.failed"
    SUBSCRIPTION_CREATED = "subscription.create"
    SUBSCRIPTION_PAST_DUE = "subscription.past_due"
    SUBSCRIPTION_PAUSED = "subscription.paused"
    SUBSCRIPTION_CANCELLED = "subscription.cancel"
    BANK_TRANSFER_PENDING = "bank_transfer_intent.pending"
    BANK_TRANSFER_SUCCEEDED = "bank_transfer_intent.succeeded"
    BANK_TRANSFER_FAILED = "bank_transfer_intent.failed"

class WebhookHandler:
    """
    Handles incoming Recurrente webhooks.
    
    Flow:
    1. Receive webhook
    2. Validate (Recurrente doesn't use signatures, so validate via API call)
    3. Route to appropriate handler
    4. Update database
    5. Trigger follow-up actions
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def handle(self, payload: Dict[str, Any]) -> Dict:
        """
        Main entry point for webhook processing.
        
        Args:
            payload: Raw webhook payload from Recurrente
            
        Returns:
            {"status": "processed", "action": "..."}
        """
        event_type = payload.get("event_type")
        
        if not event_type:
            raise HTTPException(400, "Missing event_type")
        
        # Route to handler
        handlers = {
            RecurrenteEvent.PAYMENT_SUCCEEDED: self._handle_payment_success,
            RecurrenteEvent.PAYMENT_FAILED: self._handle_payment_failed,
            RecurrenteEvent.SUBSCRIPTION_CREATED: self._handle_subscription_created,
            RecurrenteEvent.SUBSCRIPTION_PAST_DUE: self._handle_subscription_past_due,
            RecurrenteEvent.SUBSCRIPTION_CANCELLED: self._handle_subscription_cancelled,
            RecurrenteEvent.BANK_TRANSFER_PENDING: self._handle_bank_pending,
            RecurrenteEvent.BANK_TRANSFER_SUCCEEDED: self._handle_bank_success,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return await handler(payload)
        
        # Unknown event type - log but don't fail
        return {"status": "ignored", "event_type": event_type}
    
    async def _handle_payment_success(self, payload: Dict) -> Dict:
        """
        Handle successful payment.
        
        This is the main conversion event!
        
        Actions:
        1. Update business status to 'purchased'
        2. Create customer record
        3. Deploy site to production
        4. Send welcome email
        """
        checkout = payload.get("checkout", {})
        checkout_id = checkout.get("id")
        metadata = checkout.get("metadata", {})
        
        site_id = metadata.get("site_id")
        if not site_id:
            return {"status": "error", "reason": "No site_id in metadata"}
        
        customer_data = payload.get("customer", {})
        payment_data = payload.get("payment", {})
        
        # 1. Load the site and business
        from ...models.site import GeneratedSite
        from ...models.business import Business
        from ...models.customer import Customer
        from ...models.payment import Payment
        
        site = await self.db.get(GeneratedSite, site_id)
        if not site:
            return {"status": "error", "reason": "Site not found"}
        
        business = await self.db.get(Business, site.business_id)
        
        # 2. Create customer record
        customer = Customer(
            business_id=business.id,
            site_id=site.id,
            recurrente_user_id=customer_data.get("id"),
            email=customer_data.get("email"),
            full_name=customer_data.get("full_name"),
            status="active"
        )
        self.db.add(customer)
        
        # 3. Record payment
        payment = Payment(
            customer_id=customer.id,
            recurrente_payment_id=payload.get("id"),
            recurrente_checkout_id=checkout_id,
            amount_cents=payload.get("amount_in_cents", 0),
            currency=payload.get("currency", "GTQ"),
            fee_cents=payload.get("fee", 0),
            payment_type="one_time",
            status="succeeded",
            payment_method=checkout.get("payment_method", {}).get("type"),
            card_last4=checkout.get("payment_method", {}).get("card", {}).get("last4")
        )
        self.db.add(payment)
        
        # 4. Update statuses
        business.contact_status = "purchased"
        site.status = "sold"
        site.sold_at = func.now()
        
        await self.db.commit()
        
        # 5. Trigger async tasks
        from ...tasks.payment_tasks import post_purchase_workflow
        post_purchase_workflow.delay(str(customer.id), str(site.id))
        
        return {
            "status": "processed",
            "action": "customer_created",
            "customer_id": str(customer.id)
        }
    
    async def _handle_payment_failed(self, payload: Dict) -> Dict:
        """Handle failed payment attempt."""
        checkout_id = payload.get("checkout", {}).get("id")
        failure_reason = payload.get("failure_reason", "Unknown")
        
        # Log for debugging
        from ...utils.logger import logger
        logger.warning(f"Payment failed for checkout {checkout_id}: {failure_reason}")
        
        return {"status": "processed", "action": "logged_failure"}
    
    async def _handle_subscription_created(self, payload: Dict) -> Dict:
        """Handle new subscription creation."""
        subscription_id = payload.get("id")
        customer_id = payload.get("customer_id")
        
        from ...models.subscription import Subscription
        
        subscription = Subscription(
            recurrente_subscription_id=subscription_id,
            # ... other fields from payload
            status="active"
        )
        self.db.add(subscription)
        await self.db.commit()
        
        return {"status": "processed", "action": "subscription_created"}
    
    async def _handle_subscription_past_due(self, payload: Dict) -> Dict:
        """
        Handle subscription payment failure.
        
        Recurrente retries 3 times over 5 days before cancelling.
        We should:
        1. Update status
        2. Send reminder email to customer
        """
        subscription_id = payload.get("id")
        
        from ...models.subscription import Subscription
        
        query = select(Subscription).where(
            Subscription.recurrente_subscription_id == subscription_id
        )
        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.status = "past_due"
            await self.db.commit()
            
            # Send reminder email
            from ...tasks.pitcher_tasks import send_payment_reminder
            send_payment_reminder.delay(str(subscription.customer_id))
        
        return {"status": "processed", "action": "marked_past_due"}
    
    async def _handle_subscription_cancelled(self, payload: Dict) -> Dict:
        """Handle subscription cancellation."""
        subscription_id = payload.get("id")
        
        from ...models.subscription import Subscription
        
        query = select(Subscription).where(
            Subscription.recurrente_subscription_id == subscription_id
        )
        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            subscription.status = "cancelled"
            subscription.cancelled_at = func.now()
            
            # Update customer status
            customer = await self.db.get(Customer, subscription.customer_id)
            if customer:
                customer.status = "churned"
            
            await self.db.commit()
        
        return {"status": "processed", "action": "subscription_cancelled"}
    
    async def _handle_bank_pending(self, payload: Dict) -> Dict:
        """Handle pending bank transfer."""
        # Bank transfers can take up to 24h
        checkout_id = payload.get("checkout", {}).get("id")
        
        # Update checkout status in our DB
        # Don't mark as sold yet - wait for succeeded event
        
        return {"status": "processed", "action": "awaiting_bank_transfer"}
    
    async def _handle_bank_success(self, payload: Dict) -> Dict:
        """Handle successful bank transfer."""
        # Same as card payment success
        return await self._handle_payment_success(payload)
```

### API Endpoint (`api/v1/payments.py`)

```python
"""
Payment-related API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.database import get_db
from ...services.payments.checkout import CheckoutService, CheckoutConfig
from ...services.payments.webhooks import WebhookHandler

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/create-checkout/{site_id}")
async def create_checkout(
    site_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a checkout session for a site.
    Called when user clicks "Claim this site" button.
    """
    from ...models.site import GeneratedSite
    from ...models.business import Business
    
    # Load site and business
    site = await db.get(GeneratedSite, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    
    business = await db.get(Business, site.business_id)
    
    # Create checkout
    service = CheckoutService()
    config = CheckoutConfig(
        business_name=business.name,
        site_id=site_id,
        customer_email=business.email,
        success_url=f"https://webmagic.com/welcome/{site_id}",
        cancel_url=f"https://{site.subdomain}.webmagic.com"
    )
    
    result = await service.create_website_checkout(config)
    
    return {
        "checkout_url": result["checkout_url"],
        "checkout_id": result["checkout_id"]
    }

@router.post("/webhook")
async def handle_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive webhooks from Recurrente.
    
    Note: Recurrente does not sign webhooks.
    We validate by checking the payload structure.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")
    
    # Basic validation
    if "event_type" not in payload:
        raise HTTPException(400, "Missing event_type")
    
    # Process
    handler = WebhookHandler(db)
    result = await handler.handle(payload)
    
    return result

@router.get("/checkout/{checkout_id}/status")
async def get_checkout_status(
    checkout_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Poll checkout status.
    Use this for client-side polling if webhooks are delayed.
    """
    service = CheckoutService()
    status = await service.get_checkout_status(checkout_id)
    
    return {
        "checkout_id": checkout_id,
        "status": status.get("status"),
        "paid": status.get("status") == "paid"
    }
```

### Refund Service (`refunds.py`)

```python
"""
Refund processing.

Important: Same-day refunds get 100% back including commission!
"""
from .client import RecurrenteClient

class RefundService:
    """Handle refunds through Recurrente."""
    
    def __init__(self):
        self.client = RecurrenteClient()
    
    async def create_refund(self, payment_intent_id: str) -> dict:
        """
        Create a full refund for a payment.
        
        IMPORTANT: If processed same day as payment,
        customer gets 100% back AND we get commission back.
        
        Args:
            payment_intent_id: The payment ID (pa_xxx format)
            
        Returns:
            Refund details
        """
        payload = {
            "payment_intent_id": payment_intent_id
        }
        
        return await self.client.post("/refunds/", payload)
    
    async def get_refund(self, refund_id: str) -> dict:
        """Get refund status."""
        return await self.client.get(f"/refunds/{refund_id}")
```

---

## 🧪 Testing Strategy

### Mock Webhook Server

Since TEST mode doesn't fire webhooks, create a mock:

```python
# scripts/mock_webhook.py
"""
Mock Recurrente webhook for local testing.
"""
import httpx
import asyncio

WEBHOOK_URL = "http://localhost:8000/api/v1/payments/webhook"

SAMPLE_PAYMENT_SUCCESS = {
    "id": "pa_test123",
    "event_type": "payment_intent.succeeded",
    "api_version": "2024-04-24",
    "checkout": {
        "id": "ch_test123",
        "status": "paid",
        "metadata": {
            "site_id": "your-test-site-id"
        },
        "payment_method": {
            "type": "card",
            "card": {"last4": "4242", "network": "visa"}
        }
    },
    "customer": {
        "id": "us_test123",
        "email": "test@example.com",
        "full_name": "Test Customer"
    },
    "amount_in_cents": 500000,
    "currency": "GTQ",
    "fee": 22700
}

async def send_mock_webhook():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            WEBHOOK_URL,
            json=SAMPLE_PAYMENT_SUCCESS
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

if __name__ == "__main__":
    asyncio.run(send_mock_webhook())
```

### Test Card

For TEST environment:
- **Card Number**: `4242 4242 4242 4242`
- **Expiry**: Any future date
- **CVC**: Any 3 digits

---

## 📊 Embedded Checkout (Future Enhancement)

Recurrente offers an embedded checkout iframe. Could be used for a smoother UX:

```javascript
import RecurrenteCheckout from 'recurrente-checkout';

RecurrenteCheckout.load({
  url: "https://app.recurrente.com/checkout-session/ch_xxx",
  onSuccess: function(paymentData) {
    console.log('Payment successful:', paymentData);
    window.location.href = '/welcome';
  },
  onFailure: function(error) {
    console.log('Payment failed:', error);
  }
});
```

This would allow the checkout to happen in-page rather than redirecting.

---

## ✅ Checklist

- [ ] Store API keys in environment variables
- [ ] Set up webhook endpoint in Recurrente dashboard
- [ ] Test with TEST keys first
- [ ] Create mock webhook script for local development
- [ ] Handle all webhook event types
- [ ] Implement idempotency (don't process same webhook twice)
- [ ] Set up monitoring for failed payments
- [ ] Document same-day refund policy for support team
