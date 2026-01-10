"""
Coverage Grid model for tracking scraping territories.
"""
from sqlalchemy import Column, String, Integer, DateTime
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
    
    # Timing
    last_scraped_at = Column(DateTime, nullable=True)
    cooldown_until = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<CoverageGrid {self.city}, {self.state} - {self.industry} ({self.status})>"
    
    @property
    def location_key(self) -> str:
        """Generate unique location key."""
        return f"{self.country}:{self.state}:{self.city}"
    
    @property
    def full_key(self) -> str:
        """Generate unique coverage key."""
        return f"{self.country}:{self.state}:{self.city}:{self.industry}"
    
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
