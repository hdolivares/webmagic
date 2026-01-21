"""
Support Ticket Models

Support tickets for customer service requests handled by AI and staff.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from models.base import BaseModel


class SupportTicket(BaseModel):
    """
    Support ticket model for customer service requests.
    
    Tickets are categorized and can be handled by AI or staff.
    """
    
    __tablename__ = "support_tickets"
    
    # Customer relationship
    customer_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Site relationship (optional - ticket might be about account/billing)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Ticket identification
    ticket_number = Column(String(20), unique=True, nullable=False, index=True)
    
    # Content
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Category: billing, technical_support, site_edit, question, other
    category = Column(String(50), nullable=False, index=True)
    
    # Priority: low, medium, high, urgent (set by AI based on content)
    priority = Column(String(20), default="medium", nullable=False, index=True)
    
    # Status: new, in_progress, waiting_customer, waiting_ai, resolved, closed
    status = Column(String(30), default="new", nullable=False, index=True)
    
    # AI handling
    ai_processed = Column(Boolean, default=False)
    ai_category_confidence = Column(JSONB, nullable=True)  # Store AI confidence scores
    ai_suggested_response = Column(Text, nullable=True)
    ai_processing_notes = Column(JSONB, nullable=True)
    
    # Assignment
    assigned_to_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    last_customer_message_at = Column(DateTime(timezone=True), nullable=True)
    last_staff_message_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    customer_satisfaction_rating = Column(String(20), nullable=True)  # satisfied, neutral, unsatisfied
    internal_notes = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True)  # Flexible tagging system
    
    # Relationships
    customer_user = relationship("CustomerUser", back_populates="support_tickets")
    site = relationship("Site", back_populates="support_tickets")
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_support_tickets_status_created', 'status', 'created_at'),
        Index('idx_support_tickets_category_status', 'category', 'status'),
        Index('idx_support_tickets_customer_status', 'customer_user_id', 'status'),
    )
    
    def __repr__(self):
        return f"<SupportTicket {self.ticket_number} - {self.category} ({self.status})>"


class TicketMessage(BaseModel):
    """
    Messages within a support ticket conversation.
    """
    
    __tablename__ = "ticket_messages"
    
    # Ticket relationship
    ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Author (either customer or staff)
    # If customer_user_id is set, message is from customer
    # If admin_user_id is set, message is from staff
    # If ai_generated is True, message is from AI
    customer_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    admin_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Content
    message = Column(Text, nullable=False)
    
    # Message type: customer, staff, ai, system
    message_type = Column(String(20), nullable=False, index=True)
    
    # AI metadata
    ai_generated = Column(Boolean, default=False)
    ai_model = Column(String(50), nullable=True)
    ai_confidence = Column(JSONB, nullable=True)
    
    # Attachments (future enhancement)
    attachments = Column(JSONB, nullable=True)
    
    # Visibility
    internal_only = Column(Boolean, default=False)  # Hidden from customer
    
    # Relationships
    ticket = relationship("SupportTicket", back_populates="messages")
    customer_user = relationship("CustomerUser")
    admin_user = relationship("AdminUser")
    
    # Indexes
    __table_args__ = (
        Index('idx_ticket_messages_ticket_created', 'ticket_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<TicketMessage {self.message_type} - Ticket {self.ticket_id}>"


class TicketTemplate(BaseModel):
    """
    Predefined templates for common responses.
    """
    
    __tablename__ = "ticket_templates"
    
    # Template identification
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False, index=True)
    
    # Content
    subject_template = Column(String(255), nullable=True)
    message_template = Column(Text, nullable=False)
    
    # Usage
    is_active = Column(Boolean, default=True)
    usage_count = Column(JSONB, default=0)
    
    # Creator
    created_by_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    def __repr__(self):
        return f"<TicketTemplate {self.name} - {self.category}>"

