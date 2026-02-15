"""
Business (leads) model.
"""
from sqlalchemy import Column, String, Integer, Numeric, Text, DateTime, ForeignKey, Float, Boolean
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
    
    # Enhanced Website Detection (New in Migration 012)
    website_type = Column(String(20), default="none", nullable=True, index=True)
    # Values: website, booking, ordering, none
    
    website_confidence = Column(Float, nullable=True)
    # Confidence level of website detection (0.0-1.0)
    
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
    
    # Enhanced Business Data (New in Migration 012)
    verified = Column(Boolean, default=False, nullable=True, index=True)
    # Verified Google Business Profile
    
    operational = Column(Boolean, default=True, nullable=True, index=True)
    # Business operational status (from business_status field)
    
    business_status = Column(String(30), nullable=True)
    # Raw business status from Outscraper (OPERATIONAL, CLOSED_TEMPORARILY, etc)
    
    photos_count = Column(Integer, default=0, nullable=True)
    # Number of photos on Google Business Profile (engagement indicator)
    
    subtypes = Column(Text, nullable=True)
    # Additional business categories/services from Outscraper
    
    # Data Quality Scoring (New in Migration 012)
    quality_score = Column(Float, nullable=True, index=True)
    # Business quality score (0-100) based on verification, reviews, engagement, completeness
    
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
    
    # Website Validation (New in Migration 007, Extended in Migration 010)
    website_validation_status = Column(String(30), default="pending", nullable=True, index=True)
    # Values: pending, valid, invalid, no_website, error
    
    website_validation_result = Column(JSONB, nullable=True)
    # Stores full ValidationResult: status, url_type, accessibility, issues, quality_score, etc.
    
    website_validated_at = Column(DateTime, nullable=True)
    
    website_screenshot_url = Column(Text, nullable=True)
    # URL to website screenshot (if captured)
    
    discovered_urls = Column(JSONB, default=list, nullable=True)
    # URLs found in Google web results that weren't in the site field
    
    # Website Metadata (New in Migration 013)
    website_metadata = Column(JSONB, default=dict, nullable=True)
    # Complete validation history, discovery attempts, URL source tracking
    # Structure: {source, source_timestamp, validation_history[], discovery_attempts{}}
    
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
    generated_sites = relationship("GeneratedSite", back_populates="business", lazy="select")
    # campaigns = relationship("Campaign", back_populates="business")
    sms_messages = relationship("SMSMessage", back_populates="business", lazy="dynamic")
    
    def __repr__(self):
        return f"<Business {self.name} ({self.city}, {self.state})>"
    
    # ============================================================================
    # HELPER METHODS - Validation System
    # ============================================================================
    
    @property
    def url_source(self) -> str:
        """Get the source of the current website URL."""
        from core.validation_enums import URLSource
        if not self.website_metadata:
            return URLSource.NONE.value
        return self.website_metadata.get("source", URLSource.NONE.value)
    
    @property
    def has_valid_website(self) -> bool:
        """Check if business has a validated website."""
        from core.validation_enums import ValidationState
        return ValidationState.is_success_state(self.website_validation_status or "")
    
    @property
    def needs_discovery(self) -> bool:
        """Check if business needs website discovery."""
        from core.validation_enums import ValidationState
        return ValidationState.needs_discovery_action(self.website_validation_status or "")
    
    @property
    def validation_is_terminal(self) -> bool:
        """Check if validation is in a terminal state (no further action needed)."""
        from core.validation_enums import ValidationState
        return ValidationState.is_terminal_state(self.website_validation_status or "")
    
    def get_validation_history_count(self) -> int:
        """Get number of validation attempts."""
        if not self.website_metadata:
            return 0
        return len(self.website_metadata.get("validation_history", []))
    
    def get_discovery_attempt_count(self) -> int:
        """Get number of discovery attempts."""
        if not self.website_metadata:
            return 0
        return len(self.website_metadata.get("discovery_attempts", {}))
    
    def has_attempted_scrapingdog(self) -> bool:
        """Check if ScrapingDog discovery has been attempted."""
        if not self.website_metadata:
            return False
        attempts = self.website_metadata.get("discovery_attempts", {})
        return "scrapingdog" in attempts and attempts["scrapingdog"].get("attempted", False)
