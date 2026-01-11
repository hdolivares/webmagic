"""
Pydantic schemas for payments, customers, and subscriptions.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# Customer schemas

class CustomerBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None


class CustomerCreate(CustomerBase):
    business_id: Optional[UUID] = None
    site_id: Optional[UUID] = None


class CustomerOut(CustomerBase):
    id: UUID
    business_id: Optional[UUID]
    site_id: Optional[UUID]
    recurrente_user_id: Optional[str]
    status: str
    lifetime_value: float
    created_at: datetime
    
    class Config:
        from_attributes = True


# Subscription schemas

class SubscriptionOut(BaseModel):
    id: UUID
    customer_id: UUID
    site_id: Optional[UUID]
    recurrente_subscription_id: Optional[str]
    amount: float
    currency: str
    status: str
    started_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SubscriptionCancel(BaseModel):
    reason: Optional[str] = None


# Payment schemas

class PaymentOut(BaseModel):
    id: UUID
    customer_id: UUID
    subscription_id: Optional[UUID]
    recurrente_payment_id: Optional[str]
    amount: float
    currency: str
    payment_type: str
    status: str
    paid_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Checkout schemas

class CheckoutCreate(BaseModel):
    site_id: UUID
    customer_email: EmailStr
    customer_name: Optional[str] = None
    recurrence_type: str = Field(default="subscription", pattern="^(once|subscription)$")
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutOut(BaseModel):
    checkout_id: str
    checkout_url: str
    payment_id: str
    customer_id: str
    amount: float
    currency: str
    recurrence_type: str


# Webhook schemas

class WebhookEvent(BaseModel):
    event_type: str
    payload: dict


# List responses

class CustomerListOut(BaseModel):
    customers: List[CustomerOut]
    total: int
    skip: int
    limit: int


class PaymentListOut(BaseModel):
    payments: List[PaymentOut]
    total: int


# Stats schemas

class CustomerStatsOut(BaseModel):
    total_customers: int
    active_customers: int
    total_lifetime_value: float
    average_lifetime_value: float
