"""
Coverage Grid model for tracking scraping territories.
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from models.base import BaseModel


class CoverageGrid(BaseModel):
    """
    Coverage grid model for tracking which locations/industries
    have been scraped and their status.
    """
    
    __tablename__ = "coverage_grid"
    
    # Location
    state = Column(String(50), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    country = Column(String(50), default="US", nullable=False)
    
    # Geo-Grid Zone (for subdivided cities)
    zone_id = Column(String(50), nullable=True, index=True)  # Increased from 20 to 50 for metro areas
    zone_lat = Column(String(20), nullable=True)  # Center latitude of zone
    zone_lon = Column(String(20), nullable=True)  # Center longitude of zone
    zone_radius_km = Column(String(10), nullable=True)  # Search radius for this zone
    
    # Industry
    industry = Column(String(100), nullable=False, index=True)
    industry_category = Column(String(100), nullable=True)
    
    # Status: pending, in_progress, completed, cooldown
    status = Column(String(20), default="pending", nullable=False, index=True)
    
    # Priority for targeting (higher = more important)
    priority = Column(Integer, default=0, nullable=False, index=True)
    
    # Population (for prioritization)
    population = Column(Integer, nullable=True)
    
    # Metrics
    lead_count = Column(Integer, default=0, nullable=False)
    qualified_count = Column(Integer, default=0, nullable=False)
    site_count = Column(Integer, default=0, nullable=False)
    conversion_count = Column(Integer, default=0, nullable=False)
    
    # Detailed Website Metrics (New in Migration 008)
    businesses_with_websites = Column(Integer, default=0, nullable=False)
    businesses_without_websites = Column(Integer, default=0, nullable=False)
    invalid_websites = Column(Integer, default=0, nullable=False)
    websites_generated = Column(Integer, default=0, nullable=False)
    generation_in_progress = Column(Integer, default=0, nullable=False)
    generation_failed = Column(Integer, default=0, nullable=False)
    
    # Validation Metrics (New in Migration 008)
    validation_completed_count = Column(Integer, default=0, nullable=False)
    validation_pending_count = Column(Integer, default=0, nullable=False)
    
    # Zone Performance Metrics (New in Migration 008)
    avg_qualification_score = Column(Numeric(5, 2), nullable=True)
    avg_rating = Column(Numeric(2, 1), nullable=True)
    
    # Last Scrape Details - persistent storage (New in Migration 008)
    last_scrape_details = Column(JSONB, nullable=True)
    # Stores: raw_businesses, qualified_leads, new_businesses, existing_businesses,
    #         with_websites, without_websites, invalid_websites, timestamp
    
    # Pagination & Continuation Support
    scrape_count = Column(Integer, default=0, nullable=False)
    scrape_offset = Column(Integer, default=0, nullable=False)
    has_more_results = Column(Boolean, default=True, nullable=False)
    max_results_available = Column(Integer, nullable=True)
    last_scrape_size = Column(Integer, nullable=True)
    estimated_businesses = Column(Integer, nullable=True)
    
    # Timing
    last_scraped_at = Column(DateTime, nullable=True)
    cooldown_until = Column(DateTime, nullable=True)
    next_scheduled = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        zone_str = f" Zone {self.zone_id}" if self.zone_id else ""
        return f"<CoverageGrid {self.city}, {self.state}{zone_str} - {self.industry} ({self.status})>"
    
    @property
    def location_key(self) -> str:
        """Generate unique location key."""
        return f"{self.country}:{self.state}:{self.city}"
    
    @property
    def full_key(self) -> str:
        """Generate unique coverage key."""
        zone_suffix = f":{self.zone_id}" if self.zone_id else ""
        return f"{self.country}:{self.state}:{self.city}:{self.industry}{zone_suffix}"
    
    @property
    def conversion_rate(self) -> float:
        """Calculate conversion rate (sites → customers)."""
        if self.site_count == 0:
            return 0.0
        return (self.conversion_count / self.site_count) * 100
    
    @property
    def qualification_rate(self) -> float:
        """Calculate qualification rate (leads → qualified)."""
        if self.lead_count == 0:
            return 0.0
        return (self.qualified_count / self.lead_count) * 100
