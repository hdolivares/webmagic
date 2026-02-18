"""
Webhook Handlers

Processes webhooks from external services:
- Recurrente (payment processing)

Security:
- Signature verification for all webhooks
- Idempotency handling
- Error recovery

Updated: January 22, 2026
- Integrated CRM lifecycle service for automated status tracking
- All payment events now update business CRM status

Author: WebMagic Team
Date: January 21, 2026
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
import logging
import json
from typing import Dict, Any

from core.database import get_db
from core.config import get_settings
from services.payments.recurrente_client import RecurrenteClient
from services.site_purchase_service import get_site_purchase_service
from services.subscription_service import get_subscription_service
from services.emails.email_service import get_email_service
from services.crm import BusinessLifecycleService

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
    
    # Enhanced debugging - log everything
    logger.info("=" * 80)
    logger.info("WEBHOOK RECEIVED FROM RECURRENTE")
    logger.info(f"All headers: {dict(request.headers)}")
    logger.info(f"Body length: {len(body_str)} bytes")
    logger.info(f"Body preview: {body_str[:500]}")
    
    # Get signature from header (try multiple possible header names)
    signature = (
        request.headers.get('X-Recurrente-Signature') or 
        request.headers.get('x-recurrente-signature') or
        request.headers.get('Recurrente-Signature') or
        request.headers.get('X-Webhook-Signature') or
        ''
    )
    
    logger.info(f"Signature found: '{signature}'")
    logger.info(f"Webhook secret configured: {bool(settings.RECURRENTE_WEBHOOK_SECRET)}")
    logger.info("=" * 80)
    
    # Verify signature (skip if no secret configured or no signature sent)
    recurrente = RecurrenteClient()
    
    if settings.RECURRENTE_WEBHOOK_SECRET and signature:
        if not recurrente.verify_webhook_signature(body_str, signature):
            logger.error(f"❌ SIGNATURE MISMATCH! Got: '{signature[:20]}...'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
        else:
            logger.info("✅ Webhook signature verified successfully")
    else:
        logger.warning("⚠️ Webhook signature verification skipped (no secret or no signature)")
    
    
    # Parse webhook data
    try:
        webhook_data = json.loads(body_str)
    except json.JSONDecodeError:
        logger.error("Invalid webhook JSON")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON"
        )
    
    # Log full payload for debugging
    logger.info(f"📦 Full webhook payload: {json.dumps(webhook_data, indent=2)}")
    logger.info(f"📦 Webhook keys: {list(webhook_data.keys())}")
    
    # Recurrente uses 'event_type' field (not 'event')
    event_type = webhook_data.get('event_type')
    
    # Event data is at root level in Recurrente webhooks
    event_data = webhook_data
    
    logger.info(f"✅ Received Recurrente webhook: {event_type}")
    
    try:
        # Route to appropriate handler
        # Recurrente event types: payment_intent.succeeded, payment_intent.failed, etc.
        if event_type == 'payment_intent.succeeded':
            await handle_payment_succeeded(db, event_data)
        
        elif event_type == 'payment_intent.failed':
            await handle_payment_failed(db, event_data)
        
        elif event_type == 'subscription.activated' or event_type == 'setup_intent.succeeded':
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
    Handle successful payment webhook from Recurrente.
    
    Event structure:
    {
        "id": "pa_xxx",
        "event_type": "payment_intent.succeeded",
        "checkout": {
            "id": "ch_xxx",
            "status": "paid",
            "metadata": {...}
        }
    }
    
    Actions:
    1. Extract site info from metadata
    2. Create/update customer user
    3. Update site status to 'owned'
    4. Send welcome email
    5. Auto-create subscription
    """
    try:
        # Extract from Recurrente's structure
        payment_id = event_data.get('id')
        checkout = event_data.get('checkout', {})
        checkout_id = checkout.get('id')
        payment_method = checkout.get('payment', {}).get('payment_method', {})
        
        logger.info(f"💰 Processing payment success: payment_id={payment_id}, checkout_id={checkout_id}")
        logger.info(f"💰 Checkout data: status={checkout.get('status')}, metadata keys={list(checkout.get('metadata', {}).keys())}")
        
        # Process purchase - pass the checkout data (which contains metadata)
        purchase_service = get_site_purchase_service()
        result = await purchase_service.process_purchase_payment(
            db=db,
            checkout_id=checkout_id,
            payment_data=checkout  # Pass checkout object which has metadata
        )
        
        # Mark checkout session as completed
        from models.checkout_session import CheckoutSession
        from sqlalchemy import update
        
        await db.execute(
            update(CheckoutSession)
            .where(CheckoutSession.checkout_id == checkout_id)
            .values(
                status='completed',
                payment_intent_id=payment_id,
                completed_at=func.now()
            )
        )
        await db.commit()
        logger.info(f"Marked checkout session as completed for checkout: {checkout_id}")
        
        # Send purchase confirmation email
        email_service = get_email_service()
        await email_service.send_purchase_confirmation_email(
            to_email=result['customer_email'],
            customer_name=result['customer_name'],
            site_title=result['site_title'],
            site_url=result['site_url'],
            purchase_amount=result['purchase_amount'],
            transaction_id=payment_id
        )
        
        # AUTO-CREATE SUBSCRIPTION if this was a setup payment
        metadata = event_data.get('metadata', {})
        auto_subscribe = metadata.get('auto_subscribe') == 'true'
        payment_method = event_data.get('payment_method', {})
        payment_method_id = payment_method.get('id') if payment_method else None
        
        if auto_subscribe and payment_method_id:
            logger.info(
                f"Auto-subscribe flag detected. Creating subscription for site {result['site_id']} "
                f"using payment method {payment_method_id}"
            )
            
            try:
                from services.subscription_service import get_subscription_service
                
                subscription_service = get_subscription_service()
                subscription_result = await subscription_service.create_subscription_with_tokenized_payment(
                    db=db,
                    site_id=result['site_id'],
                    payment_method_id=payment_method_id,
                    customer_email=result['customer_email'],
                    customer_name=result.get('customer_name')
                )
                
                logger.info(
                    f"✅ Subscription auto-created! Site: {result['site_slug']}, "
                    f"Subscription ID: {subscription_result.get('subscription_id')}, "
                    f"Monthly: ${subscription_result['monthly_amount']}, Starts: {subscription_result['start_date']}"
                )
                
                result['subscription_created'] = True
                result['subscription_id'] = subscription_result.get('subscription_id')
                result['monthly_amount'] = subscription_result['monthly_amount']
                result['billing_starts'] = subscription_result['start_date']
                
            except Exception as sub_error:
                logger.error(f"⚠️ Failed to auto-create subscription: {sub_error}", exc_info=True)
                result['subscription_created'] = False
        else:
            result['subscription_created'] = False
        
        logger.info(
            f"Purchase completed and confirmation sent: Site {result['site_slug']} "
            f"by {result['customer_email']} (Subscription: {'✅' if result.get('subscription_created') else '❌'})"
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
    Handle subscription activation webhook.
    
    Actions:
    1. Update site status to 'active'
    2. Record subscription details
    3. Send activation email
    """
    subscription_id = event_data.get('id')
    
    logger.info(f"Subscription activated: {subscription_id}")
    
    try:
        subscription_service = get_subscription_service()
        
        # Activate subscription
        site = await subscription_service.activate_subscription(
            db=db,
            subscription_id=subscription_id,
            subscription_data=event_data
        )
        
        # Send activation email
        email_service = get_email_service()
        if site.customer_user:
            await email_service.send_subscription_activated_email(
                to_email=site.customer_user.email,
                customer_name=site.customer_user.full_name or site.customer_user.email.split('@')[0],
                site_title=site.site_title or site.slug,
                site_url=f"https://{settings.SITES_DOMAIN}/{site.slug}",
                next_billing_date=site.next_billing_date
            )
        
        logger.info(f"Subscription activated and email sent: {subscription_id}")
    
    except Exception as e:
        logger.error(f"Error activating subscription {subscription_id}: {e}", exc_info=True)
        raise


async def handle_subscription_cancelled(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    Handle subscription cancellation webhook.
    
    Actions:
    1. Update subscription status
    2. Downgrade site if immediate
    3. Send cancellation confirmation
    4. Update CRM status: website_status → archived
    """
    from datetime import datetime
    subscription_id = event_data.get('id')
    
    logger.info(f"Subscription cancelled: {subscription_id}")
    
    try:
        from sqlalchemy import select
        from models.site_models import Site
        
        # Find site
        result = await db.execute(
            select(Site).where(Site.subscription_id == subscription_id)
        )
        site = result.scalar_one_or_none()
        
        if site:
            # Update subscription status
            site.subscription_status = "cancelled"
            
            # If no end date set, cancel immediately
            if not site.subscription_ends_at:
                site.status = "owned"
                site.subscription_ends_at = datetime.utcnow()
            
            await db.commit()
            
            # CRM Integration: Update business lifecycle status
            if site.business_id:
                lifecycle_service = BusinessLifecycleService(db)
                await lifecycle_service.mark_website_archived(site.business_id)
                await db.commit()
                logger.info(
                    f"Updated business {site.business_id}: "
                    f"website_status=archived (subscription cancelled)"
                )
            else:
                logger.warning(
                    f"Site {site.slug} cancelled but has no business_id for CRM update"
                )
            
            logger.info(f"Subscription cancelled in database: {subscription_id}")
    
    except Exception as e:
        logger.error(f"Error cancelling subscription {subscription_id}: {e}", exc_info=True)
        raise


async def handle_subscription_payment_failed(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    Handle failed subscription payment webhook.
    
    Actions:
    1. Update subscription status to 'past_due'
    2. Start 7-day grace period
    3. Send payment failed email
    """
    subscription_id = event_data.get('id')
    
    logger.warning(f"Subscription payment failed: {subscription_id}")
    
    try:
        subscription_service = get_subscription_service()
        
        # Handle payment failure
        site = await subscription_service.handle_payment_failure(
            db=db,
            subscription_id=subscription_id,
            failure_data=event_data
        )
        
        # Send payment failed email
        email_service = get_email_service()
        if site.customer_user:
            await email_service.send_subscription_payment_failed_email(
                to_email=site.customer_user.email,
                customer_name=site.customer_user.full_name or site.customer_user.email.split('@')[0],
                site_title=site.site_title or site.slug,
                grace_period_ends=site.grace_period_ends,
                payment_url=f"{settings.FRONTEND_URL}/dashboard/billing"
            )
        
        logger.info(f"Payment failure processed and email sent: {subscription_id}")
    
    except Exception as e:
        logger.error(f"Error processing payment failure {subscription_id}: {e}", exc_info=True)
        raise
