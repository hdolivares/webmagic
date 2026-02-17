"""
Short Link Model - URL shortener for SMS and other channels.

Stores short URL mappings with click tracking and optional expiration.
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional

from models.base import BaseModel


class ShortLink(BaseModel):
    """
    Short link record for the URL shortener.

    Maps a short slug (e.g., 'a1B2c3') to a destination URL.
    Tracks click counts and supports optional expiration.
    """

    __tablename__ = "short_links"

    # The short slug (e.g., "a1B2c3") — the part after the domain
    slug = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    # Full destination URL
    destination_url = Column(Text, nullable=False)

    # Link type for filtering and expiration logic
    # Values: "site_preview", "campaign", "custom", "other"
    link_type = Column(
        String(30),
        nullable=False,
        default="other",
        index=True,
    )

    # Soft-disable without deleting
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Expiration — null means never expires
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Click tracking
    click_count = Column(Integer, default=0, nullable=False)
    last_clicked_at = Column(DateTime(timezone=True), nullable=True)

    # Optional relations for context (all nullable)
    business_id = Column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generated_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Flexible metadata (e.g., UTM params, source channel, etc.)
    metadata = Column(JSONB, nullable=True)

    # Relationships (lazy to avoid N+1 on bulk queries)
    business = relationship("Business", lazy="selectin")
    site = relationship("GeneratedSite", lazy="selectin")
    campaign = relationship("Campaign", lazy="selectin")

    def __repr__(self):
        return f"<ShortLink {self.slug} -> {self.destination_url[:50]}>"

    @property
    def is_expired(self) -> bool:
        """Check if this link has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at.replace(tzinfo=None)

    @property
    def is_resolvable(self) -> bool:
        """Check if this link can currently redirect."""
        return self.is_active and not self.is_expired

    @property
    def preview(self) -> str:
        """Truncated destination for display."""
        if len(self.destination_url) <= 60:
            return self.destination_url
        return self.destination_url[:57] + "..."
