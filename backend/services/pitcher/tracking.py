"""
Email tracking service for opens and clicks.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
from datetime import datetime
import logging
import secrets

from models.campaign import Campaign
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailTracker:
    """
    Email tracking service.
    Generates tracking pixels and links, records opens/clicks.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.base_url = "https://track.webmagic.com"  # TODO: Configure this
    
    def generate_tracking_pixel_url(self, campaign_id: UUID) -> str:
        """
        Generate tracking pixel URL for email opens.
        
        Args:
            campaign_id: Campaign UUID
            
        Returns:
            Tracking pixel URL
        """
        # Create a 1x1 transparent pixel URL with campaign ID
        return f"{self.base_url}/pixel/{campaign_id}.png"
    
    def generate_tracking_link(
        self,
        campaign_id: UUID,
        destination_url: str,
        link_id: Optional[str] = None
    ) -> str:
        """
        Generate tracking link for click tracking.
        
        Args:
            campaign_id: Campaign UUID
            destination_url: Original destination URL
            link_id: Optional identifier for the link (e.g., "cta", "website")
            
        Returns:
            Tracking link URL
        """
        # Generate short token for the link
        token = secrets.token_urlsafe(8)
        link_id_param = f"&link={link_id}" if link_id else ""
        
        return f"{self.base_url}/click/{campaign_id}?token={token}{link_id_param}"
    
    async def record_open(
        self,
        campaign_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Record email open event.
        
        Args:
            campaign_id: Campaign UUID
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            True if recorded successfully
        """
        try:
            # Get campaign
            result = await self.db.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()
            
            if not campaign:
                logger.warning(f"Campaign not found: {campaign_id}")
                return False
            
            # Update campaign
            now = datetime.utcnow()
            updates = {
                "opened_count": campaign.opened_count + 1,
                "updated_at": now
            }
            
            # Set opened_at on first open
            if not campaign.opened_at:
                updates["opened_at"] = now
                updates["status"] = "opened"
            
            await self.db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(**updates)
            )
            await self.db.commit()
            
            logger.info(f"Recorded open for campaign: {campaign_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to record open: {str(e)}")
            return False
    
    async def record_click(
        self,
        campaign_id: UUID,
        link_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Record email click event.
        
        Args:
            campaign_id: Campaign UUID
            link_id: Link identifier (e.g., "cta", "website")
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            True if recorded successfully
        """
        try:
            # Get campaign
            result = await self.db.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()
            
            if not campaign:
                logger.warning(f"Campaign not found: {campaign_id}")
                return False
            
            # Update campaign
            now = datetime.utcnow()
            updates = {
                "clicked_count": campaign.clicked_count + 1,
                "updated_at": now
            }
            
            # Set clicked_at on first click
            if not campaign.clicked_at:
                updates["clicked_at"] = now
                updates["status"] = "clicked"
            
            # Also record as opened if not already
            if not campaign.opened_at:
                updates["opened_at"] = now
                updates["opened_count"] = 1
            
            await self.db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(**updates)
            )
            await self.db.commit()
            
            logger.info(f"Recorded click for campaign: {campaign_id} (link: {link_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to record click: {str(e)}")
            return False
    
    async def record_reply(self, campaign_id: UUID) -> bool:
        """
        Record email reply event.
        
        Args:
            campaign_id: Campaign UUID
            
        Returns:
            True if recorded successfully
        """
        try:
            await self.db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(
                    replied_at=datetime.utcnow(),
                    status="replied",
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            logger.info(f"Recorded reply for campaign: {campaign_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to record reply: {str(e)}")
            return False
    
    async def record_conversion(self, campaign_id: UUID) -> bool:
        """
        Record conversion event (e.g., payment, signup).
        
        Args:
            campaign_id: Campaign UUID
            
        Returns:
            True if recorded successfully
        """
        try:
            await self.db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(
                    converted_at=datetime.utcnow(),
                    status="converted",
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            logger.info(f"Recorded conversion for campaign: {campaign_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to record conversion: {str(e)}")
            return False
    
    async def record_bounce(
        self,
        campaign_id: UUID,
        bounce_type: str = "hard",
        reason: Optional[str] = None
    ) -> bool:
        """
        Record email bounce event.
        
        Args:
            campaign_id: Campaign UUID
            bounce_type: "hard" or "soft"
            reason: Bounce reason message
            
        Returns:
            True if recorded successfully
        """
        try:
            await self.db.execute(
                update(Campaign)
                .where(Campaign.id == campaign_id)
                .values(
                    status="bounced",
                    error_message=f"{bounce_type} bounce: {reason}",
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.commit()
            
            logger.info(f"Recorded {bounce_type} bounce for campaign: {campaign_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to record bounce: {str(e)}")
            return False
