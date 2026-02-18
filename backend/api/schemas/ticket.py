"""
Support Ticket API Schemas

Pydantic models for ticket management API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime


class ElementContextSchema(BaseModel):
    """
    Snapshot of a DOM element captured by the visual element picker.
    Attached to site_edit tickets to give the AI pipeline a precise target.
    """
    css_selector: str
    tag: str
    id: Optional[str] = None
    classes: List[str] = []
    text_content: str = ""
    html: str = ""
    dom_path: str = ""
    computed_styles: Dict[str, Any] = {}
    bounding_box: Dict[str, Any] = {}
    captured_at: Optional[str] = None


class TicketCreateRequest(BaseModel):
    """Request schema for creating a new ticket."""

    subject: str = Field(..., min_length=5, max_length=255, description="Ticket subject")
    description: str = Field(..., min_length=10, description="Detailed description of the issue")
    category: str = Field(
        ...,
        description="Ticket category (billing, technical_support, site_edit, question, other)",
    )
    site_id: Optional[UUID] = Field(None, description="Optional site ID if ticket is site-specific")
    element_context: Optional[List[ElementContextSchema]] = Field(
        None,
        description=(
            "Ordered list of DOM element snapshots from the visual element picker "
            "(maximum 3). Only meaningful for site_edit tickets."
        ),
    )


class TicketMessageCreate(BaseModel):
    """Request schema for adding a message to a ticket."""
    
    message: str = Field(..., min_length=1, description="Message content")


class TicketStatusUpdate(BaseModel):
    """Request schema for updating ticket status."""
    
    status: str = Field(..., description="New status (new, in_progress, waiting_customer, waiting_ai, resolved, closed)")


class TicketMessageResponse(BaseModel):
    """Response schema for a ticket message."""
    
    id: UUID
    ticket_id: UUID
    customer_user_id: Optional[UUID] = None
    admin_user_id: Optional[UUID] = None
    message: str
    message_type: str
    ai_generated: bool = False
    ai_model: Optional[str] = None
    ai_confidence: Optional[Dict[str, Any]] = None
    internal_only: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    """Response schema for a support ticket."""
    
    id: UUID
    customer_user_id: UUID
    site_id: Optional[UUID] = None
    ticket_number: str
    subject: str
    description: str
    category: str
    priority: str
    status: str
    ai_processed: bool = False
    ai_category_confidence: Optional[Dict[str, Any]] = None
    ai_suggested_response: Optional[str] = None
    ai_processing_notes: Optional[Dict[str, Any]] = None
    assigned_to_admin_id: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    last_customer_message_at: Optional[datetime] = None
    last_staff_message_at: Optional[datetime] = None
    customer_satisfaction_rating: Optional[str] = None
    internal_notes: Optional[str] = None
    tags: Optional[List[str]] = None
    element_context: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    messages: List[TicketMessageResponse] = []
    
    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    """Response schema for ticket list."""
    
    tickets: List[TicketResponse]
    total: int
    limit: int
    offset: int


class TicketStatsResponse(BaseModel):
    """Response schema for ticket statistics."""
    
    total: int
    by_status: Dict[str, int]
    by_category: Dict[str, int]
    open: int
    waiting: int
    resolved: int
    closed: int


class TicketCategoriesResponse(BaseModel):
    """Response schema for available ticket categories."""
    
    categories: List[str]
    descriptions: Dict[str, str]


class MessageResponse(BaseModel):
    """Generic message response."""
    
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

