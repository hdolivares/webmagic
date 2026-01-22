"""
Business Enrichment Service

Computes CRM indicators and metadata for business records.
Enriches responses with campaign history, contact indicators, and data quality metrics.

Author: WebMagic Team
Date: January 22, 2026
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from uuid import UUID
from datetime import datetime

from models.business import Business
from models.campaign import Campaign
from models.site import GeneratedSite
from core.config import get_settings

settings = get_settings()


class BusinessEnrichmentService:
    """
    Service for enriching business data with CRM indicators.
    
    Computes:
    - Contact data availability (has_email, has_phone)
    - Contact status indicators (was_contacted, bounced, etc.)
    - Campaign summary (total_campaigns, last_contact_date)
    - Site summary (has_site, site_url)
    - Data quality metrics (data_completeness)
    - Human-readable status labels and colors
    """
    
    # Status label mapping
    STATUS_LABELS = {
        "pending": "New Lead",
        "emailed": "Contacted (Email)",
        "sms_sent": "Contacted (SMS)",
        "opened": "Opened Email",
        "clicked": "Clicked Link",
        "replied": "Replied",
        "purchased": "Customer",
        "unsubscribed": "Unsubscribed",
        "bounced": "Bounced"
    }
    
    # Status color mapping (for frontend badges)
    STATUS_COLORS = {
        "pending": "gray",
        "emailed": "blue",
        "sms_sent": "purple",
        "opened": "cyan",
        "clicked": "indigo",
        "replied": "green",
        "purchased": "gold",
        "unsubscribed": "black",
        "bounced": "red"
    }
    
    def __init__(self, db: AsyncSession):
        """
        Initialize enrichment service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def enrich_business(
        self,
        business: Business,
        include_campaign_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Enrich a single business with all CRM indicators.
        
        Args:
            business: Business instance
            include_campaign_summary: Whether to fetch campaign data (slower)
        
        Returns:
            Dictionary with all enriched fields
        """
        # Base business data
        enriched = {
            # Contact data indicators
            "has_email": business.email is not None and len(business.email) > 0,
            "has_phone": business.phone is not None and len(business.phone) > 0,
            
            # Contact status indicators
            "was_contacted": business.contact_status != "pending",
            "contacted_via_email": business.contact_status in [
                "emailed", "opened", "clicked"
            ],
            "contacted_via_sms": business.contact_status == "sms_sent",
            "contact_bounced": business.contact_status == "bounced",
            "is_unsubscribed": business.contact_status == "unsubscribed",
            "is_customer": business.contact_status == "purchased",
            
            # Site summary (computed)
            "has_generated_site": business.website_status != "none",
            
            # Data quality
            "data_completeness": self._calculate_data_completeness(business),
            
            # Human-readable status
            "status_label": self.STATUS_LABELS.get(
                business.contact_status,
                "Unknown"
            ),
            "status_color": self.STATUS_COLORS.get(
                business.contact_status,
                "gray"
            ),
        }
        
        # Fetch campaign summary if requested
        if include_campaign_summary:
            campaign_data = await self._get_campaign_summary(business.id)
            enriched.update(campaign_data)
        else:
            # Default values
            enriched.update({
                "total_campaigns": 0,
                "last_contact_date": None,
                "last_contact_channel": None
            })
        
        # Fetch site URL if site exists
        if enriched["has_generated_site"]:
            site_url = await self._get_site_url(business.id)
            enriched["site_url"] = site_url
        else:
            enriched["site_url"] = None
        
        return enriched
    
    async def _get_campaign_summary(
        self,
        business_id: UUID
    ) -> Dict[str, Any]:
        """
        Get campaign summary for a business.
        
        Args:
            business_id: Business UUID
        
        Returns:
            Dict with total_campaigns, last_contact_date, last_contact_channel
        """
        # Get total campaigns count
        count_result = await self.db.execute(
            select(func.count(Campaign.id))
            .where(Campaign.business_id == business_id)
        )
        total_campaigns = count_result.scalar() or 0
        
        # Get most recent campaign
        last_campaign_result = await self.db.execute(
            select(Campaign)
            .where(Campaign.business_id == business_id)
            .where(Campaign.sent_at.isnot(None))
            .order_by(desc(Campaign.sent_at))
            .limit(1)
        )
        last_campaign = last_campaign_result.scalar_one_or_none()
        
        if last_campaign:
            return {
                "total_campaigns": total_campaigns,
                "last_contact_date": last_campaign.sent_at,
                "last_contact_channel": last_campaign.channel
            }
        else:
            return {
                "total_campaigns": total_campaigns,
                "last_contact_date": None,
                "last_contact_channel": None
            }
    
    async def _get_site_url(self, business_id: UUID) -> Optional[str]:
        """
        Get site URL for a business.
        
        Args:
            business_id: Business UUID
        
        Returns:
            Site URL if exists, None otherwise
        """
        result = await self.db.execute(
            select(GeneratedSite.subdomain)
            .where(GeneratedSite.business_id == business_id)
            .where(GeneratedSite.status == "live")
            .limit(1)
        )
        subdomain = result.scalar_one_or_none()
        
        if subdomain:
            # Build site URL based on settings
            if hasattr(settings, 'SITES_BASE_URL'):
                return f"{settings.SITES_BASE_URL}/{subdomain}"
            else:
                return f"https://{subdomain}.webmagic.com"
        
        return None
    
    def _calculate_data_completeness(self, business: Business) -> int:
        """
        Calculate how complete a business record is (0-100%).
        
        Scoring:
        - Email: 30 points
        - Phone: 30 points
        - Address: 10 points
        - City/State: 10 points
        - Category: 10 points
        - Rating/Reviews: 10 points
        
        Args:
            business: Business instance
        
        Returns:
            Completeness score (0-100)
        """
        score = 0
        
        if business.email:
            score += 30
        if business.phone:
            score += 30
        if business.address:
            score += 10
        if business.city and business.state:
            score += 10
        if business.category:
            score += 10
        if business.rating and business.review_count and business.review_count > 0:
            score += 10
        
        return score
    
    async def enrich_businesses_bulk(
        self,
        businesses: list[Business],
        include_campaign_summary: bool = False
    ) -> list[Dict[str, Any]]:
        """
        Enrich multiple businesses (optimized for list views).
        
        For bulk operations, campaign summaries are optional to avoid
        N+1 query issues. Set include_campaign_summary=True if needed.
        
        Args:
            businesses: List of Business instances
            include_campaign_summary: Whether to include campaign data
        
        Returns:
            List of enriched business dictionaries
        """
        enriched_list = []
        
        for business in businesses:
            enriched = await self.enrich_business(
                business,
                include_campaign_summary=include_campaign_summary
            )
            enriched_list.append(enriched)
        
        return enriched_list

