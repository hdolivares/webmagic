"""
Coverage Grid schemas for API validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class CoverageBase(BaseModel):
    """Base coverage grid schema."""
    state: str = Field(..., min_length=2, max_length=50)
    city: str = Field(..., min_length=1, max_length=100)
    country: str = "US"
    industry: str = Field(..., min_length=1, max_length=100)
    industry_category: Optional[str] = None
    priority: int = Field(default=0, ge=0, le=100)
    population: Optional[int] = Field(None, ge=0)


class CoverageCreate(CoverageBase):
    """Schema for creating new coverage entry."""
    pass


class CoverageUpdate(BaseModel):
    """Schema for updating coverage entry (all optional)."""
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|cooldown)$")
    priority: Optional[int] = Field(None, ge=0, le=100)
    lead_count: Optional[int] = None
    qualified_count: Optional[int] = None
    site_count: Optional[int] = None
    conversion_count: Optional[int] = None


class CoverageResponse(CoverageBase):
    """Schema for coverage response."""
    id: UUID
    status: str
    lead_count: int
    qualified_count: int
    site_count: int
    conversion_count: int
    last_scraped_at: Optional[datetime]
    cooldown_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    conversion_rate: Optional[float] = None
    qualification_rate: Optional[float] = None
    
    class Config:
        from_attributes = True


class CoverageListResponse(BaseModel):
    """Schema for paginated coverage list."""
    coverage_entries: List[CoverageResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CoverageStats(BaseModel):
    """Coverage statistics schema."""
    total_territories: int
    pending: int
    in_progress: int
    completed: int
    cooldown: int
    total_leads: int
    total_qualified: int
    avg_qualification_rate: float
    by_state: dict
    by_industry: dict


class ScrapeRequest(BaseModel):
    """Schema for manual scrape request."""
    city: str = Field(..., min_length=1)
    state: str = Field(..., min_length=2, max_length=50)
    industry: str = Field(..., min_length=1)
    limit: int = Field(default=50, ge=1, le=100)
    country: str = "US"


class ScrapeResponse(BaseModel):
    """Schema for scrape response."""
    coverage_id: UUID
    status: str
    message: str
    estimated_results: Optional[int] = None
