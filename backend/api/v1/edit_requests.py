"""
Edit Requests API Endpoints

RESTful API for AI-powered site edit requests.
Follows best practices with clear documentation and error handling.

Author: WebMagic Team
Date: January 21, 2026
"""
from typing import Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_active_user
from api.schemas.edit_request import (
    EditRequestCreate,
    EditRequestResponse,
    EditRequestSummary,
    EditRequestList,
    EditRequestApproval,
    EditRequestStats
)
from models.user import AdminUser
from services.edit_service import get_edit_service, EditService
from core.exceptions import (
    NotFoundError,
    ValidationError,
    ForbiddenError
)

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/sites/{site_id}/edits",
    tags=["edit-requests"],
    responses={
        404: {"description": "Site or edit request not found"},
        403: {"description": "Permission denied"},
        422: {"description": "Validation error"}
    }
)


# ============================================================================
# CREATE ENDPOINTS
# ============================================================================

@router.post(
    "",
    response_model=EditRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create edit request",
    description="""
    Create a new AI-powered edit request for a site.
    
    The request will be queued for processing. You'll receive a notification
    when the preview is ready for review.
    
    **Request Types:**
    - `text`: Change text content
    - `style`: Modify colors, fonts, spacing
    - `layout`: Restructure page sections
    - `content`: Add or remove content blocks
    - `image`: Replace images (Phase 4.5)
    
    **Rate Limits:**
    - Maximum 5 concurrent pending requests per site
    - Requests are processed in FIFO order
    
    **Example:**
    ```json
    {
        "request_text": "Change the hero button to green and make it larger",
        "request_type": "style",
        "target_section": "hero"
    }
    ```
    """
)
async def create_edit_request(
    site_id: UUID,
    request_data: EditRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
) -> EditRequestResponse:
    """
    Create a new edit request.
    
    Args:
        site_id: ID of the site to edit
        request_data: Edit request details
        db: Database session
        current_user: Authenticated customer
    
    Returns:
        Created edit request
    
    Raises:
        HTTPException: If validation fails or permissions denied
    """
    try:
        # Get service
        edit_service = get_edit_service(db)
        
        # Create edit request
        edit_request = await edit_service.create_edit_request(
            site_id=site_id,
            request_text=request_data.request_text,
            request_type=request_data.request_type,
            target_section=request_data.target_section,
            customer_id=current_user.id
        )
        
        # Trigger async processing (Celery task)
        from tasks.edit_processing import process_edit_request_task
        process_edit_request_task.delay(str(edit_request.id))
        
        logger.info(
            f"Customer {current_user.id} created edit request {edit_request.id}",
            extra={
                "customer_id": str(current_user.id),
                "site_id": str(site_id),
                "edit_request_id": str(edit_request.id)
            }
        )
        
        return EditRequestResponse.model_validate(edit_request)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating edit request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the edit request"
        )


# ============================================================================
# READ ENDPOINTS
# ============================================================================

@router.get(
    "",
    response_model=EditRequestList,
    summary="List edit requests",
    description="""
    Get a paginated list of edit requests for a site.
    
    **Filters:**
    - `status`: Filter by status (pending, processing, ready_for_review, etc.)
    
    **Pagination:**
    - Default page size: 20
    - Maximum page size: 100
    
    **Sorting:**
    - Results are sorted by creation date (newest first)
    """
)
async def list_edit_requests(
    site_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
) -> EditRequestList:
    """
    List edit requests for a site.
    
    Args:
        site_id: ID of the site
        status: Optional status filter
        page: Page number (1-indexed)
        page_size: Number of items per page
        db: Database session
        current_user: Authenticated customer
    
    Returns:
        Paginated list of edit requests
    """
    try:
        # Get service
        edit_service = get_edit_service(db)
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get requests
        requests, total = await edit_service.list_edit_requests(
            site_id=site_id,
            status=status,
            limit=page_size,
            offset=offset,
            customer_id=current_user.id
        )
        
        # Convert to response models
        items = [
            EditRequestSummary.model_validate(req)
            for req in requests
        ]
        
        return EditRequestList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + len(items)) < total
        )
    
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error listing edit requests: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving edit requests"
        )


@router.get(
    "/{request_id}",
    response_model=EditRequestResponse,
    summary="Get edit request",
    description="""
    Get detailed information about a specific edit request.
    
    **Includes:**
    - Full request details
    - AI interpretation and confidence
    - Preview URL (if available)
    - Approval/rejection status
    - Deployment information
    """
)
async def get_edit_request(
    site_id: UUID,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
) -> EditRequestResponse:
    """
    Get a specific edit request.
    
    Args:
        site_id: ID of the site
        request_id: ID of the edit request
        db: Database session
        current_user: Authenticated customer
    
    Returns:
        Edit request details
    """
    try:
        # Get service
        edit_service = get_edit_service(db)
        
        # Get request
        edit_request = await edit_service.get_edit_request(
            request_id=request_id,
            customer_id=current_user.id
        )
        
        # Verify it belongs to the specified site
        if edit_request.site_id != site_id:
            raise NotFoundError(
                "Edit request not found for this site",
                resource_type="EditRequest",
                resource_id=str(request_id)
            )
        
        return EditRequestResponse.model_validate(edit_request)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting edit request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the edit request"
        )


