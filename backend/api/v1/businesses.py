"""
Business (leads) API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from core.database import get_db
from api.deps import get_current_user
from api.schemas.business import (
    BusinessResponse,
    BusinessListResponse,
    BusinessUpdate,
    BusinessStats
)
from services.hunter.business_service import BusinessService
from models.user import AdminUser

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.get("/", response_model=BusinessListResponse)
async def list_businesses(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by website_status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    has_email: Optional[bool] = Query(None, description="Filter by email presence"),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    List all businesses with pagination and filters.
    Requires authentication.
    """
    service = BusinessService(db)
    
    # Build filters
    filters = {}
    if status:
        filters["website_status"] = status
    if category:
        filters["category"] = category
    if has_email is not None:
        if has_email:
            # Only get businesses with email
            filters["email__ne"] = None
        else:
            # Only get businesses without email
            filters["email"] = None
    if min_rating:
        filters["rating__gte"] = min_rating
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    # Get businesses
    businesses, total = await service.list_businesses(
        skip=skip,
        limit=page_size,
        filters=filters if filters else None
    )
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size
    
    return BusinessListResponse(
        businesses=[BusinessResponse.model_validate(b) for b in businesses],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/stats", response_model=BusinessStats)
async def get_business_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get business statistics.
    Requires authentication.
    """
    service = BusinessService(db)
    stats = await service.get_stats()
    return BusinessStats(**stats)


@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get a specific business by ID.
    Requires authentication.
    """
    service = BusinessService(db)
    business = await service.get_business(business_id)
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return BusinessResponse.model_validate(business)


@router.patch("/{business_id}", response_model=BusinessResponse)
async def update_business(
    business_id: UUID,
    updates: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Update a business.
    Requires authentication.
    """
    service = BusinessService(db)
    
    # Get existing business
    existing = await service.get_business(business_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Apply updates
    update_dict = updates.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated = await service.update_business(business_id, update_dict)
    
    return BusinessResponse.model_validate(updated)


@router.delete("/{business_id}")
async def delete_business(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Delete a business.
    Requires authentication and super_admin role.
    """
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Only super_admin can delete businesses"
        )
    
    service = BusinessService(db)
    deleted = await service.delete_business(business_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {"message": "Business deleted successfully"}
