"""
Customer Authentication API Schemas

Pydantic models for customer registration, login, and authentication
endpoints. Includes validation rules and examples.

Author: WebMagic Team
Date: January 21, 2026
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID


# Request Schemas


class CustomerRegisterRequest(BaseModel):
    """
    Customer registration request.
    
    Used when purchasing a site or creating an account.
    """
    email: EmailStr = Field(
        ...,
        description="Customer email address",
        example="john@example.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (minimum 8 characters)",
        example="SecurePass123!"
    )
    full_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Customer full name",
        example="John Doe"
    )
    phone: Optional[str] = Field(
        None,
        max_length=50,
        description="Phone number",
        example="+1-555-123-4567"
    )
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        # Check for at least one number
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        
        # Check for at least one letter
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        
        return v
    
    @validator('email')
    def validate_email_lowercase(cls, v):
        """Convert email to lowercase."""
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "phone": "+1-555-123-4567"
            }
        }


class CustomerLoginRequest(BaseModel):
    """Customer login request."""
    email: EmailStr = Field(
        ...,
        description="Customer email address"
    )
    password: str = Field(
        ...,
        description="Customer password"
    )
    
    @validator('email')
    def validate_email_lowercase(cls, v):
        """Convert email to lowercase."""
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com",
                "password": "SecurePass123!"
            }
        }


class VerifyEmailRequest(BaseModel):
    """Email verification request."""
    token: str = Field(
        ...,
        description="Email verification token from email"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "token": "abc123def456..."
            }
        }


class ResendVerificationRequest(BaseModel):
    """Request to resend verification email."""
    email: EmailStr = Field(
        ...,
        description="Customer email address"
    )
    
    @validator('email')
    def validate_email_lowercase(cls, v):
        return v.lower()


class ForgotPasswordRequest(BaseModel):
    """Password reset request."""
    email: EmailStr = Field(
        ...,
        description="Customer email address"
    )
    
    @validator('email')
    def validate_email_lowercase(cls, v):
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@example.com"
            }
        }


class ResetPasswordRequest(BaseModel):
    """Password reset with token."""
    token: str = Field(
        ...,
        description="Password reset token from email"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password"
    )
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "token": "abc123def456...",
                "new_password": "NewSecurePass123!"
            }
        }


class ChangePasswordRequest(BaseModel):
    """Change password for logged-in user."""
    current_password: str = Field(
        ...,
        description="Current password"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password"
    )
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecurePass123!"
            }
        }


class UpdateProfileRequest(BaseModel):
    """Update customer profile."""
    full_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255
    )
    phone: Optional[str] = Field(
        None,
        max_length=50
    )
    
    class Config:
        schema_extra = {
            "example": {
                "full_name": "John Smith",
                "phone": "+1-555-999-8888"
            }
        }


# Response Schemas


class CustomerUserResponse(BaseModel):
    """Customer user profile response."""
    id: UUID
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    site_id: Optional[UUID]
    email_verified: bool
    login_count: int
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john@example.com",
                "full_name": "John Doe",
                "phone": "+1-555-123-4567",
                "site_id": "789e4567-e89b-12d3-a456-426614174000",
                "email_verified": True,
                "login_count": 5,
                "last_login": "2026-01-21T10:30:00",
                "created_at": "2026-01-15T08:00:00"
            }
        }


class CustomerLoginResponse(BaseModel):
    """Login response with JWT token."""
    access_token: str = Field(
        ...,
        description="JWT access token"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type"
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds"
    )
    user: CustomerUserResponse = Field(
        ...,
        description="Customer user profile"
    )
    email_verified: bool = Field(
        ...,
        description="Whether email is verified"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "john@example.com",
                    "full_name": "John Doe",
                    "site_id": None,
                    "email_verified": False,
                    "login_count": 1,
                    "last_login": "2026-01-21T10:30:00",
                    "created_at": "2026-01-21T10:30:00"
                },
                "email_verified": False
            }
        }


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str = Field(
        ...,
        description="Response message"
    )
    success: bool = Field(
        default=True,
        description="Whether operation was successful"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully",
                "success": True
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str = Field(
        ...,
        description="Error message"
    )
    error_code: Optional[str] = Field(
        None,
        description="Machine-readable error code"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Email already registered",
                "error_code": "EMAIL_EXISTS"
            }
        }
