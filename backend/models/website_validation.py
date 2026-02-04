"""
WebsiteValidation Model - Audit trail of website URL validation attempts.

Tracks validation results for business websites including accessibility checks,
URL type detection, and discovered alternative URLs from web results.
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from models.base import BaseModel


class WebsiteValidation(BaseModel):
    """
    Website URL validation audit record.
    
    Each record represents a validation attempt for a business's website URL,
    storing detailed results including accessibility, detected issues, and
    alternative URLs discovered from Google web results.
    """
    __tablename__ = "website_validations"
    
    # Foreign key to business
    business_id = Column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Validation input
    url_tested = Column(String(500), nullable=True)
    """The URL that was tested (may be None if business had no website)"""
    
    # Validation results
    status = Column(String(30), nullable=False, index=True)
    """Overall validation status: valid, invalid, missing, timeout, needs_generation"""
    
    url_type = Column(String(30), nullable=True)
    """Type of URL detected: html, pdf, image, redirect, archive, invalid, other"""
    
    accessibility = Column(String(30), nullable=False)
    """Accessibility status: accessible, inaccessible, timeout, not_checked"""
    
    http_status_code = Column(Integer, nullable=True)
    """HTTP status code returned (200, 404, 500, etc.)"""
    
    response_time_ms = Column(Integer, nullable=True)
    """Response time in milliseconds"""
    
    # Issues found
    issues = Column(JSONB, default=list, nullable=False)
    """
    Array of issue identifiers detected during validation:
    ["redirects_to_pdf", "certificate_error", "timeout", "404_not_found", "suspicious_domain"]
    """
    
    # Web results discovered
    web_results_urls = Column(JSONB, default=list, nullable=False)
    """
    URLs discovered in Google web results that weren't in the site field.
    Useful for finding hidden websites that businesses didn't add to their GMB listing.
    """
    
    recommended_url = Column(String(500), nullable=True)
    """
    Best URL to use based on validation results.
    May differ from url_tested if web results found a better alternative.
    """
    
    recommendation = Column(String(30), nullable=False, index=True)
    """Action recommendation: keep, replace, generate"""
    
    # Metadata
    validation_method = Column(String(50), nullable=True)
    """Method used for validation: http_head, http_get, external_api, cached"""
    
    validator_version = Column(String(20), default="1.0", nullable=False)
    """Version of the validation service used"""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    """Timestamp when validation was performed"""
    
    # Relationships
    # business = relationship("Business", back_populates="website_validations")
    
    def __repr__(self):
        return f"<WebsiteValidation business_id={self.business_id} status={self.status} url={self.url_tested}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "business_id": str(self.business_id),
            "url_tested": self.url_tested,
            "status": self.status,
            "url_type": self.url_type,
            "accessibility": self.accessibility,
            "http_status_code": self.http_status_code,
            "response_time_ms": self.response_time_ms,
            "issues": self.issues,
            "web_results_urls": self.web_results_urls,
            "recommended_url": self.recommended_url,
            "recommendation": self.recommendation,
            "validation_method": self.validation_method,
            "validator_version": self.validator_version,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def has_issues(self) -> bool:
        """Check if any issues were detected."""
        return len(self.issues) > 0 if self.issues else False
    
    @property
    def discovered_alternative(self) -> bool:
        """Check if web results discovered an alternative URL."""
        return len(self.web_results_urls) > 0 if self.web_results_urls else False