@router.get(
    "/stats",
    response_model=EditRequestStats,
    summary="Get edit request statistics",
    description="""
    Get statistics about edit requests for a site.
    
    **Metrics:**
    - Total requests by status
    - Average approval time
    - Average processing time
    - Most common request type
    """
)
async def get_edit_request_stats(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
) -> EditRequestStats:
    """
    Get edit request statistics for a site.
    
    Args:
        site_id: ID of the site
        db: Database session
        current_user: Authenticated customer
    
    Returns:
        Statistics dictionary
    """
    try:
        # Get service
        edit_service = get_edit_service(db)
        
        # Get stats
        stats = await edit_service.get_edit_request_stats(
            site_id=site_id,
            customer_id=current_user.id
        )
        
        return EditRequestStats(**stats)
    
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting edit request stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving statistics"
        )


# ============================================================================
# UPDATE ENDPOINTS
# ============================================================================

@router.post(
    "/{request_id}/approve",
    response_model=EditRequestResponse,
    summary="Approve edit request",
    description="""
    Approve an edit request preview.
    
    This will queue the changes for deployment to your live site.
    A backup of the current version will be created automatically.
    
    **Requirements:**
    - Request must be in `ready_for_review` status
    - You must own the site
    
    **What happens next:**
    1. Changes are applied to your live site
    2. A new version is created in version history
    3. You receive a confirmation email
    4. The previous version is backed up for rollback
    """
)
async def approve_edit_request(
    site_id: UUID,
    request_id: UUID,
    approval_data: EditRequestApproval,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
) -> EditRequestResponse:
    """
    Approve an edit request.
    
    Args:
        site_id: ID of the site
        request_id: ID of the edit request
        approval_data: Approval details
        db: Database session
        current_user: Authenticated customer
    
    Returns:
        Updated edit request
    """
    try:
        # Get service
        edit_service = get_edit_service(db)
        
        # Approve request
        if approval_data.approved:
            edit_request = await edit_service.approve_edit(
                request_id=request_id,
                customer_id=current_user.id,
                feedback=approval_data.feedback
            )
            
            # Trigger deployment (Celery task)
            from tasks.edit_processing import deploy_approved_edit_task
            deploy_approved_edit_task.delay(str(edit_request.id))
        else:
            # If approved=false, treat as rejection
            edit_request = await edit_service.reject_edit(
                request_id=request_id,
                customer_id=current_user.id,
                reason=approval_data.feedback or "Customer did not approve"
            )
        
        logger.info(
            f"Edit request {request_id} {'approved' if approval_data.approved else 'rejected'} by customer {current_user.id}",
            extra={
                "edit_request_id": str(request_id),
                "customer_id": str(current_user.id),
                "approved": approval_data.approved
            }
        )
        
        return EditRequestResponse.model_validate(edit_request)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error approving edit request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while approving the edit request"
        )


@router.post(
    "/{request_id}/reject",
    response_model=EditRequestResponse,
    summary="Reject edit request",
    description="""
    Reject an edit request preview.
    
    Provide feedback about why the changes weren't acceptable.
    You can submit a new request with revised instructions.
    
    **Requirements:**
    - Request must be in `ready_for_review` status
    - You must own the site
    - Rejection reason is required
    """
)
async def reject_edit_request(
    site_id: UUID,
    request_id: UUID,
    rejection_data: EditRequestApproval,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
) -> EditRequestResponse:
    """
    Reject an edit request.
    
    Args:
        site_id: ID of the site
        request_id: ID of the edit request
        rejection_data: Rejection details
        db: Database session
        current_user: Authenticated customer
    
    Returns:
        Updated edit request
    """
    try:
        # Require feedback for rejection
        if not rejection_data.feedback:
            raise ValidationError(
                "Rejection reason is required",
                field="feedback",
                value=None
            )
        
        # Get service
        edit_service = get_edit_service(db)
        
        # Reject request
        edit_request = await edit_service.reject_edit(
            request_id=request_id,
            customer_id=current_user.id,
            reason=rejection_data.feedback
        )
        
        logger.info(
            f"Edit request {request_id} rejected by customer {current_user.id}",
            extra={
                "edit_request_id": str(request_id),
                "customer_id": str(current_user.id),
                "reason": rejection_data.feedback
            }
        )
        
        return EditRequestResponse.model_validate(edit_request)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error rejecting edit request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while rejecting the edit request"
        )


# ============================================================================
# DELETE ENDPOINTS
# ============================================================================

@router.delete(
    "/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel edit request",
    description="""
    Cancel a pending edit request.
    
    **Requirements:**
    - Request must be in `pending` or `processing` status
    - Cannot cancel requests that are already approved or deployed
    
    **Use cases:**
    - Changed your mind about the edit
    - Want to submit a different request instead
    - Request is taking too long
    """
)
async def cancel_edit_request(
    site_id: UUID,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user)
) -> None:
    """
    Cancel an edit request.
    
    Args:
        site_id: ID of the site
        request_id: ID of the edit request
        db: Database session
        current_user: Authenticated customer
    """
    try:
        # Get service
        edit_service = get_edit_service(db)
        
        # Cancel request
        await edit_service.cancel_edit_request(
            request_id=request_id,
            customer_id=current_user.id
        )
        
        logger.info(
            f"Edit request {request_id} canceled by customer {current_user.id}",
            extra={
                "edit_request_id": str(request_id),
                "customer_id": str(current_user.id)
            }
        )
        
        # Return 204 No Content
        return None
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error canceling edit request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while canceling the edit request"
        )

