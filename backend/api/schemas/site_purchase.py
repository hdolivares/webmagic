"""
Site Purchase API Schemas

Pydantic models for site purchase flow and subscription management.

Author: WebMagic Team
Date: January 21, 2026
"""
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional
from datetime import datetime, date
from uuid import UUID


# Request Schemas


class PurchaseCheckoutRequest(BaseModel):
    """Request to create a purchase checkout."""
    customer_email: EmailStr = Field(
        ...,
        description="Customer email address"
    )
    customer_name: Optional[str] = Field(
        None,
        description="Customer full name (optional)"
    )
    success_url: Optional[HttpUrl] = Field(
        None,
        description="URL to redirect after successful payment"
    )
    cancel_url: Optional[HttpUrl] = Field(
        None,
        description="URL to redirect if payment is cancelled"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_email": "john@example.com",
                "customer_name": "John Doe",
                "success_url": "https://sites.lavish.solutions/purchase-success",
                "cancel_url": "https://sites.lavish.solutions/purchase-cancelled"
            }
        }


class SubscriptionCreateRequest(BaseModel):
    """Request to create monthly subscription."""
    payment_method_token: Optional[str] = Field(
        None,
        description="Payment method token from Recurrente"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "payment_method_token": "tok_abc123..."
            }
        }


# Response Schemas


class SiteResponse(BaseModel):
    """Site information response."""
    id: UUID
    slug: str
    site_title: Optional[str]
    site_description: Optional[str]
    site_url: str
    status: str
    purchased_at: Optional[datetime]
    purchase_amount: Optional[float]
    subscription_status: Optional[str]
    subscription_started_at: Optional[datetime]
    next_billing_date: Optional[date]
    monthly_amount: Optional[float]
    custom_domain: Optional[str]
    domain_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "slug": "la-plumbing-pros",
                "site_title": "LA Plumbing Pros",
                "site_description": "Professional plumbing services in Los Angeles",
                "site_url": "https://sites.lavish.solutions/la-plumbing-pros",
                "status": "active",
                "purchased_at": "2026-01-15T10:00:00",
                "purchase_amount": 495.00,
                "subscription_status": "active",
                "subscription_started_at": "2026-01-15T10:00:00",
                "next_billing_date": "2026-02-15",
                "monthly_amount": 95.00,
                "custom_domain": None,
                "domain_verified": False,
                "created_at": "2026-01-15T09:00:00"
            }
        }


class PurchaseCheckoutResponse(BaseModel):
    """Response with Recurrente checkout URL."""
    checkout_id: str = Field(
        ...,
        description="Recurrente checkout ID"
    )
    checkout_url: str = Field(
        ...,
        description="URL to redirect customer for payment"
    )
    site_slug: str = Field(
        ...,
        description="Site slug being purchased"
    )
    site_title: Optional[str] = Field(
        None,
        description="Site title"
    )
    amount: float = Field(
        ...,
        description="Purchase amount in USD"
    )
    currency: str = Field(
        default="USD",
        description="Currency code"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "checkout_id": "chk_abc123...",
                "checkout_url": "https://app.recurrente.com/checkout/abc123",
                "site_slug": "la-plumbing-pros",
                "site_title": "LA Plumbing Pros",
                "amount": 495.00,
                "currency": "USD"
            }
        }


class SiteVersionResponse(BaseModel):
    """Site version information."""
    id: UUID
    version_number: int
    change_description: Optional[str]
    change_type: Optional[str]
    created_by_type: Optional[str]
    is_current: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "version_number": 1,
                "change_description": "Initial site generation",
                "change_type": "initial",
                "created_by_type": "admin",
                "is_current": True,
                "created_at": "2026-01-15T09:00:00"
            }
        }


class SubscriptionResponse(BaseModel):
    """Subscription information response."""
    subscription_id: str
    status: str
    monthly_amount: float
    next_billing_date: Optional[date]
    started_at: datetime
    ends_at: Optional[datetime]
    
    class Config:
        json_schema_extra = {
            "example": {
                "subscription_id": "sub_abc123...",
                "status": "active",
                "monthly_amount": 95.00,
                "next_billing_date": "2026-02-15",
                "started_at": "2026-01-15T10:00:00",
                "ends_at": None
            }
        }


class PurchaseStatisticsResponse(BaseModel):
    """Purchase statistics for admin dashboard."""
    status_counts: dict
    total_preview: int
    total_owned: int
    total_active: int
    total_revenue: float
    recent_purchases: list
    
    class Config:
        json_schema_extra = {
            "example": {
                "status_counts": {
                    "preview": 10,
                    "owned": 5,
                    "active": 15
                },
                "total_preview": 10,
                "total_owned": 5,
                "total_active": 15,
                "total_revenue": 14850.00,
                "recent_purchases": [
                    {
                        "slug": "la-plumbing-pros",
                        "title": "LA Plumbing Pros",
                        "purchased_at": "2026-01-20T10:00:00",
                        "amount": 495.00
                    }
                ]
            }
        }
