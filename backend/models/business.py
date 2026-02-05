"""
Business (leads) model.
"""
from sqlalchemy import Column, String, Integer, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from models.base import BaseModel


class Business(BaseModel):
    """Business/lead model for scraped GMB data."""
    
    __tablename__ = "businesses"
    
    # External IDs
    gmb_id = Column(String(100), unique=True, nullable=True, index=True)
    gmb_place_id = Column(String(100), nullable=True)
    
    # Basic Info
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    
    # Contact
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    website_url = Column(String(500), nullable=True)
    
    # Location
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(50), nullable=True, index=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(50), default="US", nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    
    # GMB Data
    category = Column(String(100), nullable=True, index=True)
    subcategory = Column(String(100), nullable=True)
    rating = Column(Numeric(2, 1), nullable=True, index=True)
    review_count = Column(Integer, default=0, nullable=True)
    
    # Extracted Data (from AI analysis)
    reviews_summary = Column(Text, nullable=True)
    review_highlight = Column(Text, nullable=True)
    brand_archetype = Column(String(50), nullable=True)
    
    # Photos
    photos_urls = Column(JSONB, default=[], nullable=True)
    logo_url = Column(Text, nullable=True)
    
    # Processing Status
    website_status = Column(String(30), default="none", nullable=True, index=True)
    # Values: none, queued, generating, generated, deployed, sold, archived
    
    contact_status = Column(String(30), default="pending", nullable=True, index=True)
    # Values: pending, emailed, opened, clicked, replied, purchased, unsubscribed, bounced
    
    qualification_score = Column(Integer, default=0, nullable=True)
    
    # Website Validation (New in Migration 007)
    website_validation_status = Column(String(30), default="pending", nullable=True, index=True)
    # Values: pending, valid, invalid, missing, timeout
    
    website_validation_result = Column(JSONB, nullable=True)
    # Stores full ValidationResult: status, url_type, accessibility, issues, etc.
    
    website_validated_at = Column(DateTime, nullable=True)
    
    discovered_urls = Column(JSONB, default=list, nullable=True)
    # URLs found in Google web results that weren't in the site field
    
    # Website Generation Queue Tracking (New in Migration 007)
    generation_queued_at = Column(DateTime, nullable=True)
    generation_started_at = Column(DateTime, nullable=True)
    generation_completed_at = Column(DateTime, nullable=True)
    generation_attempts = Column(Integer, default=0, nullable=True)
    
    # Creative DNA (stored after AI generation)
    creative_dna = Column(JSONB, nullable=True)
    
    # Raw Data Storage (for reprocessing without wasting API credits)
    raw_data = Column(JSONB, nullable=True)
    # Stores full Outscraper response for data recovery and debugging
    
    # Tracking
    coverage_grid_id = Column(
        UUID(as_uuid=True),
        ForeignKey("coverage_grid.id", ondelete="SET NULL"),
        nullable=True
    )
    
    scraped_at = Column(DateTime, nullable=True)
    
    # Relationships
    # coverage_grid = relationship("CoverageGrid", back_populates="businesses")
    # generated_sites = relationship("GeneratedSite", back_populates="business")
    # campaigns = relationship("Campaign", back_populates="business")
    sms_messages = relationship("SMSMessage", back_populates="business", lazy="dynamic")
    
    def __repr__(self):
        return f"<Business {self.name} ({self.city}, {self.state})>"
