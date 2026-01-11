"""
Campaign model for email outreach tracking.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from models.base import BaseModel


class Campaign(BaseModel):
    """
    Email campaign model for tracking outreach.
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
    
    # Email Content
    subject_line = Column(Text, nullable=False)
    email_body = Column(Text, nullable=False)
    preview_text = Column(String(200), nullable=True)
    review_highlight = Column(Text, nullable=True)
    
    # Recipient Info
    business_name = Column(String(255), nullable=True)
    recipient_name = Column(String(255), nullable=True)
    recipient_email = Column(String(255), nullable=False, index=True)
    
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
    
    def __repr__(self):
        return f"<Campaign {self.recipient_email} ({self.status})>"
    
    @property
    def is_delivered(self) -> bool:
        """Check if email was delivered."""
        return self.status in ["delivered", "opened", "clicked", "replied", "converted"]
    
    @property
    def is_engaged(self) -> bool:
        """Check if recipient engaged (opened or clicked)."""
        return self.status in ["opened", "clicked", "replied", "converted"]
    
    @property
    def open_rate(self) -> float:
        """Calculate open rate (1 if opened, 0 if not)."""
        return 1.0 if self.opened_at else 0.0
    
    @property
    def click_rate(self) -> float:
        """Calculate click rate (1 if clicked, 0 if not)."""
        return 1.0 if self.clicked_at else 0.0
