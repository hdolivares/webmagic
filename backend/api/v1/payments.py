"""
API endpoints for payments, customers, and subscriptions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from api.deps import get_db, get_current_user
from api.schemas.payment import (
    CustomerCreate,
    CustomerOut,
    CustomerListOut,
    CustomerStatsOut,
    SubscriptionOut,
    SubscriptionCancel,
    PaymentOut,
    PaymentListOut,
    CheckoutCreate,
    CheckoutOut,
    WebhookEvent
)
from services.payments.customer_service import CustomerService
from services.payments.subscription_service import SubscriptionService
from services.payments.checkout_service import CheckoutService
from services.payments.webhook_handler import WebhookHandler
from services.payments.recurrente_client import RecurrenteClient
from models.user import AdminUser

router = APIRouter(prefix="/payments", tags=["payments"])


# Checkout endpoints (public for customers)

@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(
    checkout_data: CheckoutCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a checkout session for a site.
    Public endpoint - no authentication required.
    """
    service = CheckoutService(db)
    result = await service.create_checkout_session(
        site_id=checkout_data.site_id,
        customer_email=checkout_data.customer_email,
        customer_name=checkout_data.customer_name,
        recurrence_type=checkout_data.recurrence_type,
        success_url=checkout_data.success_url,
        cancel_url=checkout_data.cancel_url
    )
    return result


@router.get("/checkout/{checkout_id}")
async def get_checkout_status(
    checkout_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get checkout status."""
    service = CheckoutService(db)
    result = await service.get_checkout_status(checkout_id)
    return result


# Webhook endpoint (public, verified by signature)

@router.post("/webhooks/recurrente", status_code=status.HTTP_200_OK)
async def recurrente_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive Recurrente webhook events.
    Public endpoint - signature verification handled internally.
    """
    # Get raw body and signature
    body = await request.body()
    signature = request.headers.get("X-Recurrente-Signature", "")
    
    # Verify signature
    recurrente = RecurrenteClient()
    if not recurrente.verify_webhook_signature(body.decode(), signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse event
    import json
    event_data = json.loads(body)
    event_type = event_data.get("event")
    payload = event_data.get("data", {})
    
    # Handle webhook
    handler = WebhookHandler(db)
    success = await handler.handle_webhook(event_type, payload)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook handling failed"
        )
    
    return {"status": "success"}


# Customer endpoints (admin only)

@router.get("/customers", response_model=CustomerListOut)
async def list_customers(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """List all customers (admin only)."""
    service = CustomerService(db)
    customers, total = await service.list_customers(skip, limit, status)
    
    return CustomerListOut(
        customers=[CustomerOut.model_validate(c) for c in customers],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/customers/stats", response_model=CustomerStatsOut)
async def get_customer_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get customer statistics (admin only)."""
    service = CustomerService(db)
    stats = await service.get_stats()
    
    return CustomerStatsOut(
        total_customers=stats["total_customers"],
        active_customers=stats["active_customers"],
        total_lifetime_value=stats["total_lifetime_value_cents"] / 100.0,
        average_lifetime_value=stats["average_lifetime_value_cents"] / 100.0
    )


@router.get("/customers/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get customer details (admin only)."""
    from uuid import UUID
    service = CustomerService(db)
    customer = await service.get_customer(UUID(customer_id))
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return CustomerOut.model_validate(customer)


@router.get("/customers/{customer_id}/payments", response_model=PaymentListOut)
async def get_customer_payments(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get customer payment history (admin only)."""
    from uuid import UUID
    service = CustomerService(db)
    payments = await service.get_customer_payments(UUID(customer_id))
    
    return PaymentListOut(
        payments=[PaymentOut.model_validate(p) for p in payments],
        total=len(payments)
    )


# Subscription endpoints (admin only)

@router.get("/customers/{customer_id}/subscriptions")
async def get_customer_subscriptions(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get customer subscriptions (admin only)."""
    from uuid import UUID
    service = CustomerService(db)
    subscriptions = await service.get_customer_subscriptions(UUID(customer_id))
    
    return [SubscriptionOut.model_validate(s) for s in subscriptions]


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    cancel_data: SubscriptionCancel,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Cancel a subscription (admin only)."""
    from uuid import UUID
    service = SubscriptionService(db)
    success = await service.cancel_subscription(
        UUID(subscription_id),
        reason=cancel_data.reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    return {"status": "cancelled"}
