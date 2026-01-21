"""
Domain Management API Endpoints

RESTful API for custom domain management.
Handles domain connection, verification, status, and removal.

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_active_user
from api.schemas.domain import (
    DomainConnectRequest,
    DomainConnectResponse,
    DomainVerifyRequest,
    DomainVerifyResponse,
    DomainStatusResponse,
    DomainDisconnectResponse,
    DNSRecordInfo
)
from models.user import AdminUser
from services.platform.domain_service import get_domain_service, DomainService
from core.exceptions import (
    NotFoundError,
    ValidationError,
    ForbiddenError
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/domains", tags=["Custom Domains"])

# ============================================
# DOMAIN CONNECTION
# ============================================

@router.post(
    "/connect",
    response_model=DomainConnectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect Custom Domain",
    description="Initiate custom domain connection. Returns DNS instructions for verification."
)
async def connect_domain(
    site_id: UUID,
    request: DomainConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
):
    """
    Connect a custom domain to a site.
    
    Steps:
    1. Validate domain format
    2. Check domain availability
    3. Generate verification token
    4. Return DNS instructions
    
    **Response includes:**
    - Verification token
    - DNS records to add
    - Step-by-step instructions
    """
    try:
        domain_service = get_domain_service()
        
        # Request domain connection
        verification_record = await domain_service.request_domain_connection(
            db=db,
            site_id=site_id,
            domain=request.domain,
            verification_method=request.verification_method,
            user_id=current_user.id
        )
        
        # Get DNS instructions
        dns_instructions = domain_service.get_dns_instructions(
            domain=verification_record.domain,
            token=verification_record.verification_token,
            method=verification_record.verification_method
        )
        
        # Build response
        response = DomainConnectResponse(
            id=verification_record.id,
            domain=verification_record.domain,
            verification_method=verification_record.verification_method,
            verification_token=verification_record.verification_token,
            dns_records=DNSRecordInfo(**dns_instructions),
            instructions=dns_instructions["instructions"],
            status="pending_verification",
            created_at=verification_record.created_at
        )
        
        logger.info(
            f"Domain connection initiated by user {current_user.id}: {request.domain}",
            extra={
                "user_id": str(current_user.id),
                "site_id": str(site_id),
                "domain": request.domain
            }
        )
        
        return response
    
    except NotFoundError as e:
        logger.error(f"Site not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except ValidationError as e:
        logger.warning(f"Domain connection validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except ForbiddenError as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Unexpected error connecting domain: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect domain. Please try again."
        )


# ============================================
# DOMAIN VERIFICATION
# ============================================

@router.post(
    "/verify",
    response_model=DomainVerifyResponse,
    summary="Verify Domain Ownership",
    description="Check DNS records to verify domain ownership."
)
async def verify_domain(
    site_id: UUID,
    request: DomainVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
):
    """
    Verify domain ownership via DNS check.
    
    **Checks:**
    - TXT record: _webmagic-verify.{domain}
    - CNAME record: {domain} → verify-{token}.sites.lavish.solutions
    
    **Returns:**
    - Verification status
    - SSL provisioning status
    - DNS records found
    """
    try:
        domain_service = get_domain_service()
        
        # Verify domain
        verified, dns_info = await domain_service.verify_domain(
            db=db,
            site_id=site_id,
            domain=request.domain
        )
        
        if verified:
            message = "Domain verified successfully! SSL certificate provisioning will begin shortly."
            ssl_status = "provisioning"
            estimated_time = "5-10 minutes"
        else:
            message = "Domain verification failed. Please check your DNS records."
            ssl_status = None
            estimated_time = None
        
        response = DomainVerifyResponse(
            verified=verified,
            domain=request.domain,
            ssl_status=ssl_status,
            estimated_time=estimated_time,
            message=message,
            dns_found=dns_info
        )
        
        logger.info(
            f"Domain verification {'successful' if verified else 'failed'}: {request.domain}",
            extra={
                "user_id": str(current_user.id),
                "site_id": str(site_id),
                "domain": request.domain,
                "verified": verified
            }
        )
        
        return response
    
    except NotFoundError as e:
        logger.error(f"Verification record not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except ValidationError as e:
        logger.warning(f"Verification validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Unexpected error verifying domain: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify domain. Please try again."
        )


# ============================================
# DOMAIN STATUS
# ============================================

@router.get(
    "/status",
    response_model=Optional[DomainStatusResponse],
    summary="Get Domain Status",
    description="Get current status of connected custom domain."
)
async def get_domain_status(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
):
    """
    Get domain status for a site.
    
    **Returns:**
    - Domain name
    - Verification status
    - SSL certificate status
    - Last check time
    - DNS records found
    
    Returns `null` if no custom domain is connected.
    """
    try:
        domain_service = get_domain_service()
        
        # Get domain status
        record = await domain_service.get_domain_status(
            db=db,
            site_id=site_id
        )
        
        if not record:
            return None
        
        response = DomainStatusResponse(
            id=record.id,
            domain=record.domain,
            verification_status="verified" if record.verified else "pending",
            verified=record.verified,
            verified_at=record.verified_at,
            ssl_status="active" if record.verified else "pending",
            ssl_expires=None,  # TODO: Get from SSL service
            last_checked=record.last_check_at,
            verification_attempts=record.verification_attempts,
            dns_records=record.dns_records
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Unexpected error getting domain status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get domain status. Please try again."
        )


# ============================================
# DOMAIN REMOVAL
# ============================================

@router.delete(
    "/disconnect",
    response_model=DomainDisconnectResponse,
    summary="Disconnect Custom Domain",
    description="Remove custom domain from site."
)
async def disconnect_domain(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
):
    """
    Disconnect custom domain from site.
    
    **Actions:**
    - Remove DNS verification record
    - Remove SSL certificate (TODO)
    - Remove Nginx configuration (TODO)
    
    **Note:** Site will still be accessible at default URL:
    `https://sites.lavish.solutions/{slug}`
    """
    try:
        domain_service = get_domain_service()
        
        # Get domain before removal for response
        record = await domain_service.get_domain_status(db=db, site_id=site_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No custom domain found for this site"
            )
        
        domain = record.domain
        
        # Remove domain
        await domain_service.remove_domain(
            db=db,
            site_id=site_id,
            user_id=current_user.id
        )
        
        response = DomainDisconnectResponse(
            success=True,
            message=f"Domain {domain} has been disconnected successfully.",
            default_url=f"https://sites.lavish.solutions/site-{str(site_id)[:8]}"
        )
        
        logger.info(
            f"Domain disconnected by user {current_user.id}: {domain}",
            extra={
                "user_id": str(current_user.id),
                "site_id": str(site_id),
                "domain": domain
            }
        )
        
        return response
    
    except HTTPException:
        raise
    
    except NotFoundError as e:
        logger.error(f"Domain not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Unexpected error disconnecting domain: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect domain. Please try again."
        )

