"""
Webhook handler for Recurrente payment events.
"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
import logging

from models.customer import Customer, Subscription, Payment
from services.payments.recurrente_client import RecurrenteClient

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handles Recurrente webhook events."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.recurrente = RecurrenteClient()
    
    async def handle_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Handle webhook event.
        
        Args:
            event_type: Event type (payment.completed, subscription.created, etc.)
            payload: Event payload
            
        Returns:
            True if handled successfully
        """
        logger.info(f"Handling webhook: {event_type}")
        
        try:
            if event_type == "payment.completed":
                return await self._handle_payment_completed(payload)
            elif event_type == "subscription.created":
                return await self._handle_subscription_created(payload)
            elif event_type == "subscription.cancelled":
                return await self._handle_subscription_cancelled(payload)
            elif event_type == "payment.failed":
                return await self._handle_payment_failed(payload)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return False
                
        except Exception as e:
            logger.error(f"Webhook handling failed: {str(e)}", exc_info=True)
            return False
    
    async def _handle_payment_completed(self, payload: Dict[str, Any]) -> bool:
        """Handle successful payment."""
        payment_id = payload.get("payment_id")
        checkout_id = payload.get("checkout_id")
        
        # Find payment record
        result = await self.db.execute(
            select(Payment).where(Payment.recurrente_checkout_id == checkout_id)
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            await self.db.execute(
                update(Payment)
                .where(Payment.id == payment.id)
                .values(
                    recurrente_payment_id=payment_id,
                    status="completed",
                    paid_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            logger.info(f"Payment completed: {payment_id}")
        
        return True
    
    async def _handle_subscription_created(self, payload: Dict[str, Any]) -> bool:
        """Handle subscription creation."""
        subscription_id = payload.get("subscription_id")
        checkout_id = payload.get("checkout_id")
        
        # Find payment to link subscription
        result = await self.db.execute(
            select(Payment).where(Payment.recurrente_checkout_id == checkout_id)
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            # Create subscription record
            subscription = Subscription(
                customer_id=payment.customer_id,
                site_id=None,  # Get from payment metadata if needed
                recurrente_subscription_id=subscription_id,
                recurrente_checkout_id=checkout_id,
                amount_cents=payment.amount_cents,
                currency=payment.currency,
                status="active",
                started_at=datetime.utcnow()
            )
            
            self.db.add(subscription)
            await self.db.commit()
            logger.info(f"Subscription created: {subscription_id}")
        
        return True
    
    async def _handle_subscription_cancelled(self, payload: Dict[str, Any]) -> bool:
        """Handle subscription cancellation."""
        subscription_id = payload.get("subscription_id")
        
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.recurrente_subscription_id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()
        
        if subscription:
            await self.db.execute(
                update(Subscription)
                .where(Subscription.id == subscription.id)
                .values(
                    status="cancelled",
                    cancelled_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            logger.info(f"Subscription cancelled: {subscription_id}")
        
        return True
    
    async def _handle_payment_failed(self, payload: Dict[str, Any]) -> bool:
        """Handle failed payment."""
        payment_id = payload.get("payment_id")
        
        result = await self.db.execute(
            select(Payment).where(Payment.recurrente_payment_id == payment_id)
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            await self.db.execute(
                update(Payment)
                .where(Payment.id == payment.id)
                .values(
                    status="failed",
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            logger.info(f"Payment failed: {payment_id}")
        
        return True
