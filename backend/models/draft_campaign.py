"""
Draft Campaign Model

Stores scraping campaigns that are in "draft mode" - businesses have been
found and qualified, but no outreach has been sent yet. Allows for manual
review and approval before initiating contact.
"""
from sqlalchemy import Column, String, Integer, DateTime, func, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from models.base import BaseModel


class DraftCampaign(BaseModel):
    """
    Draft Campaign - Scraped businesses awaiting manual review/approval
    
    Workflow:
    1. User runs intelligent campaign in draft mode
    2. Businesses are scraped and qualified
    3. Draft campaign is created (status='pending_review')
    4. User reviews businesses and approves/rejects
    5. On approval, outreach messages are sent (status='approved')
    """
    __tablename__ = "draft_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    
    # Strategy reference
    strategy_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Location and category
    city = Column(String(100), nullable=False)
    state = Column(String(10), nullable=False)
    category = Column(String(100), nullable=False)
    
    # Zone information
    zone_id = Column(String(50), nullable=False)
    zone_lat = Column(String(20))
    zone_lon = Column(String(20))
    zone_radius_km = Column(String(10))
    
    # Results summary
    total_businesses_found = Column(Integer, nullable=False, default=0)
    qualified_leads_count = Column(Integer, nullable=False, default=0)
    qualification_rate = Column(Integer)  # Percentage
    
    # Business IDs (references to business table)
    business_ids = Column(JSON, nullable=False)  # List of UUIDs as strings
    
    # Status tracking
    status = Column(
        String(20), 
        nullable=False, 
        default='pending_review',
        index=True
    )
    # Status values: 'pending_review', 'approved', 'rejected', 'sent'
    
    # Review information
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    review_notes = Column(String(500))
    
    # Outreach tracking (after approval)
    messages_sent = Column(Integer, default=0)
    messages_failed = Column(Integer, default=0)
    sent_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return (
            f"<DraftCampaign {self.city}, {self.state} - {self.category} "
            f"({self.qualified_leads_count} leads, {self.status})>"
        )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "strategy_id": str(self.strategy_id),
            "city": self.city,
            "state": self.state,
            "category": self.category,
            "zone_id": self.zone_id,
            "zone_location": {
                "lat": self.zone_lat,
                "lon": self.zone_lon,
                "radius_km": self.zone_radius_km
            } if self.zone_lat else None,
            "total_businesses_found": self.total_businesses_found,
            "qualified_leads_count": self.qualified_leads_count,
            "qualification_rate": self.qualification_rate,
            "business_ids": self.business_ids,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "messages_sent": self.messages_sent,
            "messages_failed": self.messages_failed,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

