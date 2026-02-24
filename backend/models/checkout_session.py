"""
Checkout Session Model

Tracks checkout initiation, completion, and abandoned cart recovery.

This model enables:
- Complete purchase funnel tracking
- Abandoned cart detection and recovery emails
- Conversion rate analytics
- Customer behavior insights

Author: WebMagic Team
Date: February 14, 2026
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Index, Text
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from typing import Optional
import uuid

from core.database import Base


class CheckoutSession(Base):
    """
    Checkout session tracking for abandoned cart recovery.
    
    Lifecycle:
    1. **initiated**: User clicks "Claim This Site" and enters email/name
    2. **checkout_created**: Recurrente checkout created and URL generated
    3. **payment_pending**: User clicked checkout URL (tracked by Recurrente)
    4. **completed**: Payment successful
    5. **abandoned**: No completion within abandonment window (15+ minutes)
    
    Abandoned Cart Recovery:
    - Celery task checks for sessions in "checkout_created" status > 15 mins old
    - Sends recovery email with 10% discount code
    - Marks reminder_sent_at to prevent duplicates
    """
    
    __tablename__ = "checkout_sessions"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Unique session identifier
    session_id = Column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True,
        default=lambda: f"cs_{uuid.uuid4().hex}"
    )
    
    # Customer Information
    customer_email = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    
    # Site Information
    site_slug = Column(String(255), nullable=False, index=True)
    site_id = Column(PGUUID(as_uuid=True), nullable=True)  # FK to sites table (UUID type)
    
    # Recurrente Details
    checkout_id = Column(String(255), nullable=True, index=True)
    checkout_url = Column(String(500), nullable=True)
    
    # Pricing
    purchase_amount = Column(Numeric(10, 2), nullable=False)
    monthly_amount = Column(Numeric(10, 2), nullable=False)
    
    # Status Tracking
    status = Column(
        String(50), 
        nullable=False, 
        default='initiated',
        index=True
    )
    payment_intent_id = Column(String(255), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Abandoned Cart Recovery
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True, index=True)
    reminder_discount_code = Column(String(100), nullable=True)
    recurrente_coupon_id = Column(String(255), nullable=True, index=True)
    
    # Analytics Metadata
    user_agent = Column(String(500), nullable=True)
    referrer = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_checkout_sessions_email_status', 'customer_email', 'status'),
        Index('idx_checkout_sessions_created_status', 'created_at', 'status'),
        Index('idx_checkout_sessions_abandoned', 'created_at', 'status', 'reminder_sent_at'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<CheckoutSession("
            f"id={self.id}, "
            f"session_id={self.session_id}, "
            f"email={self.customer_email}, "
            f"status={self.status}, "
            f"site={self.site_slug})>"
        )
    
    @property
    def is_abandoned(self) -> bool:
        """Check if this session is abandoned (not completed after 15 minutes)."""
        from datetime import datetime, timedelta, timezone as dt_timezone
        
        if self.status == 'completed':
            return False
        
        if self.status != 'checkout_created':
            return False
        
        abandonment_threshold = datetime.now(dt_timezone.utc) - timedelta(minutes=15)
        return self.created_at < abandonment_threshold
    
    @property
    def can_send_reminder(self) -> bool:
        """Check if we can send an abandoned cart reminder."""
        return self.is_abandoned and self.reminder_sent_at is None
