"""
Business Lifecycle Service

Manages automated status transitions throughout the lead/customer lifecycle.
Ensures CRM status fields stay synchronized with actual business events.

Lifecycle States:
- Contact Status: pending → emailed → opened → clicked → replied → purchased
- Website Status: none → generating → generated → deployed → sold → archived

Best Practices:
- Idempotent: Safe to call multiple times
- Atomic: All updates within database transactions
- Auditable: Comprehensive logging
- Flexible: Supports manual overrides

Author: WebMagic Team
Date: January 22, 2026
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from uuid import UUID
from datetime import datetime
import logging

from models.business import Business
from core.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class BusinessLifecycleService:
    """
    Service for managing business lifecycle status transitions.
    
    Responsibilities:
    - Update contact_status based on campaign events
    - Update website_status based on site generation/deployment
    - Maintain CRM audit trail
    - Trigger follow-up actions
    """
    
    # Status Constants (aligned with LeadService)
    CONTACT_STATUS_PENDING = "pending"
    CONTACT_STATUS_EMAILED = "emailed"
    CONTACT_STATUS_SMS_SENT = "sms_sent"
    CONTACT_STATUS_OPENED = "opened"
    CONTACT_STATUS_CLICKED = "clicked"
    CONTACT_STATUS_REPLIED = "replied"
    CONTACT_STATUS_PURCHASED = "purchased"
    CONTACT_STATUS_UNSUBSCRIBED = "unsubscribed"
    CONTACT_STATUS_BOUNCED = "bounced"
    
    WEBSITE_STATUS_NONE = "none"
    WEBSITE_STATUS_GENERATING = "generating"
    WEBSITE_STATUS_GENERATED = "generated"
    WEBSITE_STATUS_DEPLOYED = "deployed"
    WEBSITE_STATUS_SOLD = "sold"
    WEBSITE_STATUS_ARCHIVED = "archived"
    
    def __init__(self, db: AsyncSession):
        """
        Initialize lifecycle service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    # ========================================================================
    # CONTACT STATUS TRANSITIONS
    # ========================================================================
    
    async def mark_campaign_sent(
        self,
        business_id: UUID,
        channel: str = "email"
    ) -> bool:
        """
        Mark that a campaign was sent to this business.
        
        Transitions:
        - pending → emailed (email channel)
        - pending → sms_sent (SMS channel)
        
        Args:
            business_id: Business UUID
            channel: "email" or "sms"
        
        Returns:
            True if status was updated
        """
        try:
            new_status = (
                self.CONTACT_STATUS_EMAILED if channel == "email"
                else self.CONTACT_STATUS_SMS_SENT
            )
            
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.contact_status == self.CONTACT_STATUS_PENDING
                )
                .values(
                    contact_status=new_status,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.info(
                    f"Business {business_id}: "
                    f"contact_status = {new_status} (campaign sent)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking campaign sent: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update contact status: {str(e)}")
    
    async def mark_campaign_opened(self, business_id: UUID) -> bool:
        """
        Mark that a campaign email was opened.
        
        Transitions:
        - emailed → opened
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.contact_status == self.CONTACT_STATUS_EMAILED
                )
                .values(
                    contact_status=self.CONTACT_STATUS_OPENED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.info(
                    f"Business {business_id}: "
                    f"contact_status = opened (email opened)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking campaign opened: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update contact status: {str(e)}")
    
    async def mark_link_clicked(self, business_id: UUID) -> bool:
        """
        Mark that a link in the campaign was clicked.
        
        Transitions:
        - emailed → clicked
        - opened → clicked
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.contact_status.in_([
                        self.CONTACT_STATUS_EMAILED,
                        self.CONTACT_STATUS_OPENED
                    ])
                )
                .values(
                    contact_status=self.CONTACT_STATUS_CLICKED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.info(
                    f"Business {business_id}: "
                    f"contact_status = clicked (link clicked)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking link clicked: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update contact status: {str(e)}")
    
    async def mark_replied(self, business_id: UUID) -> bool:
        """
        Mark that the business replied to outreach.
        
        Transitions:
        - Any non-terminal status → replied
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.contact_status.notin_([
                        self.CONTACT_STATUS_PURCHASED,
                        self.CONTACT_STATUS_UNSUBSCRIBED
                    ])
                )
                .values(
                    contact_status=self.CONTACT_STATUS_REPLIED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.info(
                    f"Business {business_id}: "
                    f"contact_status = replied (reply received)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking replied: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update contact status: {str(e)}")
    
    async def mark_purchased(self, business_id: UUID) -> bool:
        """
        Mark that the business purchased a website.
        
        This is a TERMINAL status - the business is now a paying customer.
        
        Transitions:
        - Any status → purchased
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(Business.id == business_id)
                .values(
                    contact_status=self.CONTACT_STATUS_PURCHASED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.info(
                    f"Business {business_id}: "
                    f"contact_status = purchased (CUSTOMER)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking purchased: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update contact status: {str(e)}")
    
    async def mark_unsubscribed(self, business_id: UUID) -> bool:
        """
        Mark that the business unsubscribed from communications.
        
        This is a TERMINAL status - no more outreach allowed.
        
        Transitions:
        - Any non-purchased status → unsubscribed
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.contact_status != self.CONTACT_STATUS_PURCHASED
                )
                .values(
                    contact_status=self.CONTACT_STATUS_UNSUBSCRIBED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.warning(
                    f"Business {business_id}: "
                    f"contact_status = unsubscribed (opt-out)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking unsubscribed: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update contact status: {str(e)}")
    
    async def mark_bounced(self, business_id: UUID) -> bool:
        """
        Mark that communications bounced (invalid email/phone).
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.contact_status.notin_([
                        self.CONTACT_STATUS_PURCHASED,
                        self.CONTACT_STATUS_UNSUBSCRIBED
                    ])
                )
                .values(
                    contact_status=self.CONTACT_STATUS_BOUNCED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.warning(
                    f"Business {business_id}: "
                    f"contact_status = bounced (invalid contact)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking bounced: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update contact status: {str(e)}")
    
    # ========================================================================
    # WEBSITE STATUS TRANSITIONS
    # ========================================================================
    
    async def mark_website_generating(self, business_id: UUID) -> bool:
        """
        Mark that website generation has started.
        
        Transitions:
        - none → generating
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.website_status == self.WEBSITE_STATUS_NONE
                )
                .values(
                    website_status=self.WEBSITE_STATUS_GENERATING,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.info(
                    f"Business {business_id}: "
                    f"website_status = generating (AI started)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking generating: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update website status: {str(e)}")
    
    async def mark_website_generated(self, business_id: UUID) -> bool:
        """
        Mark that website generation completed successfully.
        
        Transitions:
        - generating → generated
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.website_status == self.WEBSITE_STATUS_GENERATING
                )
                .values(
                    website_status=self.WEBSITE_STATUS_GENERATED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.info(
                    f"Business {business_id}: "
                    f"website_status = generated (site ready)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking generated: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update website status: {str(e)}")
    
    async def mark_website_deployed(self, business_id: UUID) -> bool:
        """
        Mark that website was deployed to production.
        
        Transitions:
        - generated → deployed
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.website_status == self.WEBSITE_STATUS_GENERATED
                )
                .values(
                    website_status=self.WEBSITE_STATUS_DEPLOYED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.info(
                    f"Business {business_id}: "
                    f"website_status = deployed (live site)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking deployed: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update website status: {str(e)}")
    
    async def mark_website_sold(self, business_id: UUID) -> bool:
        """
        Mark that website was sold/purchased.
        
        This triggers BOTH website_status AND contact_status updates.
        
        Transitions:
        - deployed → sold (website_status)
        - any → purchased (contact_status)
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(Business.id == business_id)
                .values(
                    website_status=self.WEBSITE_STATUS_SOLD,
                    contact_status=self.CONTACT_STATUS_PURCHASED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.info(
                    f"Business {business_id}: "
                    f"website_status = sold, contact_status = purchased "
                    f"(CONVERSION!)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking sold: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update website status: {str(e)}")
    
    async def mark_website_archived(self, business_id: UUID) -> bool:
        """
        Mark that website was archived (subscription cancelled).
        
        Transitions:
        - sold → archived
        
        Args:
            business_id: Business UUID
        
        Returns:
            True if status was updated
        """
        try:
            result = await self.db.execute(
                update(Business)
                .where(
                    Business.id == business_id,
                    Business.website_status == self.WEBSITE_STATUS_SOLD
                )
                .values(
                    website_status=self.WEBSITE_STATUS_ARCHIVED,
                    updated_at=datetime.utcnow()
                )
            )
            
            updated = result.rowcount > 0
            
            if updated:
                logger.warning(
                    f"Business {business_id}: "
                    f"website_status = archived (subscription ended)"
                )
            
            await self.db.flush()
            return updated
            
        except Exception as e:
            logger.error(f"Error marking archived: {str(e)}", exc_info=True)
            raise DatabaseException(f"Failed to update website status: {str(e)}")
    
    # ========================================================================
    # BATCH OPERATIONS
    # ========================================================================
    
    async def sync_from_campaign_event(
        self,
        business_id: UUID,
        event_type: str
    ) -> bool:
        """
        Sync business status based on campaign event.
        
        This is the PRIMARY method called by webhook handlers.
        
        Supported Events:
        - "sent" / "delivered": Mark as emailed/sms_sent
        - "opened": Mark as opened
        - "clicked": Mark as clicked
        - "replied": Mark as replied
        - "bounced": Mark as bounced
        - "unsubscribed" / "opted_out": Mark as unsubscribed
        
        Args:
            business_id: Business UUID
            event_type: Event type string
        
        Returns:
            True if status was updated
        """
        event_handlers = {
            "sent": lambda: self.mark_campaign_sent(business_id, "email"),
            "delivered": lambda: self.mark_campaign_sent(business_id, "sms"),
            "opened": lambda: self.mark_campaign_opened(business_id),
            "clicked": lambda: self.mark_link_clicked(business_id),
            "replied": lambda: self.mark_replied(business_id),
            "bounced": lambda: self.mark_bounced(business_id),
            "unsubscribed": lambda: self.mark_unsubscribed(business_id),
            "opted_out": lambda: self.mark_unsubscribed(business_id),
        }
        
        handler = event_handlers.get(event_type)
        if not handler:
            logger.warning(f"Unknown campaign event type: {event_type}")
            return False
        
        return await handler()
    
    async def sync_from_site_event(
        self,
        business_id: UUID,
        event_type: str
    ) -> bool:
        """
        Sync business status based on site generation event.
        
        Supported Events:
        - "generation_started": Mark as generating
        - "generation_completed": Mark as generated
        - "deployed": Mark as deployed
        - "purchased": Mark as sold (and contact purchased)
        - "cancelled": Mark as archived
        
        Args:
            business_id: Business UUID
            event_type: Event type string
        
        Returns:
            True if status was updated
        """
        event_handlers = {
            "generation_started": lambda: self.mark_website_generating(business_id),
            "generation_completed": lambda: self.mark_website_generated(business_id),
            "deployed": lambda: self.mark_website_deployed(business_id),
            "purchased": lambda: self.mark_website_sold(business_id),
            "cancelled": lambda: self.mark_website_archived(business_id),
        }
        
        handler = event_handlers.get(event_type)
        if not handler:
            logger.warning(f"Unknown site event type: {event_type}")
            return False
        
        return await handler()

