"""
Authentication schemas.
"""
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """User response schema."""
    id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True
