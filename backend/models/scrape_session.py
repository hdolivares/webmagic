"""
Scrape Session Model.

Purpose:
    Tracks the lifecycle and progress of scraping operations.
    Enables real-time progress monitoring and status queries.

Best Practices:
    - Separation of Concerns: Model handles data structure only
    - Business logic belongs in services/
    - Type hints for IDE support
    - Clear documentation
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from core.database import Base


class ScrapeSession(Base):
    """
    Scrape session model for tracking scraping operations.
    
    Lifecycle:
        queued → scraping → validating → completed
                                       ↘ failed
                                       ↘ cancelled
    
    Usage:
        session = ScrapeSession(
            zone_id="la_losangeles",
            strategy_id=strategy_id,
            status="queued"
        )
        db.add(session)
        db.commit()
    """
    
    __tablename__ = "scrape_sessions"
    
    # =========================================================================
    # PRIMARY FIELDS
    # =========================================================================
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique session identifier"
    )
    
    zone_id = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Geographic zone being scraped"
    )
    
    strategy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("geo_strategies.id", ondelete="SET NULL"),
        index=True,
        comment="Associated scraping strategy"
    )
    
    # =========================================================================
    # STATUS TRACKING
    # =========================================================================
    
    status = Column(
        String(50),
        nullable=False,
        default="queued",
        index=True,
        comment="Current session status"
    )
    
    # =========================================================================
    # PROGRESS METRICS
    # =========================================================================
    
    total_businesses = Column(
        Integer,
        default=0,
        comment="Total businesses expected to scrape"
    )
    
    scraped_businesses = Column(
        Integer,
        default=0,
        comment="Businesses successfully scraped"
    )
    
    validated_businesses = Column(
        Integer,
        default=0,
        comment="Businesses with validated URLs"
    )
    
    discovered_businesses = Column(
        Integer,
        default=0,
        comment="Businesses with URLs discovered via ScrapingDog"
    )
    
    # =========================================================================
    # TIMESTAMPS
    # =========================================================================
    
    started_at = Column(
        DateTime,
        nullable=True,
        comment="When scraping actually started"
    )
    
    completed_at = Column(
        DateTime,
        nullable=True,
        comment="When scraping completed (success or failure)"
    )
    
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True,
        comment="When session was created"
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Last update timestamp"
    )
    
    # =========================================================================
    # ERROR TRACKING
    # =========================================================================
    
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if status is 'failed'"
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    
    meta = Column(
        "metadata",  # DB column name - using 'meta' in Python to avoid SQLAlchemy reserved name
        JSONB,
        default=dict,
        comment="Flexible metadata for future extensions"
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    
    strategy = relationship(
        "GeoStrategy",
        back_populates="scrape_sessions",
        lazy="joined"
    )
    
    # =========================================================================
    # COMPUTED PROPERTIES
    # =========================================================================
    
    @property
    def progress_percentage(self) -> float:
        """
        Calculate scraping progress percentage.
        
        Returns:
            Progress as percentage (0-100)
        """
        if self.total_businesses == 0:
            return 0.0
        return round(
            (self.scraped_businesses / self.total_businesses) * 100,
            1
        )
    
    @property
    def validation_percentage(self) -> float:
        """
        Calculate validation progress percentage.
        
        Returns:
            Validation progress as percentage (0-100)
        """
        if self.scraped_businesses == 0:
            return 0.0
        return round(
            (self.validated_businesses / self.scraped_businesses) * 100,
            1
        )
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """
        Calculate duration of scraping operation.
        
        Returns:
            Duration in seconds, or None if not started
        """
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        delta = end_time - self.started_at
        return int(delta.total_seconds())
    
    @property
    def is_active(self) -> bool:
        """Check if session is actively scraping."""
        return self.status in ("queued", "scraping", "validating")
    
    @property
    def is_completed(self) -> bool:
        """Check if session has finished (success or failure)."""
        return self.status in ("completed", "failed", "cancelled")
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session to dictionary for API responses.
        
        Returns:
            Dictionary representation of session
        """
        return {
            "id": str(self.id),
            "zone_id": self.zone_id,
            "strategy_id": str(self.strategy_id) if self.strategy_id else None,
            "status": self.status,
            "progress": {
                "total": self.total_businesses,
                "scraped": self.scraped_businesses,
                "validated": self.validated_businesses,
                "discovered": self.discovered_businesses,
                "scrape_percentage": self.progress_percentage,
                "validation_percentage": self.validation_percentage
            },
            "timestamps": {
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "duration_seconds": self.duration_seconds
            },
            "error": self.error_message,
            "metadata": self.meta
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ScrapeSession("
            f"id={self.id}, "
            f"zone={self.zone_id}, "
            f"status={self.status}, "
            f"progress={self.scraped_businesses}/{self.total_businesses}"
            f")>"
        )
