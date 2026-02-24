"""
Abandoned Cart Recovery Tasks

Celery tasks for detecting and recovering abandoned checkout sessions.

This module:
1. Runs periodic checks for abandoned checkouts (15+ minutes old)
2. Sends recovery emails with discount codes
3. Tracks email delivery and prevents duplicates

Schedule: Runs every 5 minutes via Celery Beat

Author: WebMagic Team
Date: February 14, 2026
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from celery import shared_task
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from core.config import get_settings
from models.checkout_session import CheckoutSession
from services.emails.email_service import get_email_service
from services.payments.abandoned_cart_coupon_service import create_abandoned_cart_coupon

logger = logging.getLogger(__name__)
_settings = get_settings()


@shared_task(
    name="tasks.check_abandoned_carts",
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def check_abandoned_carts():
    """
    Periodic task to check for abandoned checkout sessions.
    
    Runs every 5 minutes via Celery Beat.
    Finds all checkouts that:
    - Are in 'checkout_created' status
    - Were created 15+ minutes ago
    - Have not received a reminder email yet
    
    Then sends recovery emails with 10% discount codes.
    """
    import asyncio
    
    try:
        # Run async function in sync context
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_process_abandoned_carts())
        
        logger.info(
            f"Abandoned cart check completed: {result['processed']} sessions found, "
            f"{result['emails_sent']} emails sent, {result['errors']} errors"
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error in abandoned cart task: {e}", exc_info=True)
        raise


async def _process_abandoned_carts() -> Dict[str, int]:
    """Process all abandoned carts and send recovery emails."""
    window_minutes = getattr(_settings, "ABANDONED_CART_WINDOW_MINUTES", 15)
    validity_hours = getattr(_settings, "ABANDONED_CART_COUPON_VALIDITY_HOURS", 24)
    abandonment_threshold = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    async with get_async_session() as db:
        query = select(CheckoutSession).where(
            and_(
                CheckoutSession.status == "checkout_created",
                CheckoutSession.created_at < abandonment_threshold,
                CheckoutSession.reminder_sent_at.is_(None),
                CheckoutSession.completed_at.is_(None),
            )
        ).order_by(CheckoutSession.created_at.asc())

        result = await db.execute(query)
        abandoned_sessions: List[CheckoutSession] = result.scalars().all()

        if not abandoned_sessions:
            logger.debug("No abandoned carts found")
            return {"processed": 0, "emails_sent": 0, "errors": 0}

        logger.info(f"Found {len(abandoned_sessions)} abandoned checkout sessions")

        emails_sent = 0
        errors = 0
        email_service = get_email_service()

        for session in abandoned_sessions:
            try:
                discount_code, recurrente_coupon_id = await create_abandoned_cart_coupon(
                    session, db, validity_hours
                )

                await email_service.send_abandoned_cart_email(
                    to_email=session.customer_email,
                    customer_name=session.customer_name,
                    site_slug=session.site_slug,
                    checkout_url=session.checkout_url,
                    discount_code=discount_code,
                    purchase_amount=float(session.purchase_amount),
                    monthly_amount=float(session.monthly_amount),
                )

                session.reminder_sent_at = datetime.now(timezone.utc)
                session.reminder_discount_code = discount_code
                session.status = "abandoned"
                if recurrente_coupon_id is not None:
                    session.recurrente_coupon_id = recurrente_coupon_id

                await db.commit()

                emails_sent += 1
                logger.info(
                    f"Sent abandoned cart email to {session.customer_email} "
                    f"for site {session.site_slug} (discount: {discount_code})"
                )
            except Exception as e:
                errors += 1
                logger.error(
                    f"Failed to send abandoned cart email for session {session.session_id}: {e}",
                    exc_info=True,
                )
                continue

        return {
            "processed": len(abandoned_sessions),
            "emails_sent": emails_sent,
            "errors": errors,
        }


@shared_task(name="tasks.cleanup_old_abandoned_carts")
def cleanup_old_abandoned_carts():
    """
    Cleanup task to archive very old abandoned carts.
    
    Runs daily. Marks sessions abandoned for 30+ days as 'expired'
    to keep the abandoned cart query performant.
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_cleanup_expired_sessions())
        
        logger.info(f"Cleaned up {result['cleaned']} expired abandoned cart sessions")
        return result
    
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}", exc_info=True)
        raise


async def _cleanup_expired_sessions() -> Dict[str, int]:
    """Mark very old abandoned sessions as expired."""
    from sqlalchemy import update
    
    async with get_async_session() as db:
        expiry_threshold = datetime.now(timezone.utc) - timedelta(days=30)
        
        result = await db.execute(
            update(CheckoutSession)
            .where(
                and_(
                    CheckoutSession.status == 'abandoned',
                    CheckoutSession.created_at < expiry_threshold
                )
            )
            .values(status='expired')
        )
        
        await db.commit()
        
        return {"cleaned": result.rowcount}
