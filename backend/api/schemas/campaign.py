"""
Campaign schemas for API validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class CampaignCreate(BaseModel):
    """Create new campaign."""
    business_id: UUID
    site_id: Optional[UUID] = None
    variant: str = Field(default="default", pattern="^(default|direct|story|value)$")
    scheduled_for: Optional[datetime] = None


class CampaignResponse(BaseModel):
    """Campaign response schema."""
    id: UUID
    business_id: UUID
    site_id: Optional[UUID]
    subject_line: str
    preview_text: Optional[str]
    recipient_email: str
    business_name: Optional[str]
    status: str
    variant: Optional[str]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    opened_at: Optional[datetime]
    opened_count: int
    clicked_at: Optional[datetime]
    clicked_count: int
    replied_at: Optional[datetime]
    converted_at: Optional[datetime]
    email_provider: Optional[str]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime
    is_delivered: bool
    is_engaged: bool
    
    class Config:
        from_attributes = True


class CampaignDetailResponse(CampaignResponse):
    """Detailed campaign response with email body."""
    email_body: str
    review_highlight: Optional[str]
    message_id: Optional[str]


class CampaignListResponse(BaseModel):
    """Paginated campaign list."""
    campaigns: List[CampaignResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CampaignStats(BaseModel):
    """Campaign statistics."""
    total_campaigns: int
    by_status: dict
    sent_24h: int
    total_sent: int
    total_opened: int
    total_clicked: int
    total_replied: int
    open_rate: float
    click_rate: float
    reply_rate: float


class BulkCampaignCreate(BaseModel):
    """Create campaigns for multiple businesses."""
    business_ids: List[UUID] = Field(..., min_items=1, max_items=100)
    variant: str = Field(default="default", pattern="^(default|direct|story|value)$")


class EmailTestRequest(BaseModel):
    """Test email request."""
    to_email: EmailStr
    subject: str = "Test Email from WebMagic"


class TrackingEvent(BaseModel):
    """Tracking event (for webhooks)."""
    campaign_id: UUID
    event_type: str = Field(..., pattern="^(open|click|reply|bounce|conversion)$")
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    link_id: Optional[str] = None
