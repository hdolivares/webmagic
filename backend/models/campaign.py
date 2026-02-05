"""
Campaign model for multi-channel outreach tracking (email + SMS).
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Campaign(BaseModel):
    """
    Multi-channel campaign model for tracking outreach.
    
    Supports email, SMS, and future channels (WhatsApp, voice, etc.)
    """
    
    __tablename__ = "campaigns"
    
    # Relationships
    business_id = Column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generated_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Multi-Channel Support
    channel = Column(String(20), default="email", nullable=False, index=True)
    # Options: "email", "sms", "whatsapp", "voice"
    
    # Email Content (optional - only for email campaigns)
    subject_line = Column(Text, nullable=True)  # Was required, now optional
    email_body = Column(Text, nullable=True)  # Was required, now optional
    preview_text = Column(String(200), nullable=True)
    review_highlight = Column(Text, nullable=True)
    
    # SMS Content (optional - only for SMS campaigns)
    sms_body = Column(Text, nullable=True)
    sms_provider = Column(String(50), nullable=True)  # "twilio", "messagebird"
    sms_sid = Column(String(255), nullable=True, index=True)  # Provider message ID
    sms_segments = Column(Integer, nullable=True)  # Number of SMS segments
    sms_cost = Column(Numeric(10, 4), nullable=True)  # Actual cost in USD
    
    # Recipient Info
    business_name = Column(String(255), nullable=True)
    recipient_name = Column(String(255), nullable=True)
    recipient_email = Column(String(255), nullable=True, index=True)  # Now optional
    recipient_phone = Column(String(20), nullable=True, index=True)  # New
    
    # Status: pending, scheduled, sent, delivered, opened, clicked, replied, converted, bounced, failed
    status = Column(String(30), default="pending", nullable=False, index=True)
    
    # Tracking
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    opened_count = Column(Integer, default=0, nullable=False)
    clicked_at = Column(DateTime, nullable=True)
    clicked_count = Column(Integer, default=0, nullable=False)
    replied_at = Column(DateTime, nullable=True)
    converted_at = Column(DateTime, nullable=True)
    
    # Email Provider Data
    email_provider = Column(String(50), nullable=True)  # ses, sendgrid
    message_id = Column(String(255), nullable=True, index=True)
    
    # Variant Testing
    variant = Column(String(50), nullable=True)
    
    # Error Handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Scheduling
    scheduled_for = Column(DateTime, nullable=True, index=True)
    
    # Relationships
    sms_messages = relationship("SMSMessage", back_populates="campaign", lazy="dynamic")
    
    def __repr__(self):
        recipient = self.recipient_email or self.recipient_phone or "N/A"
        return f"<Campaign {self.channel} to {recipient} ({self.status})>"
    
    @property
    def is_delivered(self) -> bool:
        """Check if campaign was delivered."""
        return self.status in ["delivered", "opened", "clicked", "replied", "converted"]
    
    @property
    def is_engaged(self) -> bool:
        """Check if recipient engaged (opened, clicked, or replied)."""
        return self.status in ["opened", "clicked", "replied", "converted"]
    
    @property
    def open_rate(self) -> float:
        """Calculate open rate (1 if opened, 0 if not). Only for email."""
        if self.channel != "email":
            return 0.0
        return 1.0 if self.opened_at else 0.0
    
    @property
    def click_rate(self) -> float:
        """Calculate click rate (1 if clicked, 0 if not)."""
        return 1.0 if self.clicked_at else 0.0
    
    @property
    def is_sms(self) -> bool:
        """Check if this is an SMS campaign."""
        return self.channel == "sms"
    
    @property
    def is_email(self) -> bool:
        """Check if this is an email campaign."""
        return self.channel == "email"
    
    @property
    def cost_per_message(self) -> float:
        """Get cost per message (0 for email, actual cost for SMS)."""
        if self.channel == "sms" and self.sms_cost:
            return float(self.sms_cost)
        return 0.0
