"""
Campaign management service.
Orchestrates email generation, sending, and tracking.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from uuid import UUID
from datetime import datetime, timedelta
import logging

from models.campaign import Campaign
from models.business import Business
from models.site import GeneratedSite
from services.pitcher.email_generator import EmailGenerator
from services.pitcher.email_sender import EmailSender
from services.pitcher.tracking import EmailTracker
from core.exceptions import DatabaseException, ValidationException

logger = logging.getLogger(__name__)


class CampaignService:
    """
    Campaign management service.
    Handles creation, sending, and tracking of email campaigns.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_generator = EmailGenerator()
        self.email_sender = EmailSender()
        self.tracker = EmailTracker(db)
    
    async def create_campaign(
        self,
        business_id: UUID,
        site_id: Optional[UUID] = None,
        variant: str = "default",
        scheduled_for: Optional[datetime] = None
    ) -> Campaign:
        """
        Create a new email campaign for a business.
        
        Args:
            business_id: Business UUID
            site_id: Optional generated site UUID
            variant: Email variant (default, direct, story, value)
            scheduled_for: Optional schedule time
            
        Returns:
            Created Campaign instance
        """
        logger.info(f"Creating campaign for business: {business_id}")
        
        # Get business
        business_result = await self.db.execute(
            select(Business).where(Business.id == business_id)
        )
        business = business_result.scalar_one_or_none()
        
        if not business:
            raise ValidationException(f"Business not found: {business_id}")
        
        if not business.email:
            raise ValidationException(f"Business has no email: {business.name}")
        
        # Get site if provided
        site_url = None
        if site_id:
            site_result = await self.db.execute(
                select(GeneratedSite).where(GeneratedSite.id == site_id)
            )
            site = site_result.scalar_one_or_none()
            if site:
                site_url = site.full_url
        
        # Prepare business data for email generation
        business_data = {
            "name": business.name,
            "category": business.category,
            "city": business.city,
            "state": business.state,
            "rating": float(business.rating) if business.rating else 0,
            "review_count": business.review_count
        }
        
        # Generate email
        email = await self.email_generator.generate_email(
            business_data=business_data,
            site_url=site_url,
            review_highlight=business.review_highlight,
            variant=variant
        )
        
        # Create campaign
        campaign = Campaign(
            business_id=business_id,
            site_id=site_id,
            subject_line=email["subject_line"],
            email_body=email["email_body"],
            preview_text=email.get("preview_text"),
            review_highlight=business.review_highlight,
            business_name=business.name,
            recipient_email=business.email,
            variant=variant,
            scheduled_for=scheduled_for,
            status="scheduled" if scheduled_for else "pending"
        )
        
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        
        logger.info(f"Campaign created: {campaign.id}")
        return campaign
    
    async def send_campaign(self, campaign_id: UUID) -> bool:
        """
        Send an email campaign.
        
        Args:
            campaign_id: Campaign UUID
            
        Returns:
            True if sent successfully
        """
        logger.info(f"Sending campaign: {campaign_id}")
        
        # Get campaign
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            raise ValidationException(f"Campaign not found: {campaign_id}")
        
        if campaign.status not in ["pending", "scheduled"]:
            raise ValidationException(f"Campaign already sent or invalid status: {campaign.status}")
        
        try:
            # Generate tracking pixel
            tracking_pixel = self.tracker.generate_tracking_pixel_url(campaign_id)
            
            # Convert to HTML
            body_html = self.email_sender.generate_html_from_text(campaign.email_body)
            
            # Send email
            send_result = await self.email_sender.send_campaign_email(
                to_email=campaign.recipient_email,
                subject=campaign.subject_line,
                body_text=campaign.email_body,
                body_html=body_html,
                tracking_pixel=tracking_pixel
            )
            
            # Update campaign
            await self.db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(
                    status="sent",
                    sent_at=datetime.utcnow(),
                    email_provider=send_result.get("provider"),
                    message_id=send_result.get("message_id"),
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            logger.info(f"Campaign sent successfully: {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send campaign: {str(e)}")
            
            # Update campaign with error
            await self.db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(
                    status="failed",
                    error_message=str(e),
                    retry_count=campaign.retry_count + 1,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            return False
    
    async def get_campaign(self, campaign_id: UUID) -> Optional[Campaign]:
        """Get campaign by ID."""
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()
    
    async def list_campaigns(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        business_id: Optional[UUID] = None
    ) -> tuple[List[Campaign], int]:
        """List campaigns with pagination."""
        query = select(Campaign)
        count_query = select(func.count(Campaign.id))
        
        conditions = []
        if status:
            conditions.append(Campaign.status == status)
        if business_id:
            conditions.append(Campaign.business_id == business_id)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        query = query.order_by(Campaign.created_at.desc())
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        campaigns = result.scalars().all()
        
        return list(campaigns), total
    
    async def get_pending_campaigns(self, limit: int = 10) -> List[Campaign]:
        """
        Get campaigns ready to be sent.
        Includes pending and scheduled campaigns whose time has come.
        
        Args:
            limit: Maximum number of campaigns to return
            
        Returns:
            List of Campaign instances
        """
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(Campaign)
            .where(
                or_(
                    Campaign.status == "pending",
                    and_(
                        Campaign.status == "scheduled",
                        Campaign.scheduled_for <= now
                    )
                )
            )
            .order_by(Campaign.scheduled_for.asc().nullsfirst())
            .limit(limit)
        )
        
        return list(result.scalars().all())
    
    async def bulk_create_campaigns(
        self,
        business_ids: List[UUID],
        variant: str = "default"
    ) -> List[Campaign]:
        """
        Create campaigns for multiple businesses.
        
        Args:
            business_ids: List of business UUIDs
            variant: Email variant
            
        Returns:
            List of created campaigns
        """
        campaigns = []
        
        for business_id in business_ids:
            try:
                campaign = await self.create_campaign(
                    business_id=business_id,
                    variant=variant
                )
                campaigns.append(campaign)
            except Exception as e:
                logger.warning(f"Failed to create campaign for {business_id}: {str(e)}")
                continue
        
        await self.db.commit()
        logger.info(f"Created {len(campaigns)} campaigns")
        
        return campaigns
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get campaign statistics."""
        # Total campaigns
        total_result = await self.db.execute(
            select(func.count(Campaign.id))
        )
        total = total_result.scalar()
        
        # By status
        by_status = {}
        status_result = await self.db.execute(
            select(Campaign.status, func.count(Campaign.id))
            .group_by(Campaign.status)
        )
        for status, count in status_result:
            by_status[status] = count
        
        # Sent in last 24h
        yesterday = datetime.utcnow() - timedelta(days=1)
        sent_24h_result = await self.db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.sent_at >= yesterday)
        )
        sent_24h = sent_24h_result.scalar()
        
        # Open rate
        opened_result = await self.db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.opened_at.isnot(None))
        )
        opened = opened_result.scalar()
        
        sent_count = by_status.get("sent", 0) + by_status.get("delivered", 0) + by_status.get("opened", 0) + by_status.get("clicked", 0)
        open_rate = (opened / sent_count * 100) if sent_count > 0 else 0
        
        # Click rate
        clicked_result = await self.db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.clicked_at.isnot(None))
        )
        clicked = clicked_result.scalar()
        click_rate = (clicked / sent_count * 100) if sent_count > 0 else 0
        
        # Reply rate
        replied_result = await self.db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.replied_at.isnot(None))
        )
        replied = replied_result.scalar()
        reply_rate = (replied / sent_count * 100) if sent_count > 0 else 0
        
        return {
            "total_campaigns": total,
            "by_status": by_status,
            "sent_24h": sent_24h,
            "total_sent": sent_count,
            "total_opened": opened,
            "total_clicked": clicked,
            "total_replied": replied,
            "open_rate": round(open_rate, 2),
            "click_rate": round(click_rate, 2),
            "reply_rate": round(reply_rate, 2)
        }


from sqlalchemy import or_
