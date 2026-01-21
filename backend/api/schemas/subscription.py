"""
Subscription API Schemas

Pydantic models for subscription management endpoints.

Author: WebMagic Team
Date: January 21, 2026
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from uuid import UUID


# Request Schemas


class SubscriptionActivateRequest(BaseModel):
    """Request to activate monthly subscription."""
    payment_method_token: Optional[str] = Field(
        None,
        description="Optional payment method token from payment provider"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "payment_method_token": "tok_abc123..."
            }
        }


class SubscriptionCancelRequest(BaseModel):
    """Request to cancel subscription."""
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional cancellation reason"
    )
    immediate: bool = Field(
        default=False,
        description="If True, cancel immediately. If False, cancel at period end."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "reason": "No longer need the service",
                "immediate": False
            }
        }


class SubscriptionUpdatePaymentRequest(BaseModel):
    """Request to update payment method."""
    payment_method_token: str = Field(
        ...,
        description="New payment method token"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "payment_method_token": "tok_new123..."
            }
        }


# Response Schemas


class SubscriptionResponse(BaseModel):
    """Subscription details response."""
    subscription_id: Optional[str] = Field(
        None,
        description="Recurrente subscription ID"
    )
    status: str = Field(
        ...,
        description="Subscription status: active, past_due, cancelled, expired, none"
    )
    monthly_amount: float = Field(
        ...,
        description="Monthly subscription amount"
    )
    started_at: Optional[datetime] = Field(
        None,
        description="When subscription started"
    )
    next_billing_date: Optional[date] = Field(
        None,
        description="Next billing date"
    )
    ends_at: Optional[datetime] = Field(
        None,
        description="When subscription ends (for cancelled subscriptions)"
    )
    grace_period_ends: Optional[datetime] = Field(
        None,
        description="When grace period ends (for past_due subscriptions)"
    )
    is_active: bool = Field(
        ...,
        description="Whether subscription is currently active"
    )
    is_past_due: bool = Field(
        ...,
        description="Whether subscription has failed payment"
    )
    is_cancelled: bool = Field(
        ...,
        description="Whether subscription is cancelled"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "subscription_id": "sub_abc123...",
                "status": "active",
                "monthly_amount": 95.00,
                "started_at": "2026-01-21T10:00:00Z",
                "next_billing_date": "2026-02-21",
                "ends_at": None,
                "grace_period_ends": None,
                "is_active": True,
                "is_past_due": False,
                "is_cancelled": False
            }
        }


class SubscriptionActivateResponse(BaseModel):
    """Response when activating subscription."""
    subscription_id: str = Field(
        ...,
        description="Subscription ID"
    )
    payment_url: Optional[str] = Field(
        None,
        description="URL to add payment method (if needed)"
    )
    status: str = Field(
        ...,
        description="Subscription status"
    )
    monthly_amount: float = Field(
        ...,
        description="Monthly amount"
    )
    message: str = Field(
        ...,
        description="Success message"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "subscription_id": "sub_abc123...",
                "payment_url": "https://app.recurrente.com/payment/abc123",
                "status": "pending",
                "monthly_amount": 95.00,
                "message": "Subscription created. Please add payment method."
            }
        }


class SubscriptionCancelResponse(BaseModel):
    """Response when cancelling subscription."""
    subscription_id: str
    status: str
    ends_at: Optional[datetime]
    message: str
    immediate: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "subscription_id": "sub_abc123...",
                "status": "cancelled",
                "ends_at": "2026-02-21T00:00:00Z",
                "message": "Subscription will cancel at end of billing period",
                "immediate": False
            }
        }


class SubscriptionStatisticsResponse(BaseModel):
    """Subscription statistics for admin dashboard."""
    total_active: int
    total_past_due: int
    total_cancelled: int
    monthly_recurring_revenue: float
    churn_rate: float
    recent_subscriptions: list
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_active": 25,
                "total_past_due": 3,
                "total_cancelled": 5,
                "monthly_recurring_revenue": 2375.00,
                "churn_rate": 0.15,
                "recent_subscriptions": []
            }
        }
