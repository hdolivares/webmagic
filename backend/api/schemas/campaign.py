"""
Campaign schemas for API validation.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


def _coerce_optional_str(v: Any) -> Optional[str]:
    """Coerce value to str or None for optional string fields (ORM may return non-str)."""
    if v is None:
        return None
    return str(v) if not isinstance(v, str) else v


def _coerce_optional_float(v: Any) -> Optional[float]:
    """Coerce value to float or None (e.g. Decimal from DB)."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class CampaignCreate(BaseModel):
    """Create new campaign."""
    business_id: UUID
    site_id: Optional[UUID] = None
    variant: str = Field(default="default", pattern="^(default|direct|story|value)$")
    scheduled_for: Optional[datetime] = None


class CampaignResponse(BaseModel):
    """Campaign response schema (supports email + SMS campaigns)."""
    id: UUID
    business_id: UUID
    site_id: Optional[UUID] = None
    channel: str = "email"
    # Email-only fields (None for SMS campaigns)
    subject_line: Optional[str] = None
    preview_text: Optional[str] = None
    recipient_email: Optional[str] = None
    # SMS-only fields (None for email campaigns)
    recipient_phone: Optional[str] = None
    sms_body: Optional[str] = None
    sms_cost: Optional[float] = None
    # Common fields
    business_name: Optional[str] = None
    recipient_name: Optional[str] = None
    status: str
    variant: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    opened_count: int = 0
    clicked_at: Optional[datetime] = None
    clicked_count: int = 0
    replied_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    email_provider: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime
    is_delivered: bool
    is_engaged: bool

    class Config:
        from_attributes = True

    # Coerce optional string/numeric fields from ORM (e.g. None, Decimal, non-str) to avoid ValidationError
    @field_validator(
        "recipient_email",
        "recipient_phone",
        "subject_line",
        "preview_text",
        "business_name",
        "recipient_name",
        "sms_body",
        "variant",
        "email_provider",
        "error_message",
        mode="before",
    )
    @classmethod
    def coerce_optional_str_fields(cls, v: Any) -> Optional[str]:
        return _coerce_optional_str(v)

    @field_validator("sms_cost", mode="before")
    @classmethod
    def coerce_sms_cost(cls, v: Any) -> Optional[float]:
        return _coerce_optional_float(v)


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
    business_ids: List[UUID] = Field(..., min_length=1, max_length=100)
    channel: str = Field(default="auto", pattern="^(auto|email|sms)$")
    variant: str = Field(default="friendly", pattern="^(friendly|professional|urgent)$")
    send_immediately: bool = Field(default=False, description="Send campaigns immediately after creation")
    scheduled_for: Optional[datetime] = Field(None, description="Schedule campaigns for specific time")


class EmailTestRequest(BaseModel):
    """Test email request."""
    to_email: EmailStr
    subject: str = "Test Email from WebMagic"


class SMSTestRequest(BaseModel):
    """Test SMS request."""
    to_phone: str = Field(..., description="Recipient phone in E.164 or local format (e.g. +15551234567)")
    message: str = Field(
        default="Hi! This is a test message from Lavish Solutions / WebMagic. If you received this, SMS is working correctly.",
        description="Message body to send"
    )


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
    """Business ready for campaign with generated site (used internally; /ready-businesses returns plain JSON)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    category: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    qualification_score: Optional[int] = None
    site_id: UUID
    site_subdomain: str
    site_url: str
    site_created_at: datetime
    available_channels: List[str] = Field(default_factory=list, description="Available contact channels: email, sms")
    recommended_channel: str = Field(description="Recommended channel based on available contact info")


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
