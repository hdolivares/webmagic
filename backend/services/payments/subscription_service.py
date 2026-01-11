"""
Subscription management service.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
from datetime import datetime
import logging

from models.customer import Subscription
from services.payments.recurrente_client import RecurrenteClient

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for subscription management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.recurrente = RecurrenteClient()
    
    async def get_subscription(self, subscription_id: UUID) -> Optional[Subscription]:
        """Get subscription by ID."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()
    
    async def cancel_subscription(
        self,
        subscription_id: UUID,
        reason: Optional[str] = None
    ) -> bool:
        """Cancel a subscription."""
        subscription = await self.get_subscription(subscription_id)
        if not subscription or not subscription.recurrente_subscription_id:
            return False
        
        # Cancel in Recurrente
        await self.recurrente.cancel_subscription(
            subscription.recurrente_subscription_id,
            reason=reason
        )
        
        # Update local record
        await self.db.execute(
            update(Subscription)
            .where(Subscription.id == subscription_id)
            .values(
                status="cancelled",
                cancelled_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()
        
        logger.info(f"Cancelled subscription: {subscription_id}")
        return True
