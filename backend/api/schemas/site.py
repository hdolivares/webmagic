"""
Generated Site schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class SiteGenerateRequest(BaseModel):
    """Request to generate a new site."""
    business_id: UUID = Field(..., description="Business ID to generate site for")
    force_regenerate: bool = Field(default=False, description="Force regeneration if site exists")


class ManualGenerationRequest(BaseModel):
    """
    Request to generate a site from a free-form business description.

    The description is the primary required input. Claude interprets and expands
    it into a rich structured profile before the normal 4-stage pipeline runs.

    Hard facts (name, phone, email, address, city, state) are optional but, when
    provided, are used verbatim on the generated site — they are never overridden
    or embellished by the LLM.
    """

    # Primary narrative — required
    description: str = Field(
        ...,
        min_length=10,
        description="Free-form description of the business. The more detail, the better.",
    )

    # Hard facts — used exactly as entered
    name: Optional[str] = Field(None, description="Business name (verbatim)")
    phone: Optional[str] = Field(None, description="Contact phone (verbatim)")
    email: Optional[str] = Field(None, description="Contact email (verbatim)")
    address: Optional[str] = Field(None, description="Street address (verbatim)")
    city: Optional[str] = Field(None, description="City (verbatim)")
    state: Optional[str] = Field(None, description="State (verbatim)")

    # Website configuration
    website_type: Literal["informational", "ecommerce"] = Field(
        default="informational",
        description="Layout style — informational or ecommerce",
    )

    # Branding signals (all optional, any combination works)
    branding_notes: Optional[str] = Field(
        None,
        description="Color/style description, e.g. 'deep navy and gold, luxury minimal'",
    )
    branding_images: Optional[List[str]] = Field(
        None,
        description="Base64 data URIs of logo, brand photos, or any visual references",
    )


class SiteResponse(BaseModel):
    """Site response schema."""
    id: UUID
    business_id: UUID
    subdomain: str
    custom_domain: Optional[str]
    short_url: Optional[str]  # Pre-generated short link (e.g., https://lvsh.cc/abc123)
    status: str
    version: int
    deployed_at: Optional[datetime]
    sold_at: Optional[datetime]
    lighthouse_score: Optional[int]
    load_time_ms: Optional[int]
    screenshot_desktop_url: Optional[str]
    screenshot_mobile_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    full_url: str
    is_live: bool
    business: Optional[dict] = None  # Include business data
    
    class Config:
        from_attributes = True


class SiteDetailResponse(SiteResponse):
    """Detailed site response with content."""
    html_content: Optional[str] = None
    css_content: Optional[str] = None
    js_content: Optional[str] = None
    design_brief: Optional[Dict[str, Any]] = None
    assets_urls: List[str] = []


class SiteListResponse(BaseModel):
    """Paginated site list response."""
    sites: List[SiteResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SiteGenerationResult(BaseModel):
    """Result of site generation."""
    site_id: UUID
    status: str
    message: str
    duration_ms: Optional[float]
    summary: Optional[Dict[str, Any]]


class SiteUpdate(BaseModel):
    """Site update schema."""
    status: Optional[str] = Field(None, pattern="^(draft|preview|live|archived)$")
    custom_domain: Optional[str] = None
    lighthouse_score: Optional[int] = Field(None, ge=0, le=100)
    load_time_ms: Optional[int] = Field(None, ge=0)


class SiteStats(BaseModel):
    """Site statistics schema."""
    total_sites: int
    by_status: Dict[str, int]
    avg_lighthouse_score: Optional[float]
    avg_load_time_ms: Optional[float]
    total_live: int
    total_sold: int
