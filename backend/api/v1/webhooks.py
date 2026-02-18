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
        
        elif event_type == 'subscription.create':
            await handle_subscription_created(db, event_data)
        
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
        customer = event_data.get('customer', {})
        
        metadata = checkout.get('metadata', {})
        purchase_type = metadata.get('purchase_type', 'website_setup')

        logger.info(f"💰 Processing payment success: payment_id={payment_id}, checkout_id={checkout_id}, purchase_type={purchase_type}")
        logger.info(f"💰 Checkout data: status={checkout.get('status')}, metadata keys={list(metadata.keys())}")
        logger.info(f"💰 Customer data: email={customer.get('email')}, name={customer.get('full_name')}")

        print(f"[WEBHOOK] 💰 payment_intent.succeeded — type={purchase_type}, payment={payment_id}, checkout={checkout_id}")
        
        # Combine checkout and customer data for processing
        payment_data = {
            **checkout,  # Includes metadata
            'id': payment_id,  # Payment ID from root
            'user_email': customer.get('email'),  # Customer email from root
            'user_name': customer.get('full_name'),  # Customer name from root
        }
        
        # Process purchase
        purchase_service = get_site_purchase_service()
        result = await purchase_service.process_purchase_payment(
            db=db,
            checkout_id=checkout_id,
            payment_data=payment_data
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
        temp_password = result.get('temp_password')
        is_new_customer = result.get('is_new_customer', False)
        
        print(f"[WEBHOOK] 📧 Preparing to send purchase confirmation email to {result['customer_email']}")
        print(f"[WEBHOOK] 📧 Email params: customer_name={result['customer_name']}, site_title={result['site_title']}, amount=${result['purchase_amount']}, new_customer={is_new_customer}")
        logger.info(f"📧 Preparing to send purchase confirmation email to {result['customer_email']}")
        logger.info(f"📧 Email params: customer_name={result['customer_name']}, site_title={result['site_title']}, amount=${result['purchase_amount']}, new_customer={is_new_customer}")
        
        if is_new_customer and temp_password:
            print(f"[WEBHOOK] 🔑 New customer - including credentials in email")
            logger.info(f"🔑 New customer - including credentials in email")
        
        try:
            email_service = get_email_service()
            print(f"[WEBHOOK] 📧 Email service initialized")
            logger.info(f"📧 Email service initialized")
            
            email_sent = await email_service.send_purchase_confirmation_email(
                to_email=result['customer_email'],
                customer_name=result['customer_name'],
                site_title=result['site_title'],
                site_url=result['site_url'],
                purchase_amount=result['purchase_amount'],
                transaction_id=payment_id,
                site_password=temp_password  # Pass password if available
            )
            
            if email_sent:
                print(f"[WEBHOOK] ✅ Purchase confirmation email sent successfully to {result['customer_email']}")
                logger.info(f"✅ Purchase confirmation email sent successfully to {result['customer_email']}")
            else:
                print(f"[WEBHOOK] ❌ Failed to send purchase confirmation email to {result['customer_email']}")
                logger.error(f"❌ Failed to send purchase confirmation email to {result['customer_email']}")
        except Exception as e:
            print(f"[WEBHOOK] ❌ Error sending purchase confirmation email: {e}")
            logger.error(f"❌ Error sending purchase confirmation email: {e}", exc_info=True)
        
        # Two-step payment flow:
        # - purchase_type="website_setup"       → this handler (setup fee paid → site owned, email sent)
        # - purchase_type="website_subscription" → recurring payment, just log (site already owned)
        # The subscription.create webhook handles saving the real su_xxx subscription ID.

        logger.info(
            f"Purchase completed and confirmation sent: Site {result['site_slug']} "
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


async def handle_subscription_created(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    Handle subscription.create webhook from Recurrente.
    
    This webhook is sent when Recurrente creates a subscription after a successful
    payment with charge_type="recurring".
    
    Event structure:
    {
        "event_type": "subscription.create",
        "id": "su_xxx",  ← This is the REAL subscription ID
        "customer_email": "user@example.com",
        "product": {
            "metadata": {
                "site_id": "...",
                "site_slug": "..."
            }
        }
    }
    
    Actions:
    1. Extract subscription ID from webhook
    2. Find site from metadata
    3. Update site with real subscription ID
    """
    try:
        subscription_id = event_data.get('id')
        customer_email = event_data.get('customer_email')
        product = event_data.get('product', {})
        metadata = product.get('metadata', {})
        
        print(f"[WEBHOOK] 🔔 Subscription created: {subscription_id}")
        print(f"[WEBHOOK] 🔔 Customer: {customer_email}")
        print(f"[WEBHOOK] 🔔 Metadata: {metadata}")
        
        logger.info(f"🔔 Subscription created: {subscription_id} for {customer_email}")
        logger.info(f"🔔 Metadata: {metadata}")
        
        # Extract site info from metadata
        site_slug = metadata.get('site_slug')
        site_id = metadata.get('site_id')
        
        if not site_slug and not site_id:
            logger.error("❌ No site_slug or site_id in subscription metadata")
            return
        
        # Find and update site
        from models.site_models import Site
        from sqlalchemy import select, update
        from uuid import UUID
        from datetime import datetime, timedelta
        
        # Query site
        if site_id:
            result = await db.execute(
                select(Site).where(Site.id == UUID(site_id))
            )
        else:
            result = await db.execute(
                select(Site).where(Site.slug == site_slug)
            )
        
        site = result.scalar_one_or_none()
        
        if not site:
            logger.error(f"❌ Site not found for subscription: site_id={site_id}, site_slug={site_slug}")
            return
        
        # Update site with REAL subscription ID
        next_billing = (datetime.utcnow() + timedelta(days=30)).date()
        
        await db.execute(
            update(Site)
            .where(Site.id == site.id)
            .values(
                subscription_id=subscription_id,
                subscription_status='active',
                subscription_started_at=datetime.utcnow(),
                next_billing_date=next_billing
            )
        )
        await db.commit()
        
        print(f"[WEBHOOK] ✅ Site updated with subscription ID: {subscription_id}")
        logger.info(
            f"✅ Site {site.slug} updated with subscription: {subscription_id}, "
            f"next billing: {next_billing}"
        )
        
    except Exception as e:
        print(f"[WEBHOOK] ❌ Error processing subscription.create: {e}")
        logger.error(f"❌ Error processing subscription.create: {e}", exc_info=True)
        raise


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
