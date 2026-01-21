"""
Site management models for Phase 2 customer system.

Models:
- Site: Customer site with purchase and subscription tracking
- CustomerUser: Customer authentication and profile
- SiteVersion: Site version history
- EditRequest: AI-powered edit requests
- DomainVerificationRecord: Custom domain verification

Author: WebMagic Team
Date: January 21, 2026
"""
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey,
    Boolean, Date, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
from models.base import BaseModel


class Site(BaseModel):
    """Customer site model with purchase and subscription tracking."""
    
    __tablename__ = "sites"
    
    # Basic info
    slug = Column(String(255), unique=True, nullable=False, index=True)
    business_id = Column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Status: preview, owned, active, suspended, cancelled
    status = Column(String(50), default="preview", nullable=False, index=True)
    
    # Purchase info
    purchased_at = Column(DateTime(timezone=True), nullable=True)
    purchase_amount = Column(Numeric(10, 2), default=495.00)
    purchase_transaction_id = Column(String(255), nullable=True)
    
    # Subscription info
    subscription_status = Column(String(50), nullable=True, index=True)
    subscription_id = Column(String(255), nullable=True)
    subscription_started_at = Column(DateTime(timezone=True), nullable=True)
    subscription_ends_at = Column(DateTime(timezone=True), nullable=True)
    monthly_amount = Column(Numeric(10, 2), default=95.00)
    next_billing_date = Column(Date, nullable=True)
    grace_period_ends = Column(DateTime(timezone=True), nullable=True)  # Phase 3: Grace period for failed payments
    
    # Custom domain
    custom_domain = Column(String(255), unique=True, nullable=True, index=True)
    domain_verified = Column(Boolean, default=False)
    domain_verification_token = Column(String(255), nullable=True)
    domain_verified_at = Column(DateTime(timezone=True), nullable=True)
    ssl_provisioned = Column(Boolean, default=False)
    ssl_certificate_path = Column(String(500), nullable=True)
    ssl_provisioned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Site metadata
    current_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("site_versions.id", ondelete="SET NULL"),
        nullable=True
    )
    site_title = Column(String(255), nullable=True)
    site_description = Column(Text, nullable=True)
    meta_tags = Column(JSONB, nullable=True)
    
    # Relationships
    versions = relationship(
        "SiteVersion",
        foreign_keys="SiteVersion.site_id",
        back_populates="site",
        cascade="all, delete-orphan"
    )
    edit_requests = relationship(
        "EditRequest",
        back_populates="site",
        cascade="all, delete-orphan"
    )
    support_tickets = relationship(
        "SupportTicket",
        back_populates="site",
        cascade="all, delete-orphan"
    )
    customer_user = relationship(
        "CustomerUser",
        back_populates="site",
        uselist=False
    )
    
    def __repr__(self):
        return f"<Site {self.slug} ({self.status})>"
    
    @property
    def is_preview(self) -> bool:
        """Check if site is in preview status."""
        return self.status == "preview"
    
    @property
    def is_owned(self) -> bool:
        """Check if site is purchased."""
        return self.status in ("owned", "active")
    
    @property
    def is_active(self) -> bool:
        """Check if site has active subscription."""
        return self.status == "active" and self.subscription_status == "active"
    
    @property
    def has_custom_domain(self) -> bool:
        """Check if site has custom domain configured."""
        return bool(self.custom_domain and self.domain_verified and self.ssl_provisioned)


class CustomerUser(BaseModel):
    """Customer user model for authentication and profile."""
    
    __tablename__ = "customer_users"
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Site ownership
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True, index=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Activity tracking
    last_login = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    site = relationship("Site", back_populates="customer_user")
    support_tickets = relationship("SupportTicket", back_populates="customer_user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CustomerUser {self.email}>"
    
    @property
    def has_site(self) -> bool:
        """Check if user has a site."""
        return self.site_id is not None
    
    def update_last_login(self):
        """Update last login timestamp and increment count."""
        self.last_login = datetime.utcnow()
        self.login_count += 1


class SiteVersion(BaseModel):
    """
    Site version history model.
    
    Versions are immutable once created, so no updated_at column.
    """
    
    __tablename__ = "site_versions"
    
    # Override updated_at from BaseModel (versions are immutable)
    updated_at = None
    
    # Reference
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version_number = Column(Integer, nullable=False)
    
    # Content
    html_content = Column(Text, nullable=False)
    css_content = Column(Text, nullable=True)
    js_content = Column(Text, nullable=True)
    assets = Column(JSONB, nullable=True)
    
    # Metadata
    change_description = Column(Text, nullable=True)
    change_type = Column(String(50), nullable=True)  # initial, edit, major_update
    created_by_type = Column(String(50), nullable=True)  # admin, customer, ai
    created_by_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Status
    is_current = Column(Boolean, default=False)
    is_preview = Column(Boolean, default=False)
    
    # Relationships
    site = relationship("Site", foreign_keys=[site_id], back_populates="versions")
    
    def __repr__(self):
        return f"<SiteVersion {self.site_id} v{self.version_number}>"
    
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


class EditRequest(BaseModel):
    """AI-powered edit request model."""
    
    __tablename__ = "edit_requests"
    
    # Reference
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Request details
    request_text = Column(Text, nullable=False)
    request_type = Column(String(50), nullable=True)  # text, style, image, layout
    target_section = Column(String(100), nullable=True)  # hero, about, services
    
    # Status: pending, processing, ready_for_review, approved, rejected, deployed
    status = Column(String(50), default="pending", nullable=False, index=True)
    
    # AI processing
    ai_interpretation = Column(JSONB, nullable=True)
    ai_confidence = Column(Numeric(3, 2), nullable=True)
    changes_made = Column(JSONB, nullable=True)
    
    # Preview
    preview_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("site_versions.id"),
        nullable=True
    )
    preview_url = Column(String(500), nullable=True)
    
    # Approval workflow
    customer_approved = Column(Boolean, nullable=True)
    customer_feedback = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)
    
    # Deployment
    deployed_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("site_versions.id"),
        nullable=True
    )
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Processing time
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    site = relationship("Site", back_populates="edit_requests")
    
    def __repr__(self):
        return f"<EditRequest {self.id} ({self.status})>"
    
    @property
    def is_pending(self) -> bool:
        """Check if request is pending."""
        return self.status == "pending"
    
    @property
    def is_ready_for_review(self) -> bool:
        """Check if request is ready for customer review."""
        return self.status == "ready_for_review"
    
    @property
    def is_deployed(self) -> bool:
        """Check if changes are deployed."""
        return self.status == "deployed" and self.deployed_at is not None


class DomainVerificationRecord(BaseModel):
    """Domain verification record for custom domains."""
    
    __tablename__ = "domain_verification_records"
    
    # Reference
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    domain = Column(String(255), nullable=False)
    
    # Verification method: dns_txt, dns_cname, file_upload
    verification_method = Column(String(50), nullable=False)
    verification_token = Column(String(255), nullable=False)
    
    # Status
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_attempts = Column(Integer, default=0)
    last_check_at = Column(DateTime(timezone=True), nullable=True)
    
    # DNS records found
    dns_records = Column(JSONB, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<DomainVerificationRecord {self.domain} ({self.verified})>"
    
    @property
    def is_verified(self) -> bool:
        """Check if domain is verified."""
        return self.verified and self.verified_at is not None
    
    @property
    def is_expired(self) -> bool:
        """Check if verification has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
