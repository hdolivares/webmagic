"""
SMS Opt-Out Model for TCPA Compliance.

Tracks phone numbers that have opted out of SMS campaigns.
This is required by US TCPA regulations and SMS best practices.
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from models.base import BaseModel


class SMSOptOut(BaseModel):
    """
    SMS opt-out tracking for TCPA compliance.
    
    When a recipient replies "STOP" or opts out through any method,
    their phone number must be added to this table and we must never
    send them SMS again.
    
    Legal requirement: Must honor opt-outs immediately and permanently.
    """
    
    __tablename__ = "sms_opt_outs"
    
    # Phone number in E.164 format (e.g., +12345678900)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    
    # When they opted out
    opted_out_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # How they opted out
    source = Column(String(50), nullable=False)
    # Options: "reply_stop", "manual", "complaint", "admin"
    
    # Reference to the campaign they opted out from (if applicable)
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Optional notes about the opt-out
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<SMSOptOut {self.phone_number} ({self.source})>"
    
    @property
    def is_active(self) -> bool:
        """Check if opt-out is active (always True once opted out)."""
        return True  # Opt-outs are permanent

