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
    channel: str = Field(default="auto", pattern="^(auto|email|sms)$")
    variant: str = Field(default="friendly", pattern="^(friendly|professional|urgent)$")
    send_immediately: bool = Field(default=False, description="Send campaigns immediately after creation")
    scheduled_for: Optional[datetime] = Field(None, description="Schedule campaigns for specific time")


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


# ============================================================================
# NEW SCHEMAS FOR CAMPAIGN CREATION UI
# ============================================================================

class ReadyBusinessResponse(BaseModel):
    """Business ready for campaign with generated site."""
    id: UUID
    name: str
    category: Optional[str]
    city: Optional[str]
    state: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    qualification_score: Optional[int]
    site_id: UUID
    site_subdomain: str
    site_url: str
    site_created_at: datetime
    available_channels: List[str] = Field(description="Available contact channels: email, sms")
    recommended_channel: str = Field(description="Recommended channel based on available contact info")
    
    class Config:
        from_attributes = True


class ReadyBusinessesListResponse(BaseModel):
    """List of businesses ready for campaigns."""
    businesses: List[ReadyBusinessResponse]
    total: int
    with_email: int
    with_phone: int
    sms_only: int
    email_only: int


class SMSPreviewRequest(BaseModel):
    """Request SMS message preview."""
    business_id: UUID
    variant: str = Field(default="friendly", pattern="^(friendly|professional|urgent)$")


class SMSPreviewResponse(BaseModel):
    """SMS message preview."""
    business_id: UUID
    business_name: str
    sms_body: str
    character_count: int
    segment_count: int
    estimated_cost: float
    site_url: str
    variant: str


class BulkCampaignCreateResponse(BaseModel):
    """Response for bulk campaign creation."""
    status: str
    message: str
    total_queued: int
    by_channel: dict = Field(description="Count by channel (email, sms)")
    estimated_sms_cost: float = Field(description="Total estimated SMS cost")
    campaigns_created: List[UUID] = Field(default_factory=list, description="IDs of created campaigns")
