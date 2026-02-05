"""
BusinessFilterPreset Model - User-defined filter combinations for business queries.

Allows users to save and reuse complex filter combinations for efficient
business discovery and management.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from models.base import BaseModel


class BusinessFilterPreset(BaseModel):
    """
    Saved filter preset for business queries.
    
    Allows users to save complex filter combinations with custom names
    for quick reuse. Tracks usage statistics for popular presets.
    """
    __tablename__ = "business_filter_presets"
    
    # Owner
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Preset details
    name = Column(String(100), nullable=False)
    """User-defined name for the preset (e.g., "LA Plumbers Without Websites")"""
    
    description = Column(Text, nullable=True)
    """Optional description of what this filter does"""
    
    is_public = Column(Integer, default=0, nullable=False, index=True)
    """Whether this preset is shared with all users (1) or private (0)"""
    
    # Filter criteria
    filters = Column(JSONB, nullable=False)
    """
    JSON object containing filter criteria:
    {
      "website_status": ["none", "invalid"],
      "has_website": false,
      "min_rating": 4.0,
      "location": {"state": "CA", "city": "Los Angeles"},
      "categories": ["plumbers", "electricians"],
      "min_review_count": 10,
      "min_qualification_score": 70,
      "scraped_after": "2026-01-01"
    }
    """
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True, index=True)
    """Last time this preset was used"""
    
    use_count = Column(Integer, default=0, nullable=False, index=True)
    """Number of times this preset has been used"""
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='business_filter_presets_user_name_unique'),
    )
    
    # Relationships
    # user = relationship("AdminUser", back_populates="filter_presets")
    
    def __repr__(self):
        return f"<BusinessFilterPreset name='{self.name}' user_id={self.user_id} uses={self.use_count}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "description": self.description,
            "is_public": bool(self.is_public),
            "filters": self.filters,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "use_count": self.use_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def mark_used(self):
        """Mark this preset as used (increment counter and update timestamp)."""
        self.use_count += 1
        self.last_used_at = datetime.utcnow()
    
    @property
    def is_popular(self) -> bool:
        """Check if this is a frequently used preset (10+ uses)."""
        return self.use_count >= 10
    
    @property
    def filter_count(self) -> int:
        """Count how many filter criteria are set."""
        if not self.filters:
            return 0
        return len([v for v in self.filters.values() if v is not None and v != "" and v != []])

