"""
Business (Lead) schemas for API validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class BusinessBase(BaseModel):
    """Base business schema with common fields."""
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: str = "US"
    category: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: Optional[int] = Field(None, ge=0)


class BusinessCreate(BusinessBase):
    """Schema for creating a new business."""
    gmb_id: Optional[str] = None
    slug: str = Field(..., min_length=1, max_length=255)
    photos_urls: List[str] = []


class BusinessUpdate(BaseModel):
    """Schema for updating a business (all fields optional)."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website_url: Optional[str] = None
    website_status: Optional[str] = None
    contact_status: Optional[str] = None
    qualification_score: Optional[int] = None
    review_highlight: Optional[str] = None
    brand_archetype: Optional[str] = None


class BusinessResponse(BusinessBase):
    """Schema for business response."""
    id: UUID
    slug: str
    gmb_id: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    reviews_summary: Optional[str]
    review_highlight: Optional[str]
    brand_archetype: Optional[str]
    photos_urls: List[str] = []
    logo_url: Optional[str]
    website_status: str
    contact_status: str
    qualification_score: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BusinessListResponse(BaseModel):
    """Schema for paginated business list."""
    businesses: List[BusinessResponse]
    total: int
    page: int
    page_size: int
    pages: int


class BusinessStats(BaseModel):
    """Business statistics schema."""
    total_leads: int
    qualified_leads: int
    with_email: int
    without_website: int
    high_rating: int
    by_status: dict
    by_category: dict
