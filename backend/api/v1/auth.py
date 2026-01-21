"""
Authentication endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from typing import Literal
from pydantic import BaseModel
from core.database import get_db
from core.security import verify_password, create_access_token
from core.customer_security import create_customer_access_token, ACCESS_TOKEN_EXPIRE_HOURS
from api.schemas.auth import LoginRequest, LoginResponse, UserResponse
from api.deps import get_current_user
from models.user import AdminUser
from models.site_models import CustomerUser
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================
# UNIFIED LOGIN SCHEMA
# ============================================

class UnifiedLoginResponse(BaseModel):
    """Response for unified login that works for both admin and customer users."""
    access_token: str
    token_type: str = "bearer"
    user_type: Literal["admin", "customer"]
    user: dict
    email_verified: bool = True  # Always true for admins, checked for customers


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login endpoint - returns JWT token.
    
    Default credentials (from seed data):
    - Email: admin@webmagic.com
    - Password: admin123
    """
    # Validate email format
    email = form_data.username.strip().lower()
    
    # Find user by email
    result = await db.execute(
        select(AdminUser).where(AdminUser.email == email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No account found with this email address. Please check your email and try again.",
        )
    
    # Verify password
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. Please try again.",
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact an administrator.",
        )
    
    # Update last login
    await db.execute(
        update(AdminUser)
        .where(AdminUser.id == user.id)
        .values(last_login_at=datetime.utcnow())
    )
    await db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    )


@router.post("/unified-login", response_model=UnifiedLoginResponse)
async def unified_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified login endpoint - automatically detects admin or customer users.
    
    This endpoint checks both admin and customer tables and returns
    the appropriate user type and access token.
    
    Returns user_type field indicating whether user is 'admin' or 'customer'.
    Frontend should redirect to appropriate dashboard based on user_type.
    """
    email = form_data.username.strip().lower()
    password = form_data.password
    
    # Try to authenticate as admin first
    result = await db.execute(
        select(AdminUser).where(AdminUser.email == email)
    )
    admin_user = result.scalar_one_or_none()
    
    if admin_user:
        # Found admin user - verify password
        if not verify_password(password, admin_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password. Please try again.",
            )
        
        # Check if user is active
        if not admin_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact an administrator.",
            )
        
        # Update last login
        await db.execute(
            update(AdminUser)
            .where(AdminUser.id == admin_user.id)
            .values(last_login_at=datetime.utcnow())
        )
        await db.commit()
        
        # Create access token with user_type
        access_token = create_access_token(data={
            "sub": admin_user.email,
            "user_type": "admin"
        })
        
        logger.info(f"Admin logged in via unified endpoint: {admin_user.email}")
        
        return UnifiedLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_type="admin",
            user={
                "id": str(admin_user.id),
                "email": admin_user.email,
                "full_name": admin_user.full_name,
                "role": admin_user.role
            },
            email_verified=True
        )
    
    # Try to authenticate as customer
    result = await db.execute(
        select(CustomerUser).where(CustomerUser.email == email)
    )
    customer_user = result.scalar_one_or_none()
    
    if customer_user:
        # Found customer user - verify password
        if not verify_password(password, customer_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password. Please try again.",
            )
        
        # Check if user is active
        if not customer_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact support.",
            )
        
        # Update last login
        await db.execute(
            update(CustomerUser)
            .where(CustomerUser.id == customer_user.id)
            .values(last_login_at=datetime.utcnow())
        )
        await db.commit()
        
        # Create customer access token with user_type
        access_token = create_customer_access_token(
            customer_id=str(customer_user.id),
            email=customer_user.email
        )
        
        logger.info(f"Customer logged in via unified endpoint: {customer_user.email}")
        
        return UnifiedLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_type="customer",
            user={
                "id": str(customer_user.id),
                "email": customer_user.email,
                "full_name": customer_user.full_name,
                "phone": customer_user.phone
            },
            email_verified=customer_user.email_verified
        )
    
    # No user found with this email
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No account found with this email address. Please check your email and try again.",
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get current logged-in user information.
    Requires valid JWT token in Authorization header.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active
    )


@router.post("/logout")
async def logout():
    """
    Logout endpoint.
    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token.
    """
    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change password for currently logged-in user.
    Requires valid JWT token and current password verification.
    """
    from core.security import hash_password
    
    # Verify current password
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long",
        )
    
    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )
    
    # Hash new password and update
    new_password_hash = hash_password(new_password)
    await db.execute(
        update(AdminUser)
        .where(AdminUser.id == current_user.id)
        .values(
            password_hash=new_password_hash,
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    return {"message": "Password changed successfully"}
