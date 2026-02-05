"""
Generated Site model.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from models.base import BaseModel


class GeneratedSite(BaseModel):
    """Generated website model."""
    
    __tablename__ = "generated_sites"
    
    # Business relationship
    business_id = Column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    business = relationship("Business", back_populates="generated_sites", lazy="select")
    
    # Site info
    subdomain = Column(String(100), unique=True, nullable=False, index=True)
    custom_domain = Column(String(255), nullable=True, index=True)
    
    # Content
    html_content = Column(Text, nullable=True)  # Nullable during generation
    css_content = Column(Text, nullable=True)
    js_content = Column(Text, nullable=True)
    
    # Metadata
    design_brief = Column(JSONB, nullable=True)
    builder_prompt = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    previous_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generated_sites.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Status: draft, preview, live, archived
    status = Column(String(30), default="draft", nullable=False, index=True)
    
    # Assets
    screenshot_desktop_url = Column(Text, nullable=True)
    screenshot_mobile_url = Column(Text, nullable=True)
    assets_urls = Column(JSONB, default=[], nullable=True)
    
    # Performance metrics
    lighthouse_score = Column(Integer, nullable=True)
    load_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    deployed_at = Column(DateTime, nullable=True)
    sold_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<GeneratedSite {self.subdomain} ({self.status})>"
    
    @property
    def full_url(self) -> str:
        """Get full URL for the site (path-based routing)."""
        if self.custom_domain:
            return f"https://{self.custom_domain}"
        # Use path-based routing on sites.lavish.solutions
        return f"https://sites.lavish.solutions/{self.subdomain}"
    
    @property
    def is_live(self) -> bool:
        """Check if site is live."""
        return self.status == "live"
