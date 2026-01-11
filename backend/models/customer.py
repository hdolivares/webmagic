"""
Customer and payment models.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from models.base import BaseModel


class Customer(BaseModel):
    """
    Customer model for paying clients.
    """
    
    __tablename__ = "customers"
    
    # Business relationship
    business_id = Column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Site relationship
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generated_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Recurrente user ID
    recurrente_user_id = Column(String(50), unique=True, nullable=True, index=True)
    
    # Contact information
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Billing information
    billing_name = Column(String(255), nullable=True)
    billing_tax_id = Column(String(50), nullable=True)
    billing_address = Column(Text, nullable=True)
    
    # Status: active, cancelled, past_due, suspended
    status = Column(String(30), default="active", nullable=False, index=True)
    
    # Lifetime value in cents
    lifetime_value_cents = Column(Integer, default=0, nullable=False)
    
    def __repr__(self):
        return f"<Customer {self.email} ({self.status})>"
    
    @property
    def lifetime_value(self) -> float:
        """Get lifetime value in dollars/local currency."""
        return self.lifetime_value_cents / 100.0


class Subscription(BaseModel):
    """
    Subscription model for recurring billing.
    """
    
    __tablename__ = "subscriptions"
    
    # Customer relationship
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Site relationship
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generated_sites.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Recurrente subscription ID
    recurrente_subscription_id = Column(String(50), unique=True, nullable=True, index=True)
    recurrente_checkout_id = Column(String(50), nullable=True)
    
    # Pricing
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default="GTQ", nullable=False)
    
    # Status: active, cancelled, past_due, paused
    status = Column(String(30), default="active", nullable=False, index=True)
    
    # Billing period
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Subscription {self.recurrente_subscription_id} ({self.status})>"
    
    @property
    def amount(self) -> float:
        """Get amount in dollars/local currency."""
        return self.amount_cents / 100.0
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status == "active"


class Payment(BaseModel):
    """
    Payment model for individual payment records.
    """
    
    __tablename__ = "payments"
    
    # Customer relationship
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Subscription relationship (if recurring payment)
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Recurrente payment ID
    recurrente_payment_id = Column(String(50), unique=True, nullable=True, index=True)
    recurrente_checkout_id = Column(String(50), nullable=True)
    
    # Payment details
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default="GTQ", nullable=False)
    fee_cents = Column(Integer, nullable=True)
    net_cents = Column(Integer, nullable=True)
    
    # Type: one_time, subscription_initial, subscription_renewal
    payment_type = Column(String(30), nullable=False)
    
    # Status: pending, processing, completed, failed, refunded
    status = Column(String(30), default="pending", nullable=False, index=True)
    
    # Payment method info
    payment_method = Column(String(30), nullable=True)
    card_last4 = Column(String(4), nullable=True)
    card_network = Column(String(20), nullable=True)
    
    # Timestamps
    paid_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Payment {self.recurrente_payment_id} ({self.status})>"
    
    @property
    def amount(self) -> float:
        """Get amount in dollars/local currency."""
        return self.amount_cents / 100.0
    
    @property
    def fee(self) -> float:
        """Get fee in dollars/local currency."""
        return (self.fee_cents or 0) / 100.0
    
    @property
    def net(self) -> float:
        """Get net amount in dollars/local currency."""
        return (self.net_cents or 0) / 100.0
    
    @property
    def is_completed(self) -> bool:
        """Check if payment is completed."""
        return self.status == "completed"
