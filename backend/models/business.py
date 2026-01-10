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
    # Values: none, generating, generated, deployed, sold, archived
    
    contact_status = Column(String(30), default="pending", nullable=True, index=True)
    # Values: pending, emailed, opened, clicked, replied, purchased, unsubscribed, bounced
    
    qualification_score = Column(Integer, default=0, nullable=True)
    
    # Creative DNA (stored after AI generation)
    creative_dna = Column(JSONB, nullable=True)
    
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
    
    def __repr__(self):
        return f"<Business {self.name} ({self.city}, {self.state})>"
