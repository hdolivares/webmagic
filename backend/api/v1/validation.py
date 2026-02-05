"""
Website validation API endpoints.
Provides endpoints for triggering and managing website validations.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from core.database import get_db
from api.deps import get_current_user
from models.user import AdminUser
from models.business import Business
from tasks.validation_tasks import (
    validate_business_website,
    batch_validate_websites,
    validate_all_pending
)

router = APIRouter(prefix="/validation", tags=["validation"])
logger = logging.getLogger(__name__)


# ============================================
# Schemas
# ============================================

class ValidationTriggerResponse(BaseModel):
    """Response when validation is triggered."""
    message: str
    business_id: str
    task_id: str
    status: str = "queued"


class BatchValidationRequest(BaseModel):
    """Request to validate multiple businesses."""
    business_ids: List[UUID] = Field(..., description="List of business IDs to validate")


class BatchValidationResponse(BaseModel):
    """Response for batch validation."""
    message: str
    total: int
    queued: int
    tasks: List[dict]


class ValidationStatusResponse(BaseModel):
    """Validation status for a business."""
    business_id: str
    business_name: str
    website_url: Optional[str]
    validation_status: str
    validation_result: Optional[dict]
    validated_at: Optional[datetime]
    quality_score: Optional[int]


class ValidationStatsResponse(BaseModel):
    """Overall validation statistics."""
    total_businesses: int
    total_with_websites: int
    pending: int
    valid: int
    invalid: int
    no_website: int
    error: int


# ============================================
# Endpoints
# ============================================

@router.post("/businesses/{business_id}/validate", response_model=ValidationTriggerResponse)
async def trigger_business_validation(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Trigger website validation for a specific business.
    
    The validation runs in the background via Celery and includes:
    - Website accessibility check
    - Content extraction (title, description, etc.)
    - Contact information detection (phone, email, address)
    - Quality scoring
    - Screenshot capture
    
    The validation result will be stored in the business record.
    """
    # Check if business exists
    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    if not business.website_url:
        raise HTTPException(status_code=400, detail="Business has no website URL")
    
    # Queue validation task
    task = validate_business_website.delay(str(business_id))
    
    logger.info(f"Queued validation for business {business_id}, task_id: {task.id}")
    
    return ValidationTriggerResponse(
        message=f"Validation queued for {business.name}",
        business_id=str(business_id),
        task_id=task.id,
        status="queued"
    )


@router.post("/businesses/batch-validate", response_model=BatchValidationResponse)
async def trigger_batch_validation(
    request: BatchValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Trigger validation for multiple businesses at once.
    
    Useful for bulk processing. Maximum 100 businesses per request.
    """
    if len(request.business_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 businesses per batch request"
        )
    
    # Verify all businesses exist
    result = await db.execute(
        select(Business).where(Business.id.in_(request.business_ids))
    )
    businesses = result.scalars().all()
    
    if len(businesses) != len(request.business_ids):
        raise HTTPException(
            status_code=404,
            detail="Some businesses not found"
        )
    
    # Queue batch validation
    task_result = batch_validate_websites.delay(
        [str(bid) for bid in request.business_ids]
    )
    
    logger.info(f"Queued batch validation for {len(request.business_ids)} businesses")
    
    # Return immediate response (actual tasks are queued internally)
    return BatchValidationResponse(
        message=f"Batch validation queued for {len(request.business_ids)} businesses",
        total=len(request.business_ids),
        queued=len(request.business_ids),
        tasks=[{"task_id": task_result.id}]
    )


@router.post("/validate-all-pending")
async def trigger_validate_all_pending(
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Trigger validation for all businesses with pending validation status.
    
    Processes up to 100 businesses at a time.
    Useful for periodic batch processing.
    """
    task = validate_all_pending.delay()
    
    logger.info(f"Queued validate_all_pending task: {task.id}")
    
    return {
        "message": "Queued validation for all pending businesses",
        "task_id": task.id
    }


@router.get("/businesses/{business_id}/status", response_model=ValidationStatusResponse)
async def get_validation_status(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get validation status and results for a specific business.
    """
    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Extract quality score from validation result
    quality_score = None
    if business.website_validation_result:
        quality_score = business.website_validation_result.get("quality_score")
    
    return ValidationStatusResponse(
        business_id=str(business.id),
        business_name=business.name,
        website_url=business.website_url,
        validation_status=business.website_validation_status or "pending",
        validation_result=business.website_validation_result,
        validated_at=business.website_validated_at,
        quality_score=quality_score
    )


@router.get("/stats", response_model=ValidationStatsResponse)
async def get_validation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get overall validation statistics.
    
    Shows breakdown of validation statuses across all businesses.
    """
    # Total businesses
    total_result = await db.execute(select(func.count(Business.id)))
    total = total_result.scalar()
    
    # Businesses with websites
    with_websites_result = await db.execute(
        select(func.count(Business.id)).where(Business.website_url.isnot(None))
    )
    with_websites = with_websites_result.scalar()
    
    # Count by status
    status_counts = {}
    for status in ['pending', 'valid', 'invalid', 'no_website', 'error']:
        result = await db.execute(
            select(func.count(Business.id)).where(
                Business.website_validation_status == status
            )
        )
        status_counts[status] = result.scalar() or 0
    
    return ValidationStatsResponse(
        total_businesses=total,
        total_with_websites=with_websites,
        **status_counts
    )


@router.get("/businesses/validated")
async def list_validated_businesses(
    status: Optional[str] = Query(None, description="Filter by validation status"),
    min_quality_score: Optional[int] = Query(None, ge=0, le=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    List businesses with their validation status.
    
    Supports filtering by:
    - Validation status
    - Minimum quality score
    
    Results are paginated.
    """
    # Build query
    query = select(Business).where(Business.website_url.isnot(None))
    
    # Apply filters
    if status:
        query = query.where(Business.website_validation_status == status)
    
    # For quality score filter, need to use JSONB query
    if min_quality_score is not None:
        query = query.where(
            func.cast(
                Business.website_validation_result['quality_score'],
                Integer
            ) >= min_quality_score
        )
    
    # Order by validation date (most recent first)
    query = query.order_by(Business.website_validated_at.desc().nullslast())
    
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    businesses = result.scalars().all()
    
    # Format response
    return {
        "businesses": [
            {
                "id": str(b.id),
                "name": b.name,
                "website_url": b.website_url,
                "validation_status": b.website_validation_status,
                "quality_score": b.website_validation_result.get("quality_score") if b.website_validation_result else None,
                "validated_at": b.website_validated_at,
            }
            for b in businesses
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size
    }


# Import Integer for quality score filter
from sqlalchemy import Integer

