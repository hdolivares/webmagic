"""
SMS Message Model - Stores all SMS messages for inbox functionality.

Tracks both inbound (received) and outbound (sent) messages.
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from models.base import BaseModel


class SMSMessage(BaseModel):
    """
    SMS message record for inbox functionality.
    
    Stores all SMS messages - both sent and received - to provide
    a complete conversation view in the admin dashboard.
    """
    
    __tablename__ = "sms_messages"
    
    # Relations (optional)
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    business_id = Column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Message details
    direction = Column(
        String(10),
        nullable=False,
        index=True
    )  # 'inbound' or 'outbound'
    
    from_phone = Column(String(20), nullable=False, index=True)
    to_phone = Column(String(20), nullable=False, index=True)
    body = Column(Text, nullable=False)
    
    # Status tracking
    status = Column(String(20), nullable=False, default="pending", index=True)
    # inbound: received
    # outbound: pending, queued, sent, delivered, failed
    
    # Provider tracking
    telnyx_message_id = Column(String(255), nullable=True, index=True)
    
    # Cost tracking (for outbound)
    segments = Column(Integer, default=1)
    cost = Column(Numeric(10, 4), nullable=True)
    
    # Error tracking
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    received_at = Column(DateTime(timezone=True), nullable=True)  # Inbound
    sent_at = Column(DateTime(timezone=True), nullable=True)      # Outbound
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="sms_messages", lazy="selectin")
    business = relationship("Business", back_populates="sms_messages", lazy="selectin")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="check_sms_message_direction"
        ),
    )
    
    def __repr__(self):
        return f"<SMSMessage {self.direction} {self.from_phone} -> {self.to_phone}>"
    
    @property
    def is_inbound(self) -> bool:
        """Check if message is inbound (received from business)."""
        return self.direction == "inbound"
    
    @property
    def is_outbound(self) -> bool:
        """Check if message is outbound (sent to business)."""
        return self.direction == "outbound"
    
    @property
    def is_opt_out(self) -> bool:
        """Check if message is a STOP/opt-out request."""
        if not self.is_inbound:
            return False
        
        stop_keywords = ["stop", "unsubscribe", "cancel", "end", "quit", "optout"]
        body_lower = self.body.strip().lower()
        return any(kw in body_lower for kw in stop_keywords)
    
    @property
    def preview(self) -> str:
        """Get truncated preview of message body."""
        if len(self.body) <= 50:
            return self.body
        return self.body[:47] + "..."
    
    @classmethod
    def create_outbound(
        cls,
        to_phone: str,
        from_phone: str,
        body: str,
        campaign_id=None,
        business_id=None,
        telnyx_message_id=None
    ) -> "SMSMessage":
        """Create an outbound message record."""
        return cls(
            direction="outbound",
            from_phone=from_phone,
            to_phone=to_phone,
            body=body,
            campaign_id=campaign_id,
            business_id=business_id,
            telnyx_message_id=telnyx_message_id,
            status="pending",
            sent_at=datetime.utcnow()
        )
    
    @classmethod
    def create_inbound(
        cls,
        from_phone: str,
        to_phone: str,
        body: str,
        campaign_id=None,
        business_id=None,
        telnyx_message_id=None
    ) -> "SMSMessage":
        """Create an inbound message record."""
        return cls(
            direction="inbound",
            from_phone=from_phone,
            to_phone=to_phone,
            body=body,
            campaign_id=campaign_id,
            business_id=business_id,
            telnyx_message_id=telnyx_message_id,
            status="received",
            received_at=datetime.utcnow()
        )

