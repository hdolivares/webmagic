"""
Pydantic models for Recurrente API requests and responses.
These models ensure type safety and proper data structure for Recurrente integration.
"""
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


class CheckoutItem(BaseModel):
    """
    Represents an item in a Recurrente checkout.
    
    For one-time payments, only basic fields are required.
    For subscriptions, additional billing fields are needed.
    """
    name: str = Field(..., description="Product/service name")
    amount_in_cents: int = Field(..., gt=0, description="Amount in cents (e.g., 49500 for $495)")
    currency: Literal["USD", "GTQ"] = Field(default="USD", description="Currency code")
    quantity: int = Field(default=1, ge=1, le=9, description="Quantity (1-9)")
    image_url: Optional[str] = Field(None, description="Product image URL")
    description: Optional[str] = Field(None, description="Product description")
    
    # Subscription-specific fields
    charge_type: Optional[Literal["one_time", "recurring"]] = Field(
        None, 
        description="Payment type: 'one_time' for single payment, 'recurring' for subscription"
    )
    billing_interval: Optional[Literal["week", "month", "year"]] = Field(
        None, 
        description="Billing frequency (required for subscriptions)"
    )
    billing_interval_count: Optional[int] = Field(
        None, 
        ge=1,
        description="Number of intervals between billings (e.g., 1 = every month, 2 = every 2 months)"
    )
    periods_before_automatic_cancellation: Optional[int] = Field(
        None,
        description="Number of billing periods before auto-cancel (None = never cancel)"
    )
    free_trial_interval: Optional[Literal["week", "month", "year"]] = Field(
        None,
        description="Free trial period unit"
    )
    free_trial_interval_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of free trial periods (0 = no trial)"
    )
    
    @field_validator("charge_type")
    @classmethod
    def validate_subscription_fields(cls, v, info):
        """Ensure subscription items have required billing fields."""
        if v == "recurring":
            data = info.data
            if not data.get("billing_interval"):
                raise ValueError("billing_interval is required for recurring charges")
            if not data.get("billing_interval_count"):
                raise ValueError("billing_interval_count is required for recurring charges")
        return v


class CheckoutRequest(BaseModel):
    """
    Request model for creating a Recurrente checkout.
    
    This follows the official Recurrente API format:
    https://docs.recurrente.com - POST /api/checkouts
    """
    items: List[CheckoutItem] = Field(..., min_length=1, description="Items to include in checkout")
    success_url: Optional[str] = Field(None, description="Redirect URL after successful payment")
    cancel_url: Optional[str] = Field(None, description="Redirect URL if payment is cancelled")
    user_id: Optional[str] = Field(None, description="Recurrente user ID (prepopulates customer info)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata (max 50 keys)")
    expires_at: Optional[str] = Field(None, description="Checkout expiration (ISO 8601 format)")


class CheckoutResponse(BaseModel):
    """Response from Recurrente checkout creation."""
    id: str = Field(..., description="Checkout ID (e.g., ch_xxxxx)")
    checkout_url: str = Field(..., description="URL to redirect customer to payment page")


class RecurrenteUser(BaseModel):
    """Recurrente user (customer) model."""
    email: str = Field(..., description="Customer email")
    full_name: Optional[str] = Field(None, description="Customer full name")
    phone: Optional[str] = Field(None, description="Customer phone number")


class RecurrenteUserResponse(BaseModel):
    """Response from creating a Recurrente user."""
    id: str = Field(..., description="User ID (e.g., us_xxxxx)")
    email: str = Field(..., description="Customer email")
