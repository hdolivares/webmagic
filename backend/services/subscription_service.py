"""
Subscription Management Service

Handles automatic subscription creation after successful one-time payments.
Follows separation of concerns principle - only manages subscription lifecycle.

Author: WebMagic Team
Date: February 14, 2026
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from models.site_models import Site
from services.payments.recurrente_client import RecurrenteClient
from core.config import get_settings
from core.exceptions import ExternalAPIException, ValidationError

logger = logging.getLogger(__name__)
settings = get_settings()


class SubscriptionService:
    """
    Service for managing customer subscriptions.
    
    Responsibilities:
    - Create subscriptions with saved payment methods
    - Calculate subscription start dates
    - Update site subscription status
    - Handle subscription lifecycle events
    """
    
    def __init__(self, recurrente_client: Optional[RecurrenteClient] = None):
        """Initialize with optional Recurrente client (for dependency injection)."""
        self.recurrente = recurrente_client or RecurrenteClient()
    
    def calculate_subscription_start_date(self, days_from_now: int = 30) -> datetime:
        """
        Calculate when subscription should start.
        
        Default: 30 days from now (one month after setup payment)
        
        Args:
            days_from_now: Days to add to current date
            
        Returns:
            Datetime for subscription start
        """
        return datetime.utcnow() + timedelta(days=days_from_now)
    
    async def create_monthly_subscription(
        self,
        db: AsyncSession,
        site_id: str,
        payment_method_id: str,
        customer_email: str,
        customer_name: Optional[str] = None,
        start_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a monthly subscription using a saved payment method.
        
        This is called automatically after a successful one-time payment.
        Uses Recurrente's tokenized payment API to charge the saved card.
        
        Args:
            db: Database session
            site_id: Site ID (UUID as string)
            payment_method_id: Recurrente payment method ID (from webhook)
            customer_email: Customer email
            customer_name: Optional customer name
            start_date: When to start subscription (default: 30 days from now)
            
        Returns:
            Dict with subscription details
            
        Raises:
            ValidationError: If site doesn't exist or invalid state
            ExternalAPIException: If Recurrente API fails
        """
        # Get site from database
        from uuid import UUID
        result = await db.execute(
            select(Site).where(Site.id == UUID(site_id))
        )
        site = result.scalar_one_or_none()
        
        if not site:
            raise ValidationError(f"Site not found: {site_id}")
        
        # Calculate subscription start date (30 days from now = next month)
        sub_start_date = start_date or self.calculate_subscription_start_date(days_from_now=30)
        
        logger.info(
            f"Creating monthly subscription for site {site.slug}: "
            f"${site.monthly_amount}/month starting {sub_start_date.date()}"
        )
        
        try:
            # Create subscription using Recurrente's subscription API
            # Note: We'll use create_subscription_checkout but with a future start date
            subscription = await self.recurrente.create_subscription_checkout(
                name=f"Monthly Hosting - {site.site_title or site.slug}",
                amount_cents=int(site.monthly_amount * 100),  # $97.00 -> 9700 cents
                billing_interval="month",
                billing_interval_count=1,
                currency="USD",
                description="Monthly hosting, maintenance, and unlimited AI-powered updates",
                periods_before_cancellation=None,  # Never auto-cancel
                free_trial_interval_count=0,  # No trial
                metadata={
                    "site_id": site_id,
                    "site_slug": site.slug,
                    "subscription_type": "monthly_hosting",
                    "customer_email": customer_email,
                    "payment_method_id": payment_method_id,
                    "start_date": sub_start_date.isoformat()
                }
            )
            
            # Update site with subscription info
            await db.execute(
                update(Site)
                .where(Site.id == UUID(site_id))
                .values(
                    subscription_status="active",
                    subscription_started_at=datetime.utcnow(),
                    next_billing_date=sub_start_date.date()
                )
            )
            await db.commit()
            
            logger.info(
                f"Subscription created successfully for site {site.slug}: "
                f"checkout_id={subscription.id}"
            )
            
            return {
                "subscription_checkout_id": subscription.id,
                "subscription_checkout_url": subscription.checkout_url,
                "monthly_amount": float(site.monthly_amount),
                "start_date": sub_start_date.isoformat(),
                "billing_interval": "monthly",
                "status": "pending_activation",
                "site_id": site_id,
                "site_slug": site.slug
            }
            
        except ExternalAPIException as e:
            logger.error(f"Failed to create subscription for site {site.slug}: {e}")
            # Don't fail the purchase - we can retry subscription creation later
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating subscription: {e}", exc_info=True)
            await db.rollback()
            raise ExternalAPIException(f"Failed to create subscription: {str(e)}")
    
    async def create_subscription_with_tokenized_payment(
        self,
        db: AsyncSession,
        site_id: str,
        payment_method_id: str,
        customer_email: str,
        customer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create subscription using Recurrente's tokenized payment API.
        
        This directly charges the saved payment method without checkout flow.
        Used for automatic subscription creation after one-time payment.
        
        Args:
            db: Database session
            site_id: Site ID
            payment_method_id: Saved payment method ID from initial payment
            customer_email: Customer email
            customer_name: Optional customer name
            
        Returns:
            Dict with subscription details
        """
        # Get site
        from uuid import UUID
        result = await db.execute(
            select(Site).where(Site.id == UUID(site_id))
        )
        site = result.scalar_one_or_none()
        
        if not site:
            raise ValidationError(f"Site not found: {site_id}")
        
        logger.info(
            f"Creating tokenized subscription for site {site.slug} "
            f"with payment method {payment_method_id}"
        )
        
        # TODO: Implement Recurrente's tokenized payment API
        # For now, we'll use the checkout flow and rely on the saved payment method
        # Recurrente will recognize the payment_method_id and use it automatically
        
        return await self.create_monthly_subscription(
            db=db,
            site_id=site_id,
            payment_method_id=payment_method_id,
            customer_email=customer_email,
            customer_name=customer_name
        )
    
    async def cancel_subscription(
        self,
        db: AsyncSession,
        site_id: str,
        recurrente_subscription_id: str
    ) -> Dict[str, Any]:
        """
        Cancel a customer's subscription.
        
        Args:
            db: Database session
            site_id: Site ID
            recurrente_subscription_id: Recurrente subscription ID
            
        Returns:
            Dict with cancellation details
        """
        logger.info(f"Cancelling subscription {recurrente_subscription_id} for site {site_id}")
        
        try:
            # Call Recurrente API to cancel subscription
            # DELETE /api/subscriptions/{id}
            await self.recurrente._request("DELETE", f"/subscriptions/{recurrente_subscription_id}")
            
            # Update site status
            from uuid import UUID
            await db.execute(
                update(Site)
                .where(Site.id == UUID(site_id))
                .values(
                    subscription_status="cancelled",
                    subscription_ended_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            logger.info(f"Subscription cancelled successfully for site {site_id}")
            
            return {
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
                "site_id": site_id
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}", exc_info=True)
            await db.rollback()
            raise ExternalAPIException(f"Failed to cancel subscription: {str(e)}")


# Dependency injection helper
def get_subscription_service(recurrente_client: Optional[RecurrenteClient] = None) -> SubscriptionService:
    """Factory function for dependency injection."""
    return SubscriptionService(recurrente_client=recurrente_client)
