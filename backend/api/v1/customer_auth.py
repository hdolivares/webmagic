"""
Customer Authentication API Endpoints

Handles customer registration, login, email verification,
and password management.

Also contains customer-facing domain management endpoints that use customer
auth (get_current_customer) so the customer portal can manage domains without
needing admin credentials.

Author: WebMagic Team
Date: January 21, 2026
"""
from typing import Optional
from uuid import UUID

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
from services.emails.email_service import get_email_service
from services.customer_site_service import CustomerSiteService
from services.platform.domain_service import get_domain_service
from api.schemas.domain import (
    DomainConnectRequest,
    DomainConnectResponse,
    DomainVerifyRequest,
    DomainVerifyResponse,
    DomainStatusResponse,
    DomainDisconnectResponse,
    DNSRecordInfo,
)

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
        
        # Send welcome email with verification link
        email_service = get_email_service()
        await email_service.send_welcome_email(
            to_email=user.email,
            customer_name=user.full_name or user.email.split('@')[0],
            verification_token=user.verification_token
        )
        logger.info(f"Customer registered and welcome email sent: {user.email}")
        
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
        
        # Send verification email
        email_service = get_email_service()
        await email_service.send_verification_email(
            to_email=user.email,
            customer_name=user.full_name or user.email.split('@')[0],
            verification_token=user.verification_token
        )
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
        
        # Send password reset email
        email_service = get_email_service()
        await email_service.send_password_reset_email(
            to_email=user.email,
            customer_name=user.full_name or user.email.split('@')[0],
            reset_token=user.reset_token
        )
        logger.info(f"Password reset requested and email sent: {user.email}")
    
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


# ============================================================
# CUSTOMER-FACING DOMAIN MANAGEMENT
# Routes: /customer/domain/...
# Auth: get_current_customer (customer JWT, not admin JWT)
# ============================================================

async def _assert_site_ownership(
    db: AsyncSession,
    customer: CustomerUser,
    site_id: UUID,
) -> None:
    """Raise 403 if the customer does not own the requested site."""
    owns = await CustomerSiteService.verify_site_ownership(
        db=db,
        customer_user_id=customer.id,
        site_id=site_id,
    )
    if not owns:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't own this site",
        )


@router.get(
    "/domain/status",
    response_model=Optional[DomainStatusResponse],
    summary="Get domain status (customer)",
    description="Get the custom domain status for a site owned by the customer.",
)
async def customer_get_domain_status(
    site_id: UUID,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    await _assert_site_ownership(db, current_customer, site_id)
    try:
        domain_service = get_domain_service()
        record = await domain_service.get_domain_status(db=db, site_id=site_id)
        if not record:
            return None
        return DomainStatusResponse(
            id=record.id,
            domain=record.domain,
            verification_status="verified" if record.verified else "pending",
            verified=record.verified,
            verified_at=record.verified_at,
            ssl_status="active" if record.verified else "pending",
            ssl_expires=None,
            last_checked=record.last_check_at,
            verification_attempts=record.verification_attempts,
            dns_records=record.dns_records,
        )
    except Exception as e:
        logger.error(f"[CustomerDomain] get_domain_status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get domain status.")


@router.post(
    "/domain/connect",
    response_model=DomainConnectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect custom domain (customer)",
    description="Initiate a custom domain connection for a site owned by the customer.",
)
async def customer_connect_domain(
    site_id: UUID,
    request: DomainConnectRequest,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    await _assert_site_ownership(db, current_customer, site_id)
    try:
        domain_service = get_domain_service()
        record = await domain_service.request_domain_connection(
            db=db,
            site_id=site_id,
            domain=request.domain,
            verification_method=request.verification_method,
            user_id=current_customer.id,
        )
        dns_instructions = domain_service.get_dns_instructions(
            domain=record.domain,
            token=record.verification_token,
            method=record.verification_method,
        )
        return DomainConnectResponse(
            id=record.id,
            domain=record.domain,
            verification_method=record.verification_method,
            verification_token=record.verification_token,
            dns_records=DNSRecordInfo(**dns_instructions),
            instructions=dns_instructions["instructions"],
            status="pending_verification",
            created_at=record.created_at,
        )
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[CustomerDomain] connect_domain error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to connect domain.")


@router.post(
    "/domain/verify",
    response_model=DomainVerifyResponse,
    summary="Verify domain ownership (customer)",
    description="Check DNS records to verify domain ownership for a customer-owned site.",
)
async def customer_verify_domain(
    site_id: UUID,
    request: DomainVerifyRequest,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    await _assert_site_ownership(db, current_customer, site_id)
    try:
        domain_service = get_domain_service()
        verified, dns_info = await domain_service.verify_domain(
            db=db, site_id=site_id, domain=request.domain
        )
        return DomainVerifyResponse(
            verified=verified,
            domain=request.domain,
            ssl_status="provisioning" if verified else None,
            estimated_time="5-10 minutes" if verified else None,
            message=(
                "Domain verified successfully! SSL certificate provisioning will begin shortly."
                if verified
                else "Domain verification failed. Please check your DNS records."
            ),
            dns_found=dns_info,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[CustomerDomain] verify_domain error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify domain.")


@router.delete(
    "/domain/disconnect",
    response_model=DomainDisconnectResponse,
    summary="Disconnect custom domain (customer)",
    description="Remove a custom domain from a site owned by the customer.",
)
async def customer_disconnect_domain(
    site_id: UUID,
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    await _assert_site_ownership(db, current_customer, site_id)
    try:
        domain_service = get_domain_service()
        record = await domain_service.get_domain_status(db=db, site_id=site_id)
        if not record:
            raise HTTPException(status_code=404, detail="No custom domain found for this site")
        domain = record.domain
        await domain_service.remove_domain(
            db=db, site_id=site_id, user_id=current_customer.id
        )
        return DomainDisconnectResponse(
            success=True,
            message=f"Domain {domain} has been disconnected successfully.",
            default_url=f"https://web.lavish.solutions/{site_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CustomerDomain] disconnect_domain error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to disconnect domain.")
