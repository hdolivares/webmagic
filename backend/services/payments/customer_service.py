"""
Customer service - manages customer records and operations.
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from uuid import UUID
import logging

from models.customer import Customer, Subscription, Payment
from services.payments.recurrente_client import RecurrenteClient
from core.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class CustomerService:
    """Service for customer management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.recurrente = RecurrenteClient()
    
    async def get_or_create_customer(
        self,
        email: str,
        full_name: Optional[str] = None,
        business_id: Optional[UUID] = None,
        site_id: Optional[UUID] = None
    ) -> Customer:
        """Get existing customer or create new one."""
        # Try to find existing
        result = await self.db.execute(
            select(Customer).where(Customer.email == email)
        )
        customer = result.scalar_one_or_none()
        
        if customer:
            return customer
        
        # Create new customer
        customer = Customer(
            email=email,
            full_name=full_name,
            business_id=business_id,
            site_id=site_id,
            status="active"
        )
        
        self.db.add(customer)
        await self.db.flush()
        await self.db.refresh(customer)
        
        logger.info(f"Created customer: {email}")
        return customer
    
    async def get_customer(self, customer_id: UUID) -> Optional[Customer]:
        """Get customer by ID."""
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()
    
    async def list_customers(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> Tuple[List[Customer], int]:
        """List customers with pagination."""
        query = select(Customer)
        count_query = select(func.count(Customer.id))
        
        if status:
            query = query.where(Customer.status == status)
            count_query = count_query.where(Customer.status == status)
        
        query = query.order_by(Customer.created_at.desc())
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        customers = result.scalars().all()
        
        return list(customers), total
    
    async def get_customer_subscriptions(
        self,
        customer_id: UUID
    ) -> List[Subscription]:
        """Get all subscriptions for a customer."""
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.customer_id == customer_id)
            .order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_customer_payments(
        self,
        customer_id: UUID
    ) -> List[Payment]:
        """Get all payments for a customer."""
        result = await self.db.execute(
            select(Payment)
            .where(Payment.customer_id == customer_id)
            .order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get customer statistics."""
        # Total customers
        total_result = await self.db.execute(select(func.count(Customer.id)))
        total = total_result.scalar()
        
        # Active customers
        active_result = await self.db.execute(
            select(func.count(Customer.id)).where(Customer.status == "active")
        )
        active = active_result.scalar()
        
        # Total lifetime value
        ltv_result = await self.db.execute(
            select(func.sum(Customer.lifetime_value_cents))
        )
        total_ltv = ltv_result.scalar() or 0
        
        return {
            "total_customers": total,
            "active_customers": active,
            "total_lifetime_value_cents": total_ltv,
            "average_lifetime_value_cents": total_ltv // total if total > 0 else 0
        }
