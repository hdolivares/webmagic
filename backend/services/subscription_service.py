"""
Subscription Service

Handles $95/month recurring subscriptions for site hosting.

Features:
- Subscription activation
- Payment processing
- Grace period management
- Cancellation/reactivation

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.site_models import Site, CustomerUser
from services.payments.recurrente_client import RecurrenteClient
from core.exceptions import NotFoundError, ValidationError, ConflictError
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Subscription configuration
MONTHLY_SUBSCRIPTION_AMOUNT = Decimal("95.00")  # $95/month
GRACE_PERIOD_DAYS = 7  # Days before suspension after payment failure


class SubscriptionService:
    """Service for managing recurring subscriptions."""
    
    @staticmethod
    async def create_subscription(
        db: AsyncSession,
        site_id: UUID,
        customer_id: UUID,
        payment_method_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create recurring subscription via Recurrente.
        
        Args:
            db: Database session
            site_id: Site ID to activate subscription for
            customer_id: Customer user ID
            payment_method_token: Optional payment method token
        
        Returns:
            dict with subscription_id and payment_url
        
        Raises:
            NotFoundError: Site or customer not found
            ValidationError: Site not in correct state
            ConflictError: Subscription already active
        """
        # Get site and customer
        site_result = await db.execute(select(Site).where(Site.id == site_id))
        site = site_result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found: {site_id}")
        
        customer_result = await db.execute(
            select(CustomerUser).where(CustomerUser.id == customer_id)
        )
        customer = customer_result.scalar_one_or_none()
        
        if not customer:
            raise NotFoundError(f"Customer not found: {customer_id}")
        
        # Validate site ownership (customer has site_id, not site has customer_id)
        if customer.site_id != site_id:
            raise ValidationError("You don't own this site")
        
        # Validate site status (must be owned, not active already)
        if site.status not in ["owned", "past_due"]:
            raise ValidationError(f"Site status '{site.status}' cannot activate subscription")
        
        if site.subscription_status == "active":
            raise ConflictError("Subscription already active")
        
        # Create subscription in Recurrente
        recurrente = RecurrenteClient()
        
        try:
            subscription_data = recurrente.create_subscription(
                customer_email=customer.email,
                customer_name=customer.full_name or customer.email.split('@')[0],
                plan_id=settings.RECURRENTE_SUBSCRIPTION_PLAN_ID,
                amount=float(MONTHLY_SUBSCRIPTION_AMOUNT),
                currency="USD",
                interval="month",
                interval_count=1,
                metadata={
                    "site_id": str(site.id),
                    "customer_id": str(customer.id),
                    "site_slug": site.slug,
                    "type": "monthly_subscription"
                },
                payment_method_token=payment_method_token
            )
            
            logger.info(
                f"Subscription created in Recurrente: {subscription_data.get('id')} "
                f"for site {site.slug}"
            )
            
            return {
                "subscription_id": subscription_data.get("id"),
                "payment_url": subscription_data.get("payment_url"),
                "status": "pending",
                "monthly_amount": float(MONTHLY_SUBSCRIPTION_AMOUNT)
            }
        
        except Exception as e:
            logger.error(f"Failed to create subscription in Recurrente: {e}")
            raise ValidationError(f"Failed to create subscription: {str(e)}")
    
    @staticmethod
    async def activate_subscription(
        db: AsyncSession,
        subscription_id: str,
        subscription_data: Dict[str, Any]
    ) -> Site:
        """
        Activate subscription after Recurrente confirmation.
        
        Args:
            db: Database session
            subscription_id: Recurrente subscription ID
            subscription_data: Subscription data from webhook
        
        Returns:
            Updated Site object
        
        Raises:
            NotFoundError: Site not found in metadata
        """
        # Extract site_id from metadata
        metadata = subscription_data.get("metadata", {})
        site_id = metadata.get("site_id")
        
        if not site_id:
            raise NotFoundError("Site ID not found in subscription metadata")
        
        # Get site
        site_result = await db.execute(
            select(Site).where(Site.id == UUID(site_id))
        )
        site = site_result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found: {site_id}")
        
        # Calculate next billing date (30 days from now)
        started_at = datetime.now()
        next_billing = (started_at + timedelta(days=30)).date()
        
        # Update site
        site.status = "active"
        site.subscription_id = subscription_id
        site.subscription_status = "active"
        site.subscription_started_at = started_at
        site.subscription_ends_at = None  # No end date for active subscription
        site.next_billing_date = next_billing
        site.monthly_amount = MONTHLY_SUBSCRIPTION_AMOUNT
        
        await db.commit()
        await db.refresh(site)
        
        logger.info(
            f"Subscription activated: {subscription_id} for site {site.slug}, "
            f"next billing: {next_billing}"
        )
        
        return site
    
    @staticmethod
    async def handle_payment_success(
        db: AsyncSession,
        subscription_id: str,
        payment_data: Dict[str, Any]
    ) -> Site:
        """
        Process successful recurring payment.
        
        Args:
            db: Database session
            subscription_id: Subscription ID
            payment_data: Payment data from webhook
        
        Returns:
            Updated Site object
        """
        # Find site by subscription_id
        site_result = await db.execute(
            select(Site).where(Site.subscription_id == subscription_id)
        )
        site = site_result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found for subscription: {subscription_id}")
        
        # Update billing date (add 30 days)
        if site.next_billing_date:
            site.next_billing_date = site.next_billing_date + timedelta(days=30)
        else:
            site.next_billing_date = (datetime.utcnow() + timedelta(days=30)).date()
        
        # Ensure status is active (in case it was past_due)
        if site.subscription_status in ["past_due", "active"]:
            site.status = "active"
            site.subscription_status = "active"
            site.grace_period_ends = None  # Clear grace period
        
        await db.commit()
        await db.refresh(site)
        
        logger.info(
            f"Payment successful for subscription {subscription_id}, "
            f"next billing: {site.next_billing_date}"
        )
        
        return site
    
    @staticmethod
    async def handle_payment_failure(
        db: AsyncSession,
        subscription_id: str,
        failure_data: Dict[str, Any]
    ) -> Site:
        """
        Handle failed recurring payment.
        
        Starts 7-day grace period. After grace period, site downgrades to 'owned'.
        
        Args:
            db: Database session
            subscription_id: Subscription ID
            failure_data: Failure data from webhook
        
        Returns:
            Updated Site object
        """
        # Find site
        site_result = await db.execute(
            select(Site).where(Site.subscription_id == subscription_id)
        )
        site = site_result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found for subscription: {subscription_id}")
        
        # Start grace period
        grace_period_end = datetime.now() + timedelta(days=GRACE_PERIOD_DAYS)
        
        site.subscription_status = "past_due"
        site.grace_period_ends = grace_period_end
        # Keep status="active" during grace period so customer can update payment
        
        await db.commit()
        await db.refresh(site)
        
        logger.warning(
            f"Payment failed for subscription {subscription_id}, "
            f"grace period until {grace_period_end}"
        )
        
        return site
    
    @staticmethod
    async def cancel_subscription(
        db: AsyncSession,
        site_id: UUID,
        immediate: bool = False,
        reason: Optional[str] = None
    ) -> Site:
        """
        Cancel subscription.
        
        Args:
            db: Database session
            site_id: Site ID
            immediate: If True, cancel immediately. If False, cancel at period end.
            reason: Optional cancellation reason
        
        Returns:
            Updated Site object
        
        Raises:
            NotFoundError: Site not found
            ValidationError: No active subscription
        """
        # Get site
        site_result = await db.execute(select(Site).where(Site.id == site_id))
        site = site_result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found: {site_id}")
        
        if not site.subscription_id:
            raise ValidationError("No subscription to cancel")
        
        if site.subscription_status in ["cancelled", "expired"]:
            raise ValidationError("Subscription already cancelled")
        
        # Cancel in Recurrente
        recurrente = RecurrenteClient()
        
        try:
            await recurrente.cancel_subscription(
                subscription_id=site.subscription_id,
                reason=reason
            )
        except Exception as e:
            logger.error(f"Failed to cancel subscription in Recurrente: {e}")
            # Continue anyway to update local state
        
        # Update site
        site.subscription_status = "cancelled"
        
        if immediate:
            # Cancel immediately
            site.status = "owned"
            site.subscription_ends_at = datetime.utcnow()
            logger.info(f"Subscription cancelled immediately for site {site.slug}")
        else:
            # Cancel at end of billing period
            if site.next_billing_date:
                site.subscription_ends_at = datetime.combine(
                    site.next_billing_date,
                    datetime.min.time()
                )
            else:
                site.subscription_ends_at = datetime.now()
            logger.info(
                f"Subscription will cancel at period end for site {site.slug}: "
                f"{site.subscription_ends_at}"
            )
        
        await db.commit()
        await db.refresh(site)
        
        return site
    
    @staticmethod
    async def reactivate_subscription(
        db: AsyncSession,
        site_id: UUID,
        payment_method_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reactivate a cancelled subscription.
        
        Args:
            db: Database session
            site_id: Site ID
            payment_method_token: Optional payment method token
        
        Returns:
            dict with reactivation details
        
        Raises:
            NotFoundError: Site not found
            ValidationError: Cannot reactivate
        """
        # Get site
        site_result = await db.execute(select(Site).where(Site.id == site_id))
        site = site_result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found: {site_id}")
        
        if site.subscription_status == "active":
            raise ValidationError("Subscription is already active")
        
        if not site.customer_id:
            raise ValidationError("No customer associated with site")
        
        # If previously had subscription, try to reactivate in Recurrente
        if site.subscription_id and site.subscription_status == "cancelled":
            recurrente = RecurrenteClient()
            
            try:
                result = recurrente.reactivate_subscription(
                    subscription_id=site.subscription_id
                )
                
                # Update site
                site.status = "active"
                site.subscription_status = "active"
                site.subscription_ends_at = None
                site.next_billing_date = (datetime.utcnow() + timedelta(days=30)).date()
                
                await db.commit()
                await db.refresh(site)
                
                logger.info(f"Subscription reactivated for site {site.slug}")
                
                return {
                    "subscription_id": site.subscription_id,
                    "status": "active",
                    "next_billing_date": str(site.next_billing_date)
                }
            
            except Exception as e:
                logger.error(f"Failed to reactivate in Recurrente: {e}")
                # Fall through to create new subscription
        
        # Create new subscription
        return await SubscriptionService.create_subscription(
            db=db,
            site_id=site_id,
            customer_id=site.customer_id,
            payment_method_token=payment_method_token
        )
    
    @staticmethod
    async def get_subscription_status(
        db: AsyncSession,
        site_id: UUID
    ) -> Dict[str, Any]:
        """
        Get current subscription status for a site.
        
        Args:
            db: Database session
            site_id: Site ID
        
        Returns:
            dict with subscription details
        
        Raises:
            NotFoundError: Site not found
        """
        site_result = await db.execute(select(Site).where(Site.id == site_id))
        site = site_result.scalar_one_or_none()
        
        if not site:
            raise NotFoundError(f"Site not found: {site_id}")
        
        return {
            "subscription_id": site.subscription_id,
            "status": site.subscription_status or "none",
            "monthly_amount": float(site.monthly_amount) if site.monthly_amount else 0,
            "started_at": site.subscription_started_at.isoformat() if site.subscription_started_at else None,
            "next_billing_date": str(site.next_billing_date) if site.next_billing_date else None,
            "ends_at": site.subscription_ends_at.isoformat() if site.subscription_ends_at else None,
            "grace_period_ends": site.grace_period_ends.isoformat() if site.grace_period_ends else None,
            "is_active": site.subscription_status == "active",
            "is_past_due": site.subscription_status == "past_due",
            "is_cancelled": site.subscription_status == "cancelled"
        }


def get_subscription_service() -> SubscriptionService:
    """Get subscription service instance."""
    return SubscriptionService()
