"""
Edit Request API Schemas

Pydantic models for AI-powered site edit requests.
Follows best practices with clear validation and documentation.

Author: WebMagic Team
Date: January 21, 2026
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# REQUEST SCHEMAS (Input)
# ============================================================================

class EditRequestCreate(BaseModel):
    """
    Schema for creating a new edit request.
    
    Example:
        {
            "request_text": "Change the header background to blue",
            "request_type": "style",
            "target_section": "hero"
        }
    """
    request_text: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Natural language description of the edit",
        examples=["Change the hero button color to blue"]
    )
    request_type: Optional[str] = Field(
        None,
        description="Type of edit: text, style, layout, content, image",
        examples=["style"]
    )
    target_section: Optional[str] = Field(
        None,
        description="Specific section to edit: hero, about, services, contact",
        examples=["hero"]
    )
    
    @field_validator("request_type")
    @classmethod
    def validate_request_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate request type is one of the allowed values."""
        if v is None:
            return v
        
        allowed_types = ["text", "style", "layout", "content", "image"]
        if v.lower() not in allowed_types:
            raise ValueError(
                f"request_type must be one of: {', '.join(allowed_types)}"
            )
        return v.lower()
    
    @field_validator("target_section")
    @classmethod
    def validate_target_section(cls, v: Optional[str]) -> Optional[str]:
        """Validate target section is reasonable."""
        if v is None:
            return v
        
        # Common sections - can be expanded
        allowed_sections = [
            "hero", "about", "services", "contact", "footer",
            "header", "navigation", "testimonials", "pricing", "faq"
        ]
        if v.lower() not in allowed_sections:
            # Don't fail, just normalize
            return v.lower()
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_text": "Make the call-to-action button larger and change it to green",
                "request_type": "style",
                "target_section": "hero"
            }
        }


class EditRequestUpdate(BaseModel):
    """
    Schema for updating an edit request.
    Used for internal updates during processing.
    """
    status: Optional[str] = Field(None, description="New status")
    ai_interpretation: Optional[Dict[str, Any]] = Field(None, description="AI analysis")
    ai_confidence: Optional[Decimal] = Field(None, ge=0.0, le=1.0)
    changes_made: Optional[Dict[str, Any]] = Field(None, description="Changes applied")


class EditRequestApproval(BaseModel):
    """
    Schema for customer approval/rejection of edit preview.
    
    Example:
        {
            "approved": true,
            "feedback": "Looks great!"
        }
    """
    approved: bool = Field(..., description="Whether customer approves the changes")
    feedback: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional feedback from customer"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "approved": True,
                "feedback": "Perfect! Exactly what I wanted."
            }
        }


# ============================================================================
# RESPONSE SCHEMAS (Output)
# ============================================================================

class EditRequestResponse(BaseModel):
    """
    Complete edit request response with all details.
    """
    id: UUID
    site_id: UUID
    request_text: str
    request_type: Optional[str]
    target_section: Optional[str]
    status: str
    
    # AI Processing
    ai_interpretation: Optional[Dict[str, Any]] = None
    ai_confidence: Optional[Decimal] = None
    changes_made: Optional[Dict[str, Any]] = None
    
    # Preview
    preview_version_id: Optional[UUID] = None
    preview_url: Optional[str] = None
    
    # Approval
    customer_approved: Optional[bool] = None
    customer_feedback: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    
    # Deployment
    deployed_version_id: Optional[UUID] = None
    deployed_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EditRequestSummary(BaseModel):
    """
    Lightweight edit request summary for lists.
    """
    id: UUID
    site_id: UUID
    request_text: str
    request_type: Optional[str]
    status: str
    preview_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class EditRequestList(BaseModel):
    """
    Paginated list of edit requests.
    """
    items: List[EditRequestSummary]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


# ============================================================================
# STATUS UPDATE SCHEMAS
# ============================================================================

class EditRequestStatusUpdate(BaseModel):
    """
    Status update notification for real-time updates.
    """
    id: UUID
    status: str
    message: str
    progress_percent: Optional[int] = Field(None, ge=0, le=100)
    estimated_completion: Optional[datetime] = None


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class EditRequestStats(BaseModel):
    """
    Statistics about edit requests for a site.
    """
    total_requests: int = 0
    pending_requests: int = 0
    approved_requests: int = 0
    rejected_requests: int = 0
    deployed_requests: int = 0
    average_approval_time_minutes: Optional[float] = None
    average_processing_time_seconds: Optional[float] = None
    most_common_request_type: Optional[str] = None

