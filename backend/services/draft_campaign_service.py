"""
Draft Campaign Service

Handles the creation, review, and approval workflow for draft campaigns.
Provides a clean separation between scraping/discovery and outreach.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from datetime import datetime

from models.draft_campaign import DraftCampaign
from models.business import Business

logger = logging.getLogger(__name__)


class DraftCampaignService:
    """
    Service for managing draft campaigns.
    
    Draft campaigns represent scraped businesses that are awaiting manual
    review before outreach is initiated.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_draft_campaign(
        self,
        strategy_id: UUID,
        city: str,
        state: str,
        category: str,
        zone_id: str,
        zone_lat: Optional[float],
        zone_lon: Optional[float],
        zone_radius_km: Optional[float],
        business_ids: List[str],
        total_businesses_found: int,
        qualified_leads_count: int
    ) -> DraftCampaign:
        """
        Create a new draft campaign with scraped businesses.
        
        Args:
            strategy_id: UUID of the geo-strategy
            city: City name
            state: State code
            category: Business category
            zone_id: Zone identifier
            zone_lat: Zone latitude
            zone_lon: Zone longitude
            zone_radius_km: Zone radius in kilometers
            business_ids: List of business UUIDs as strings
            total_businesses_found: Total businesses found
            qualified_leads_count: Number of qualified leads
            
        Returns:
            Created DraftCampaign instance
        """
        qualification_rate = None
        if total_businesses_found > 0:
            qualification_rate = int((qualified_leads_count / total_businesses_found) * 100)
        
        draft_campaign = DraftCampaign(
            strategy_id=strategy_id,
            city=city,
            state=state,
            category=category,
            zone_id=zone_id,
            zone_lat=str(zone_lat) if zone_lat else None,
            zone_lon=str(zone_lon) if zone_lon else None,
            zone_radius_km=str(zone_radius_km) if zone_radius_km else None,
            business_ids=business_ids,
            total_businesses_found=total_businesses_found,
            qualified_leads_count=qualified_leads_count,
            qualification_rate=qualification_rate,
            status='pending_review'
        )
        
        self.db.add(draft_campaign)
        await self.db.commit()
        await self.db.refresh(draft_campaign)
        
        logger.info(
            f"Created draft campaign: {city}, {state} - {category} "
            f"({qualified_leads_count} leads in zone {zone_id})"
        )
        
        return draft_campaign
    
    async def get_pending_campaigns(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[DraftCampaign]:
        """
        Get pending draft campaigns awaiting review.
        
        Args:
            city: Filter by city (optional)
            state: Filter by state (optional)
            category: Filter by category (optional)
            limit: Maximum number of campaigns to return
            
        Returns:
            List of pending DraftCampaign instances
        """
        filters = [DraftCampaign.status == 'pending_review']
        
        if city:
            filters.append(DraftCampaign.city == city)
        if state:
            filters.append(DraftCampaign.state == state)
        if category:
            filters.append(DraftCampaign.category == category)
        
        stmt = (
            select(DraftCampaign)
            .where(and_(*filters))
            .order_by(desc(DraftCampaign.created_at))
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_campaign_by_id(self, campaign_id: UUID) -> Optional[DraftCampaign]:
        """Get a draft campaign by ID."""
        stmt = select(DraftCampaign).where(DraftCampaign.id == campaign_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_campaign_businesses(
        self,
        campaign_id: UUID
    ) -> List[Business]:
        """
        Get all businesses associated with a draft campaign.
        
        Args:
            campaign_id: UUID of the draft campaign
            
        Returns:
            List of Business instances
        """
        campaign = await self.get_campaign_by_id(campaign_id)
        if not campaign:
            return []
        
        if not campaign.business_ids:
            return []
        
        # Convert string UUIDs to UUID objects
        business_uuids = [UUID(bid) for bid in campaign.business_ids]
        
        stmt = select(Business).where(Business.id.in_(business_uuids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def approve_campaign(
        self,
        campaign_id: UUID,
        reviewed_by: str,
        review_notes: Optional[str] = None
    ) -> DraftCampaign:
        """
        Approve a draft campaign.
        
        This marks the campaign as approved and ready for outreach.
        Actual message sending should be triggered separately.
        
        Args:
            campaign_id: UUID of the draft campaign
            reviewed_by: Username/email of reviewer
            review_notes: Optional notes from reviewer
            
        Returns:
            Updated DraftCampaign instance
        """
        campaign = await self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        if campaign.status != 'pending_review':
            raise ValueError(f"Campaign is not pending review (status: {campaign.status})")
        
        campaign.status = 'approved'
        campaign.reviewed_by = reviewed_by
        campaign.reviewed_at = datetime.utcnow()
        campaign.review_notes = review_notes
        
        await self.db.commit()
        await self.db.refresh(campaign)
        
        logger.info(
            f"Approved draft campaign {campaign_id}: "
            f"{campaign.city}, {campaign.state} - {campaign.category} "
            f"({campaign.qualified_leads_count} leads)"
        )
        
        return campaign
    
    async def reject_campaign(
        self,
        campaign_id: UUID,
        reviewed_by: str,
        review_notes: Optional[str] = None
    ) -> DraftCampaign:
        """
        Reject a draft campaign.
        
        This marks the campaign as rejected. No outreach will be sent.
        
        Args:
            campaign_id: UUID of the draft campaign
            reviewed_by: Username/email of reviewer
            review_notes: Reason for rejection
            
        Returns:
            Updated DraftCampaign instance
        """
        campaign = await self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        if campaign.status != 'pending_review':
            raise ValueError(f"Campaign is not pending review (status: {campaign.status})")
        
        campaign.status = 'rejected'
        campaign.reviewed_by = reviewed_by
        campaign.reviewed_at = datetime.utcnow()
        campaign.review_notes = review_notes
        
        await self.db.commit()
        await self.db.refresh(campaign)
        
        logger.info(
            f"Rejected draft campaign {campaign_id}: "
            f"{campaign.city}, {campaign.state} - {campaign.category}"
        )
        
        return campaign
    
    async def mark_as_sent(
        self,
        campaign_id: UUID,
        messages_sent: int,
        messages_failed: int
    ) -> DraftCampaign:
        """
        Mark a draft campaign as sent after outreach is completed.
        
        Args:
            campaign_id: UUID of the draft campaign
            messages_sent: Number of messages successfully sent
            messages_failed: Number of messages that failed
            
        Returns:
            Updated DraftCampaign instance
        """
        campaign = await self.get_campaign_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        campaign.status = 'sent'
        campaign.messages_sent = messages_sent
        campaign.messages_failed = messages_failed
        campaign.sent_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(campaign)
        
        logger.info(
            f"Marked draft campaign {campaign_id} as sent: "
            f"{messages_sent} sent, {messages_failed} failed"
        )
        
        return campaign
    
    async def get_campaign_stats(self) -> Dict[str, Any]:
        """
        Get statistics about draft campaigns.
        
        Returns:
            Dictionary with campaign statistics
        """
        # Get counts by status
        stmt_pending = select(DraftCampaign).where(
            DraftCampaign.status == 'pending_review'
        )
        stmt_approved = select(DraftCampaign).where(
            DraftCampaign.status == 'approved'
        )
        stmt_sent = select(DraftCampaign).where(
            DraftCampaign.status == 'sent'
        )
        stmt_rejected = select(DraftCampaign).where(
            DraftCampaign.status == 'rejected'
        )
        
        pending_result = await self.db.execute(stmt_pending)
        approved_result = await self.db.execute(stmt_approved)
        sent_result = await self.db.execute(stmt_sent)
        rejected_result = await self.db.execute(stmt_rejected)
        
        pending_campaigns = list(pending_result.scalars().all())
        approved_campaigns = list(approved_result.scalars().all())
        sent_campaigns = list(sent_result.scalars().all())
        rejected_campaigns = list(rejected_result.scalars().all())
        
        total_pending_leads = sum(c.qualified_leads_count for c in pending_campaigns)
        total_approved_leads = sum(c.qualified_leads_count for c in approved_campaigns)
        total_sent_messages = sum(c.messages_sent or 0 for c in sent_campaigns)
        
        return {
            "pending_campaigns": len(pending_campaigns),
            "approved_campaigns": len(approved_campaigns),
            "sent_campaigns": len(sent_campaigns),
            "rejected_campaigns": len(rejected_campaigns),
            "total_campaigns": len(pending_campaigns) + len(approved_campaigns) + len(sent_campaigns) + len(rejected_campaigns),
            "total_pending_leads": total_pending_leads,
            "total_approved_leads": total_approved_leads,
            "total_sent_messages": total_sent_messages
        }

