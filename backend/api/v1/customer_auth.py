"""
Customer Authentication API Endpoints

Handles customer registration, login, email verification,
and password management.

Author: WebMagic Team
Date: January 21, 2026
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.database import get_db
from core.customer_security import (
    create_customer_access_token,
    get_current_customer,
    ACCESS_TOKEN_EXPIRE_HOURS
)
from core.exceptions import ValidationError, UnauthorizedError, NotFoundError
from api.schemas.customer_auth import (
    CustomerRegisterRequest,
    CustomerLoginRequest,
    CustomerLoginResponse,
    CustomerUserResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    UpdateProfileRequest,
    MessageResponse,
    ErrorResponse
)
from models.site_models import CustomerUser
from services.customer_auth_service import CustomerAuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customer", tags=["Customer Authentication"])


@router.post(
    "/register",
    response_model=CustomerLoginResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Email already registered"}
    },
    summary="Register new customer account",
    description="Create a new customer account. Returns JWT token for immediate login."
)
async def register(
    request: CustomerRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new customer account.
    
    - **email**: Valid email address (will be lowercased)
    - **password**: Minimum 8 characters, must contain letter and number
    - **full_name**: Optional full name
    - **phone**: Optional phone number
    
    Returns JWT access token for immediate login.
    Email verification required for full access.
    """
    try:
        # Create customer user
        user = await CustomerAuthService.create_customer_user(
            db=db,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            phone=request.phone
        )
        
        # Generate JWT token
        access_token = create_customer_access_token(
            customer_id=str(user.id),
            email=user.email
        )
        
        # TODO: Send verification email
        logger.info(f"Customer registered: {user.email}")
        
        return CustomerLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
            user=CustomerUserResponse.from_orm(user),
            email_verified=user.email_verified
        )
    
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post(
    "/login",
    response_model=CustomerLoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"}
    },
    summary="Customer login",
    description="Authenticate customer and return JWT token."
)
async def login(
    request: CustomerLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate customer with email and password.
    
    Returns JWT access token valid for 24 hours.
    """
    try:
        # Authenticate customer
        user, email_verified = await CustomerAuthService.authenticate_customer(
            db=db,
            email=request.email,
            password=request.password
        )
        
        # Generate JWT token
        access_token = create_customer_access_token(
            customer_id=str(user.id),
            email=user.email
        )
        
        logger.info(f"Customer logged in: {user.email}")
        
        return CustomerLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
            user=CustomerUserResponse.from_orm(user),
            email_verified=email_verified
        )
    
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.get(
    "/me",
    response_model=CustomerUserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    },
    summary="Get current customer profile",
    description="Get authenticated customer's profile information."
)
async def get_profile(
    current_customer: CustomerUser = Depends(get_current_customer)
):
    """
    Get current customer's profile.
    
    Requires valid JWT token in Authorization header.
    """
    return CustomerUserResponse.from_orm(current_customer)


@router.put(
    "/profile",
    response_model=CustomerUserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    },
    summary="Update customer profile",
    description="Update customer's profile information."
)
async def update_profile(
    request: UpdateProfileRequest,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Update customer profile (name, phone).
    
    Email cannot be changed through this endpoint.
    """
    try:
        updated_user = await CustomerAuthService.update_customer_profile(
            db=db,
            user_id=current_customer.id,
            full_name=request.full_name,
            phone=request.phone
        )
        
        logger.info(f"Profile updated: {current_customer.email}")
        
        return CustomerUserResponse.from_orm(updated_user)
    
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed. Please try again."
        )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Invalid token"}
    },
    summary="Verify email address",
    description="Verify customer's email address using token from email."
)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email address using verification token.
    
    Token is sent to customer's email during registration.
    """
    try:
        user = await CustomerAuthService.verify_email(
            db=db,
            token=request.token
        )
        
        logger.info(f"Email verified: {user.email}")
        
        return MessageResponse(
            message="Email verified successfully!",
            success=True
        )
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed. Please try again."
        )


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        400: {"model": ErrorResponse, "description": "Already verified"}
    },
    summary="Resend verification email",
    description="Resend email verification link to customer."
)
async def resend_verification(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend verification email to customer.
    
    Generates new verification token and sends email.
    """
    try:
        user = await CustomerAuthService.resend_verification_email(
            db=db,
            email=request.email
        )
        
        # TODO: Send verification email
        logger.info(f"Verification email resent: {user.email}")
        
        return MessageResponse(
            message="Verification email sent! Please check your inbox.",
            success=True
        )
    
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again."
        )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Send password reset link to customer's email."
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset.
    
    Sends password reset link to customer's email.
    Returns success even if email doesn't exist (security best practice).
    """
    try:
        user = await CustomerAuthService.request_password_reset(
            db=db,
            email=request.email
        )
        
        # TODO: Send password reset email
        logger.info(f"Password reset requested: {user.email}")
    
    except NotFoundError:
        # Don't reveal if email exists (security)
        pass
    except Exception as e:
        logger.error(f"Password reset error: {e}")
    
    # Always return success (don't reveal if email exists)
    return MessageResponse(
        message="If that email exists, a password reset link has been sent.",
        success=True
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired token"}
    },
    summary="Reset password",
    description="Reset password using token from email."
)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password using reset token.
    
    Token is sent to customer's email via forgot-password endpoint.
    """
    try:
        user = await CustomerAuthService.reset_password(
            db=db,
            token=request.token,
            new_password=request.new_password
        )
        
        logger.info(f"Password reset: {user.email}")
        
        return MessageResponse(
            message="Password reset successfully! You can now log in.",
            success=True
        )
    
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed. Please try again."
        )


@router.post(
    "/change-password",
    response_model=MessageResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Current password incorrect"}
    },
    summary="Change password",
    description="Change password for logged-in customer."
)
async def change_password(
    request: ChangePasswordRequest,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Change password for authenticated customer.
    
    Requires current password for verification.
    """
    try:
        await CustomerAuthService.change_password(
            db=db,
            user_id=current_customer.id,
            current_password=request.current_password,
            new_password=request.new_password
        )
        
        logger.info(f"Password changed: {current_customer.email}")
        
        return MessageResponse(
            message="Password changed successfully!",
            success=True
        )
    
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed. Please try again."
        )
