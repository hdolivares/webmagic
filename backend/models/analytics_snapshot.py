"""
Analytics Snapshot model for daily metrics aggregation.

Stores daily snapshots of key performance indicators (KPIs)
for dashboard analytics and historical reporting.
"""
from sqlalchemy import Column, Integer, Date, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, date
import uuid

from core.database import Base


class AnalyticsSnapshot(Base):
    """
    Daily analytics snapshot for dashboard metrics.
    
    One row per day containing aggregated KPIs across the platform.
    Used for trend analysis, reporting, and dashboard visualizations.
    """
    
    __tablename__ = "analytics_snapshots"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Snapshot date (unique - one per day)
    snapshot_date = Column(Date, unique=True, nullable=False, index=True)
    
    # Lead metrics
    leads_scraped = Column(Integer, default=0, nullable=False)
    leads_qualified = Column(Integer, default=0, nullable=False)
    
    # Site metrics
    sites_generated = Column(Integer, default=0, nullable=False)
    sites_deployed = Column(Integer, default=0, nullable=False)
    
    # Email campaign metrics
    emails_sent = Column(Integer, default=0, nullable=False)
    emails_opened = Column(Integer, default=0, nullable=False)
    emails_clicked = Column(Integer, default=0, nullable=False)
    
    # Conversion metrics
    checkouts_created = Column(Integer, default=0, nullable=False)
    purchases = Column(Integer, default=0, nullable=False)
    
    # Revenue metrics (in cents to avoid floating point issues)
    revenue_cents = Column(Integer, default=0, nullable=False)
    mrr_cents = Column(Integer, default=0, nullable=False)  # Monthly Recurring Revenue
    
    # Cost tracking
    api_costs_cents = Column(Integer, default=0, nullable=False)
    
    # Timestamp
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_date_desc', snapshot_date.desc()),
    )
    
    def __repr__(self):
        return f"<AnalyticsSnapshot {self.snapshot_date} - {self.purchases} purchases, ${self.revenue/100:.2f}>"
    
    @property
    def revenue(self) -> float:
        """Get revenue in dollars."""
        return self.revenue_cents / 100.0
    
    @property
    def mrr(self) -> float:
        """Get MRR in dollars."""
        return self.mrr_cents / 100.0
    
    @property
    def api_costs(self) -> float:
        """Get API costs in dollars."""
        return self.api_costs_cents / 100.0
    
    @property
    def profit_cents(self) -> int:
        """Calculate profit (revenue - costs)."""
        return self.revenue_cents - self.api_costs_cents
    
    @property
    def profit(self) -> float:
        """Get profit in dollars."""
        return self.profit_cents / 100.0
    
    @property
    def qualification_rate(self) -> float:
        """Calculate lead qualification rate percentage."""
        if self.leads_scraped == 0:
            return 0.0
        return (self.leads_qualified / self.leads_scraped) * 100
    
    @property
    def email_open_rate(self) -> float:
        """Calculate email open rate percentage."""
        if self.emails_sent == 0:
            return 0.0
        return (self.emails_opened / self.emails_sent) * 100
    
    @property
    def email_click_rate(self) -> float:
        """Calculate email click rate percentage."""
        if self.emails_sent == 0:
            return 0.0
        return (self.emails_clicked / self.emails_sent) * 100
    
    @property
    def conversion_rate(self) -> float:
        """Calculate checkout-to-purchase conversion rate percentage."""
        if self.checkouts_created == 0:
            return 0.0
        return (self.purchases / self.checkouts_created) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "leads": {
                "scraped": self.leads_scraped,
                "qualified": self.leads_qualified,
                "qualification_rate": round(self.qualification_rate, 2),
            },
            "sites": {
                "generated": self.sites_generated,
                "deployed": self.sites_deployed,
            },
            "email": {
                "sent": self.emails_sent,
                "opened": self.emails_opened,
                "clicked": self.emails_clicked,
                "open_rate": round(self.email_open_rate, 2),
                "click_rate": round(self.email_click_rate, 2),
            },
            "conversions": {
                "checkouts": self.checkouts_created,
                "purchases": self.purchases,
                "conversion_rate": round(self.conversion_rate, 2),
            },
            "revenue": {
                "total": self.revenue,
                "mrr": self.mrr,
                "api_costs": self.api_costs,
                "profit": self.profit,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def for_date(cls, target_date: date = None) -> "AnalyticsSnapshot":
        """
        Factory method to create a new snapshot for a specific date.
        
        Usage:
            snapshot = AnalyticsSnapshot.for_date(date.today())
            snapshot.leads_scraped = 150
            session.add(snapshot)
        """
        if target_date is None:
            target_date = date.today()
        
        return cls(snapshot_date=target_date)

