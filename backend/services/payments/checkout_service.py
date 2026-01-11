"""
Checkout service - creates payment sessions and manages checkout flow.
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from services.payments.recurrente_client import RecurrenteClient
from models.customer import Customer, Payment
from models.business import Business
from models.site import GeneratedSite
from core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class CheckoutService:
    """
    Checkout service for creating payment sessions.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.recurrente = RecurrenteClient()
        self.monthly_price_cents = 9900  # $99.00 or Q99.00
        self.currency = "GTQ"  # Guatemalan Quetzal
    
    async def create_checkout_session(
        self,
        site_id: UUID,
        customer_email: str,
        customer_name: Optional[str] = None,
        recurrence_type: str = "subscription",
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a checkout session for a site.
        
        Args:
            site_id: Generated site UUID
            customer_email: Customer email
            customer_name: Customer name
            recurrence_type: "once" or "subscription"
            success_url: Redirect after payment
            cancel_url: Redirect if cancelled
            
        Returns:
            Checkout session data with checkout_url
        """
        logger.info(f"Creating checkout for site: {site_id}")
        
        # Get site and business
        from sqlalchemy import select
        site_result = await self.db.execute(
            select(GeneratedSite).where(GeneratedSite.id == site_id)
        )
        site = site_result.scalar_one_or_none()
        
        if not site:
            raise ValidationException(f"Site not found: {site_id}")
        
        business_result = await self.db.execute(
            select(Business).where(Business.id == site.business_id)
        )
        business = business_result.scalar_one_or_none()
        
        # Build description
        description = f"Website for {business.name if business else 'your business'}"
        if recurrence_type == "subscription":
            description += " - Monthly Subscription"
        
        # Create checkout in Recurrente
        checkout_data = await self.recurrente.create_checkout(
            description=description,
            price_cents=self.monthly_price_cents,
            currency=self.currency,
            recurrence_type=recurrence_type,
            success_url=success_url or f"https://webmagic.com/success?site={site_id}",
            cancel_url=cancel_url or f"https://webmagic.com/cancel?site={site_id}",
            user_email=customer_email,
            user_name=customer_name,
            metadata={
                "site_id": str(site_id),
                "business_id": str(site.business_id),
                "subdomain": site.subdomain
            }
        )
        
        # Get or create customer
        from services.payments.customer_service import CustomerService
        customer_service = CustomerService(self.db)
        customer = await customer_service.get_or_create_customer(
            email=customer_email,
            full_name=customer_name,
            business_id=site.business_id if business else None,
            site_id=site_id
        )
        
        # Create pending payment record
        payment = Payment(
            customer_id=customer.id,
            recurrente_checkout_id=checkout_data.get("id"),
            amount_cents=self.monthly_price_cents,
            currency=self.currency,
            payment_type="subscription_initial" if recurrence_type == "subscription" else "one_time",
            status="pending"
        )
        
        self.db.add(payment)
        await self.db.commit()
        
        logger.info(f"Checkout created: {checkout_data.get('id')}")
        
        return {
            "checkout_id": checkout_data.get("id"),
            "checkout_url": checkout_data.get("checkout_url"),
            "payment_id": str(payment.id),
            "customer_id": str(customer.id),
            "amount": self.monthly_price_cents / 100.0,
            "currency": self.currency,
            "recurrence_type": recurrence_type
        }
    
    async def get_checkout_status(self, checkout_id: str) -> Dict[str, Any]:
        """
        Get checkout status from Recurrente.
        
        Args:
            checkout_id: Recurrente checkout ID
            
        Returns:
            Checkout status data
        """
        checkout_data = await self.recurrente.get_checkout(checkout_id)
        
        return {
            "checkout_id": checkout_id,
            "status": checkout_data.get("status"),
            "paid": checkout_data.get("paid", False),
            "amount": checkout_data.get("price"),
            "currency": checkout_data.get("currency"),
            "user_email": checkout_data.get("user_email"),
            "created_at": checkout_data.get("created_at")
        }
