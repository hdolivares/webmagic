"""
Business (leads) API endpoints.

Updated: January 22, 2026
- Added CRM enrichment with contact/campaign indicators
- Added advanced filtering options
- Enhanced responses with data quality metrics
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
import logging

from core.database import get_db
from api.deps import get_current_user
from api.schemas.business import (
    BusinessResponse,
    BusinessListResponse,
    BusinessUpdate,
    BusinessStats
)
from services.hunter.business_service import BusinessService
from services.hunter.business_filter_service import BusinessFilterService, QUICK_FILTERS
from services.crm import BusinessEnrichmentService
from models.user import AdminUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.get("/", response_model=BusinessListResponse)
async def list_businesses(
    # Pagination
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    
    # Basic filters
    category: Optional[str] = Query(None, description="Filter by category"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    
    # Contact data filters
    has_email: Optional[bool] = Query(None, description="Has email address"),
    has_phone: Optional[bool] = Query(None, description="Has phone number"),
    
    # Contact status filters
    contact_status: Optional[str] = Query(None, description="Exact contact status"),
    was_contacted: Optional[bool] = Query(None, description="Any contact made"),
    is_customer: Optional[bool] = Query(None, description="Is paying customer"),
    is_bounced: Optional[bool] = Query(None, description="Contact bounced"),
    is_unsubscribed: Optional[bool] = Query(None, description="Opted out"),
    
    # Website status filters
    website_status: Optional[str] = Query(None, description="Exact website status"),
    has_site: Optional[bool] = Query(None, description="Has generated site"),
    
    # Qualification filters
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Min qualification score"),
    max_score: Optional[int] = Query(None, ge=0, le=100, description="Max qualification score"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Min rating"),
    min_reviews: Optional[int] = Query(None, ge=0, description="Min review count"),
    
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    List businesses with advanced CRM filtering.
    
    Returns enriched business data with:
    - Contact availability indicators
    - Campaign history
    - Data quality metrics
    - Human-readable status labels
    
    Examples:
    - High-value leads: ?min_score=70&was_contacted=false
    - SMS candidates: ?has_phone=true&has_email=false
    - Bounced contacts: ?is_bounced=true
    - Customers: ?is_customer=true
    """
    service = BusinessService(db)
    enrichment = BusinessEnrichmentService(db)
    
    # Build filters
    filters = {}
    
    # Basic filters
    if category:
        filters["category"] = category
    if city:
        filters["city"] = city
    if state:
        filters["state"] = state
    
    # Contact data filters
    if has_email is not None:
        filters["email__ne" if has_email else "email"] = None
    if has_phone is not None:
        filters["phone__ne" if has_phone else "phone"] = None
    
    # Contact status filters
    if contact_status:
        filters["contact_status"] = contact_status
    elif was_contacted is True:
        filters["contact_status__ne"] = "pending"
    elif was_contacted is False:
        filters["contact_status"] = "pending"
    
    if is_customer is not None:
        if is_customer:
            filters["contact_status"] = "purchased"
        else:
            filters["contact_status__ne"] = "purchased"
    
    if is_bounced is not None:
        if is_bounced:
            filters["contact_status"] = "bounced"
    
    if is_unsubscribed is not None:
        if is_unsubscribed:
            filters["contact_status"] = "unsubscribed"
    
    # Website status filters
    if website_status:
        filters["website_status"] = website_status
    elif has_site is True:
        filters["website_status__ne"] = "none"
    elif has_site is False:
        filters["website_status"] = "none"
    
    # Qualification filters
    if min_score is not None:
        filters["qualification_score__gte"] = min_score
    if max_score is not None:
        filters["qualification_score__lte"] = max_score
    if min_rating is not None:
        filters["rating__gte"] = min_rating
    if min_reviews is not None:
        filters["review_count__gte"] = min_reviews
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    # Get businesses
    businesses, total = await service.list_businesses(
        skip=skip,
        limit=page_size,
        filters=filters if filters else None
    )
    
    # Enrich businesses with CRM indicators
    enriched_businesses = []
    for business in businesses:
        # Convert to dict
        business_dict = {
            "id": business.id,
            "slug": business.slug,
            "gmb_id": business.gmb_id,
            "name": business.name,
            "email": business.email,
            "phone": business.phone,
            "website_url": business.website_url,
            "address": business.address,
            "city": business.city,
            "state": business.state,
            "zip_code": business.zip_code,
            "country": business.country,
            "latitude": float(business.latitude) if business.latitude else None,
            "longitude": float(business.longitude) if business.longitude else None,
            "category": business.category,
            "rating": float(business.rating) if business.rating else None,
            "review_count": business.review_count,
            "reviews_summary": business.reviews_summary,
            "review_highlight": business.review_highlight,
            "brand_archetype": business.brand_archetype,
            "photos_urls": business.photos_urls or [],
            "logo_url": business.logo_url,
            "website_status": business.website_status or "none",
            "contact_status": business.contact_status or "pending",
            "qualification_score": business.qualification_score or 0,
            "created_at": business.created_at,
            "updated_at": business.updated_at,
        }
        
        # Add enrichment data
        enrichment_data = await enrichment.enrich_business(
            business,
            include_campaign_summary=False  # Skip for performance in lists
        )
        business_dict.update(enrichment_data)
        
        enriched_businesses.append(BusinessResponse(**business_dict))
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size
    
    return BusinessListResponse(
        businesses=enriched_businesses,
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
    Get a specific business by ID with full CRM enrichment.
    
    Includes:
    - All contact indicators
    - Complete campaign history
    - Site information
    - Data quality metrics
    
    Requires authentication.
    """
    service = BusinessService(db)
    enrichment = BusinessEnrichmentService(db)
    
    business = await service.get_business(business_id)
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Convert to dict
    business_dict = {
        "id": business.id,
        "slug": business.slug,
        "gmb_id": business.gmb_id,
        "name": business.name,
        "email": business.email,
        "phone": business.phone,
        "website_url": business.website_url,
        "address": business.address,
        "city": business.city,
        "state": business.state,
        "zip_code": business.zip_code,
        "country": business.country,
        "latitude": float(business.latitude) if business.latitude else None,
        "longitude": float(business.longitude) if business.longitude else None,
        "category": business.category,
        "rating": float(business.rating) if business.rating else None,
        "review_count": business.review_count,
        "reviews_summary": business.reviews_summary,
        "review_highlight": business.review_highlight,
        "brand_archetype": business.brand_archetype,
        "photos_urls": business.photos_urls or [],
        "logo_url": business.logo_url,
        "website_status": business.website_status or "none",
        "contact_status": business.contact_status or "pending",
        "qualification_score": business.qualification_score or 0,
        "created_at": business.created_at,
        "updated_at": business.updated_at,
    }
    
    # Add full enrichment data (including campaign summary)
    enrichment_data = await enrichment.enrich_business(
        business,
        include_campaign_summary=True  # Include full details for single view
    )
    business_dict.update(enrichment_data)
    
    return BusinessResponse(**business_dict)


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


# ============================================================================
# BULK ACTIONS
# ============================================================================

class BulkStatusUpdate(BaseModel):
    """Schema for bulk status updates."""
    business_ids: List[UUID]
    contact_status: Optional[str] = None
    website_status: Optional[str] = None


class BulkActionResponse(BaseModel):
    """Response for bulk actions."""
    success: int
    failed: int
    message: str


@router.post("/bulk/update-status", response_model=BulkActionResponse)
async def bulk_update_status(
    data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Bulk update status for multiple businesses.
    
    Updates contact_status and/or website_status for selected businesses.
    
    Example:
    ```json
    {
        "business_ids": ["uuid1", "uuid2", "uuid3"],
        "contact_status": "emailed",
        "website_status": null
    }
    ```
    """
    if not data.business_ids:
        raise HTTPException(status_code=400, detail="No business IDs provided")
    
    if not data.contact_status and not data.website_status:
        raise HTTPException(
            status_code=400,
            detail="Must provide at least one status to update"
        )
    
    service = BusinessService(db)
    success_count = 0
    failed_count = 0
    
    updates = {}
    if data.contact_status:
        updates["contact_status"] = data.contact_status
    if data.website_status:
        updates["website_status"] = data.website_status
    
    for business_id in data.business_ids:
        try:
            await service.update_business(business_id, updates)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to update business {business_id}: {e}")
            failed_count += 1
    
    await db.commit()
    
    return BulkActionResponse(
        success=success_count,
        failed=failed_count,
        message=f"Updated {success_count} businesses, {failed_count} failed"
    )


@router.post("/bulk/export")
async def bulk_export(
    business_ids: Optional[List[UUID]] = None,
    format: str = Query("csv", regex="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Export businesses to CSV or JSON.
    
    If business_ids is provided, exports only those businesses.
    Otherwise, applies current filters from session (future enhancement).
    
    Formats:
    - csv: Comma-separated values
    - json: JSON array
    """
    from fastapi.responses import StreamingResponse
    import io
    import csv
    import json as json_lib
    
    service = BusinessService(db)
    enrichment = BusinessEnrichmentService(db)
    
    # Get businesses
    if business_ids:
        businesses = []
        for business_id in business_ids:
            business = await service.get_business(business_id)
            if business:
                businesses.append(business)
    else:
        # Export all (limit to 1000 for safety)
        businesses, _ = await service.list_businesses(skip=0, limit=1000)
    
    if format == "csv":
        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "name", "email", "phone", "category", "city", "state",
            "rating", "review_count", "qualification_score",
            "contact_status", "website_status", "has_email", "has_phone",
            "was_contacted", "is_customer", "data_completeness",
            "created_at"
        ])
        writer.writeheader()
        
        for business in businesses:
            enrichment_data = await enrichment.enrich_business(
                business,
                include_campaign_summary=False
            )
            writer.writerow({
                "id": str(business.id),
                "name": business.name,
                "email": business.email or "",
                "phone": business.phone or "",
                "category": business.category or "",
                "city": business.city or "",
                "state": business.state or "",
                "rating": business.rating or "",
                "review_count": business.review_count or 0,
                "qualification_score": business.qualification_score or 0,
                "contact_status": business.contact_status or "pending",
                "website_status": business.website_status or "none",
                "has_email": enrichment_data["has_email"],
                "has_phone": enrichment_data["has_phone"],
                "was_contacted": enrichment_data["was_contacted"],
                "is_customer": enrichment_data["is_customer"],
                "data_completeness": enrichment_data["data_completeness"],
                "created_at": business.created_at.isoformat()
            })
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=businesses.csv"}
        )
    
    else:  # json
        # Create JSON
        export_data = []
        for business in businesses:
            enrichment_data = await enrichment.enrich_business(
                business,
                include_campaign_summary=True
            )
            export_data.append({
                "id": str(business.id),
                "name": business.name,
                "email": business.email,
                "phone": business.phone,
                "category": business.category,
                "city": business.city,
                "state": business.state,
                "rating": float(business.rating) if business.rating else None,
                "review_count": business.review_count,
                "qualification_score": business.qualification_score,
                "contact_status": business.contact_status,
                "website_status": business.website_status,
                **enrichment_data,
                "created_at": business.created_at.isoformat()
            })
        
        return StreamingResponse(
            iter([json_lib.dumps(export_data, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=businesses.json"}
        )


# ============================================
# PHASE 4: ADVANCED FILTERING ENDPOINTS
# ============================================

class FilterRequest(BaseModel):
    """Request model for advanced filtering."""
    filters: dict
    sort_by: str = "scraped_at"
    sort_desc: bool = True
    page: int = 1
    page_size: int = 50


class SaveFilterPresetRequest(BaseModel):
    """Request model for saving filter preset."""
    name: str
    filters: dict
    is_public: bool = False


@router.post("/filter")
async def filter_businesses_advanced(
    request: FilterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Advanced business filtering with complex AND/OR logic.
    
    Supports:
    - Complex filter combinations
    - Custom operators (eq, ne, gt, lt, in, contains, etc.)
    - Nested AND/OR logic
    - Multiple field filtering
    
    Example request body:
    ```json
    {
        "filters": {
            "AND": [
                {"state": "CA"},
                {"OR": [
                    {"website_url": {"operator": "is_null", "value": null}},
                    {"website_validation_status": {"operator": "in", "value": ["invalid", "missing"]}}
                ]},
                {"rating": {"operator": "gte", "value": 4.0}}
            ]
        },
        "sort_by": "rating",
        "sort_desc": true,
        "page": 1,
        "page_size": 50
    }
    ```
    """
    try:
        filter_service = BusinessFilterService(db)
        
        # Calculate skip for pagination
        skip = (request.page - 1) * request.page_size
        
        result = await filter_service.filter_businesses(
            filters=request.filters,
            sort_by=request.sort_by,
            sort_desc=request.sort_desc,
            skip=skip,
            limit=request.page_size
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to filter businesses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters/quick")
async def get_quick_filters(
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get predefined quick filter templates.
    
    Returns commonly used filter configurations that can be applied instantly.
    """
    return {
        "quick_filters": QUICK_FILTERS
    }


@router.get("/filters/stats")
async def get_filter_stats(
    filters: Optional[str] = Query(None, description="JSON string of filters to apply"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get statistics for businesses matching filters.
    
    Useful for showing "You have X businesses without websites" messages.
    """
    try:
        import json as json_lib
        
        filter_service = BusinessFilterService(db)
        
        # Parse filters if provided
        parsed_filters = None
        if filters:
            try:
                parsed_filters = json_lib.loads(filters)
            except json_lib.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in filters parameter")
        
        # Get counts by website status
        counts = await filter_service.count_by_website_status(parsed_filters)
        
        return {
            "by_website_status": counts,
            "filters_applied": parsed_filters
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get filter stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/filters/presets")
async def save_filter_preset(
    request: SaveFilterPresetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Save a filter preset for reuse.
    
    Allows users to save complex filter combinations with a friendly name.
    """
    try:
        filter_service = BusinessFilterService(db)
        
        preset = await filter_service.save_filter_preset(
            user_id=current_user.id,
            name=request.name,
            filters=request.filters,
            is_public=request.is_public
        )
        
        return {
            "id": str(preset.id),
            "name": preset.name,
            "filters": preset.filters,
            "is_public": preset.is_public,
            "created_at": preset.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to save filter preset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters/presets")
async def list_filter_presets(
    include_public: bool = Query(True, description="Include public presets from other users"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    List all filter presets for the current user.
    
    Includes user's own presets and optionally public presets from other users.
    """
    try:
        filter_service = BusinessFilterService(db)
        
        presets = await filter_service.get_user_presets(
            user_id=current_user.id,
            include_public=include_public
        )
        
        return {
            "presets": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "filters": p.filters,
                    "is_public": p.is_public,
                    "is_own": p.user_id == current_user.id,
                    "created_at": p.created_at.isoformat()
                }
                for p in presets
            ],
            "total": len(presets)
        }
        
    except Exception as e:
        logger.error(f"Failed to list filter presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/filters/presets/{preset_id}")
async def delete_filter_preset(
    preset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Delete a filter preset.
    
    Users can only delete their own presets.
    """
    try:
        filter_service = BusinessFilterService(db)
        
        deleted = await filter_service.delete_preset(
            preset_id=preset_id,
            user_id=current_user.id
        )
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Preset not found or you don't have permission to delete it"
            )
        
        return {"message": "Preset deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete filter preset: {e}")
        raise HTTPException(status_code=500, detail=str(e))
