"""
Generated Site schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class SiteGenerateRequest(BaseModel):
    """Request to generate a new site."""
    business_id: UUID = Field(..., description="Business ID to generate site for")
    force_regenerate: bool = Field(default=False, description="Force regeneration if site exists")


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
