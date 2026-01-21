"""
Webhook Handlers

Processes webhooks from external services:
- Recurrente (payment processing)

Security:
- Signature verification for all webhooks
- Idempotency handling
- Error recovery

Author: WebMagic Team
Date: January 21, 2026
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json
from typing import Dict, Any

from core.database import get_db
from core.config import get_settings
from services.payments.recurrente_client import RecurrenteClient
from services.site_purchase_service import get_site_purchase_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "/recurrente",
    status_code=status.HTTP_200_OK,
    summary="Recurrente webhook handler",
    description="Process payment events from Recurrente."
)
async def recurrente_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Process Recurrente webhook events.
    
    Handles:
    - payment.succeeded - Purchase completed
    - payment.failed - Purchase failed
    - subscription.activated - Subscription started
    - subscription.cancelled - Subscription cancelled
    - subscription.payment_failed - Recurring payment failed
    
    Security: Verifies webhook signature using HMAC-SHA256.
    """
    # Get raw body for signature verification
    raw_body = await request.body()
    body_str = raw_body.decode('utf-8')
    
    # Get signature from header
    signature = request.headers.get('X-Recurrente-Signature', '')
    
    # Verify signature
    recurrente = RecurrenteClient()
    if not recurrente.verify_webhook_signature(body_str, signature):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Parse webhook data
    try:
        webhook_data = json.loads(body_str)
    except json.JSONDecodeError:
        logger.error("Invalid webhook JSON")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON"
        )
    
    event_type = webhook_data.get('event')
    event_data = webhook_data.get('data', {})
    
    logger.info(f"Received Recurrente webhook: {event_type}")
    
    try:
        # Route to appropriate handler
        if event_type == 'payment.succeeded':
            await handle_payment_succeeded(db, event_data)
        
        elif event_type == 'payment.failed':
            await handle_payment_failed(db, event_data)
        
        elif event_type == 'subscription.activated':
            await handle_subscription_activated(db, event_data)
        
        elif event_type == 'subscription.cancelled':
            await handle_subscription_cancelled(db, event_data)
        
        elif event_type == 'subscription.payment_failed':
            await handle_subscription_payment_failed(db, event_data)
        
        else:
            logger.warning(f"Unhandled webhook event type: {event_type}")
        
        return {
            "status": "success",
            "event": event_type,
            "message": "Webhook processed successfully"
        }
    
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        # Return 200 to prevent Recurrente retries for permanent errors
        # Log error for manual review
        return {
            "status": "error",
            "event": event_type,
            "message": "Error logged for manual review"
        }


async def handle_payment_succeeded(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    Handle successful payment webhook.
    
    Actions:
    1. Extract site info from metadata
    2. Create/update customer user
    3. Update site status to 'owned'
    4. Send welcome email
    5. Log transaction
    """
    try:
        checkout_id = event_data.get('checkout_id')
        payment_id = event_data.get('id')
        
        logger.info(f"Processing payment success: {payment_id}")
        
        # Process purchase
        purchase_service = get_site_purchase_service()
        result = await purchase_service.process_purchase_payment(
            db=db,
            checkout_id=checkout_id,
            payment_data=event_data
        )
        
        # TODO: Send welcome email
        logger.info(
            f"Purchase completed: Site {result['site_slug']} "
            f"by {result['customer_email']}"
        )
        
        # TODO: Trigger post-purchase tasks (Celery)
        # - Send welcome email
        # - Create initial site version if not exists
        # - Log to analytics
    
    except Exception as e:
        logger.error(f"Error processing payment success: {e}", exc_info=True)
        raise


async def handle_payment_failed(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    Handle failed payment webhook.
    
    Actions:
    1. Log payment failure
    2. Notify admin (optional)
    """
    payment_id = event_data.get('id')
    failure_reason = event_data.get('failure_reason', 'Unknown')
    
    logger.warning(
        f"Payment failed: {payment_id} - Reason: {failure_reason}"
    )
    
    # No site status changes for preview sites
    # Customer can retry purchase


async def handle_subscription_activated(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    Handle subscription activation webhook (Phase 3).
    
    Actions:
    1. Update site status to 'active'
    2. Record subscription details
    3. Send activation email
    """
    subscription_id = event_data.get('id')
    
    logger.info(f"Subscription activated: {subscription_id}")
    
    # TODO: Implement in Phase 3
    # This will activate monthly billing and make site live


async def handle_subscription_cancelled(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    Handle subscription cancellation webhook (Phase 3).
    
    Actions:
    1. Update subscription status
    2. Set grace period end date
    3. Send cancellation confirmation
    """
    subscription_id = event_data.get('id')
    
    logger.info(f"Subscription cancelled: {subscription_id}")
    
    # TODO: Implement in Phase 3


async def handle_subscription_payment_failed(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    Handle failed subscription payment webhook (Phase 3).
    
    Actions:
    1. Update subscription status to 'past_due'
    2. Send payment failed email
    3. Start grace period
    """
    subscription_id = event_data.get('id')
    
    logger.warning(f"Subscription payment failed: {subscription_id}")
    
    # TODO: Implement in Phase 3
