"""
Site Purchase API Endpoints

Handles site purchase checkout, webhook processing, and
customer site management.

Author: WebMagic Team
Date: January 21, 2026
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from typing import Optional
from uuid import UUID

from core.database import get_db
from core.customer_security import get_current_customer, get_optional_customer
from core.exceptions import NotFoundError, ValidationError
from api.schemas.site_purchase import (
    PurchaseCheckoutRequest,
    PurchaseCheckoutResponse,
    SiteResponse,
    SiteVersionResponse,
    PurchaseStatisticsResponse
)
from api.schemas.customer_auth import (
    CustomerUserResponse,
    MessageResponse,
    ErrorResponse
)
from models.site_models import CustomerUser, Site
from services.site_purchase_service import get_site_purchase_service
from services.site_service import get_site_service
from services.customer_site_service import CustomerSiteService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Site Purchase"])


@router.post(
    "/sites/{slug}/purchase",
    response_model=PurchaseCheckoutResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Site not found"},
        400: {"model": ErrorResponse, "description": "Site not available"}
    },
    summary="Create purchase checkout",
    description="Create Recurrente checkout session for site purchase ($495)."
)
async def create_purchase_checkout(
    slug: str,
    request: PurchaseCheckoutRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a checkout session for purchasing a site.
    
    **Flow:**
    1. Customer views preview site at `sites.lavish.solutions/{slug}`
    2. Customer clicks "Purchase This Site"
    3. Frontend calls this endpoint with customer email
    4. Recurrente checkout URL returned
    5. Customer redirected to Recurrente payment page
    6. After payment, webhook processes purchase
    
    **Args:**
    - `slug`: Site slug (from URL)
    - `customer_email`: Customer's email address
    - `customer_name`: Optional customer name
    - `success_url`: Optional redirect URL after success
    - `cancel_url`: Optional redirect URL if cancelled
    
    **Returns:**
    - `checkout_id`: Recurrente checkout ID
    - `checkout_url`: URL to redirect customer to
    - `amount`: Purchase amount ($495)
    """
    try:
        purchase_service = get_site_purchase_service()
        
        checkout = await purchase_service.create_purchase_checkout(
            db=db,
            slug=slug,
            customer_email=request.customer_email,
            customer_name=request.customer_name,
            success_url=str(request.success_url) if request.success_url else None,
            cancel_url=str(request.cancel_url) if request.cancel_url else None
        )
        
        logger.info(f"Purchase checkout created for {slug}: {checkout['checkout_id']}")
        
        return PurchaseCheckoutResponse(**checkout)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Purchase checkout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout. Please try again."
        )


@router.get(
    "/sites/{slug}",
    response_model=SiteResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Site not found"}
    },
    summary="Get site information",
    description="Get public information about a site."
)
async def get_site(
    slug: str,
    db: AsyncSession = Depends(get_db),
    customer: Optional[CustomerUser] = Depends(get_optional_customer)
):
    """
    Get site information by slug.
    
    **Public endpoint** - No authentication required.
    Shows basic site info suitable for preview.
    
    If authenticated and site owner, returns full details.
    """
    try:
        purchase_service = get_site_purchase_service()
        site = await purchase_service.get_site_by_slug(db=db, slug=slug)
        
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site not found: {slug}"
            )
        
        # Generate site URL
        site_service = get_site_service()
        site_url = site_service.generate_site_url(
            slug=site.slug,
            custom_domain=site.custom_domain if site.has_custom_domain else None
        )
        
        # Build response
        response_data = {
            "id": site.id,
            "slug": site.slug,
            "site_title": site.site_title,
            "site_description": site.site_description,
            "site_url": site_url,
            "status": site.status,
            "purchased_at": site.purchased_at,
            "purchase_amount": float(site.purchase_amount) if site.purchase_amount else None,
            "subscription_status": site.subscription_status,
            "subscription_started_at": site.subscription_started_at,
            "next_billing_date": site.next_billing_date,
            "monthly_amount": float(site.monthly_amount) if site.monthly_amount else None,
            "custom_domain": site.custom_domain,
            "domain_verified": site.domain_verified,
            "created_at": site.created_at
        }
        
        return SiteResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get site error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve site information."
        )


@router.get(
    "/customer/my-sites",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    },
    summary="Get customer's sites",
    description="Get all sites owned by authenticated customer (supports multi-site)."
)
async def get_my_sites(
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all sites owned by the current customer.
    
    **Multi-Site Support:**
    Returns a list of all sites the customer owns, with the primary site marked.
    
    Requires authentication.
    """
    try:
        customer_site_service = CustomerSiteService()
        sites = await customer_site_service.get_customer_sites(
            db=db,
            customer_user_id=current_customer.id,
            include_site_details=True
        )
        
        return {
            "sites": sites,
            "total": len(sites),
            "has_multiple_sites": len(sites) > 1
        }
    
    except Exception as e:
        logger.error(f"Get my sites error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sites."
        )


@router.get(
    "/customer/my-site",
    response_model=SiteResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "No site found"}
    },
    summary="Get customer's primary site",
    description="Get authenticated customer's primary site (for backwards compatibility)."
)
async def get_my_site(
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current customer's primary site.
    
    **Note:** This endpoint returns the primary site for backwards compatibility.
    For multi-site support, use GET /customer/my-sites instead.
    
    Requires authentication.
    Returns 404 if customer doesn't own a site yet.
    """
    if not current_customer.primary_site_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't own a site yet. Purchase a site to get started!"
        )
    
    try:
        purchase_service = get_site_purchase_service()
        site = await purchase_service.get_site_by_id(
            db=db,
            site_id=current_customer.primary_site_id
        )
        
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found"
            )
        
        # Generate site URL
        site_service = get_site_service()
        site_url = site_service.generate_site_url(
            slug=site.slug,
            custom_domain=site.custom_domain if site.has_custom_domain else None
        )
        
        response_data = {
            "id": site.id,
            "slug": site.slug,
            "site_title": site.site_title,
            "site_description": site.site_description,
            "site_url": site_url,
            "status": site.status,
            "purchased_at": site.purchased_at,
            "purchase_amount": float(site.purchase_amount) if site.purchase_amount else None,
            "subscription_status": site.subscription_status,
            "subscription_started_at": site.subscription_started_at,
            "next_billing_date": site.next_billing_date,
            "monthly_amount": float(site.monthly_amount) if site.monthly_amount else None,
            "custom_domain": site.custom_domain,
            "domain_verified": site.domain_verified,
            "created_at": site.created_at
        }
        
        return SiteResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get my site error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve site."
        )


@router.get(
    "/customer/site/versions",
    response_model=list[SiteVersionResponse],
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "No site found"}
    },
    summary="Get site version history",
    description="Get version history for customer's site."
)
async def get_site_versions(
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get version history for customer's site.
    
    Shows all versions with change descriptions.
    Useful for rollback and audit trail.
    """
    if not current_customer.site_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't own a site yet."
        )
    
    try:
        from sqlalchemy import select
        from models.site_models import SiteVersion
        
        result = await db.execute(
            select(SiteVersion)
            .where(SiteVersion.site_id == current_customer.site_id)
            .order_by(SiteVersion.version_number.desc())
        )
        versions = result.scalars().all()
        
        return [SiteVersionResponse.from_orm(v) for v in versions]
    
    except Exception as e:
        logger.error(f"Get site versions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve versions."
        )


# Admin endpoint to list all deployed sites
@router.get(
    "/admin/sites",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    },
    summary="List all deployed sites",
    description="List all deployed/purchased sites (requires admin auth)."
)
async def list_deployed_sites(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
    # TODO: Add admin authentication dependency
):
    """
    List all deployed sites.
    
    **For admin use only.**
    
    Returns list of all purchased/deployed sites with customer info.
    """
    try:
        from sqlalchemy import select, func
        
        # Count total
        count_query = select(func.count(Site.id))
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get sites
        query = select(Site).order_by(Site.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        sites = result.scalars().all()
        
        # Format response
        site_service = get_site_service()
        sites_data = []
        for site in sites:
            site_url = site_service.generate_site_url(
                slug=site.slug,
                custom_domain=site.custom_domain if site.has_custom_domain else None
            )
            sites_data.append({
                "id": str(site.id),
                "slug": site.slug,
                "site_title": site.site_title,
                "site_url": site_url,
                "status": site.status,
                "business_id": str(site.business_id) if site.business_id else None,
                "subscription_status": site.subscription_status,
                "purchased_at": site.purchased_at.isoformat() if site.purchased_at else None,
                "created_at": site.created_at.isoformat() if site.created_at else None,
            })
        
        return {
            "sites": sites_data,
            "total": total
        }
    
    except Exception as e:
        logger.error(f"List deployed sites error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sites."
        )


# Admin endpoint for purchase statistics
@router.get(
    "/admin/purchase-statistics",
    response_model=PurchaseStatisticsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    },
    summary="Get purchase statistics",
    description="Get purchase statistics for admin dashboard (requires admin auth)."
)
async def get_purchase_statistics(
    db: AsyncSession = Depends(get_db)
    # TODO: Add admin authentication dependency
):
    """
    Get purchase statistics.
    
    **For admin use only.**
    
    Returns:
    - Total sites by status
    - Total revenue
    - Recent purchases
    """
    try:
        purchase_service = get_site_purchase_service()
        stats = await purchase_service.get_purchase_statistics(db=db)
        
        return PurchaseStatisticsResponse(**stats)
    
    except Exception as e:
        logger.error(f"Get purchase statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics."
        )
