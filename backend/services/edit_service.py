"""
Edit Service

Business logic for AI-powered site edit requests.
Handles CRUD operations, workflow management, and orchestration.

Architecture:
- Separation of concerns: Each function has one responsibility
- Clean error handling with custom exceptions
- Async/await for non-blocking operations
- Type hints for clarity

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload

from models.site_models import EditRequest, Site, SiteVersion
from core.exceptions import (
    NotFoundError,
    ValidationError,
    ForbiddenError
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

class EditRequestStatus:
    """Edit request status constants for type safety."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    FAILED = "failed"
    
    @classmethod
    def all(cls) -> List[str]:
        """Get all valid statuses."""
        return [
            cls.PENDING, cls.PROCESSING, cls.READY_FOR_REVIEW,
            cls.APPROVED, cls.REJECTED, cls.DEPLOYED, cls.FAILED
        ]
    
    @classmethod
    def is_valid(cls, status: str) -> bool:
        """Check if status is valid."""
        return status in cls.all()


class EditRequestType:
    """Edit request type constants."""
    TEXT = "text"
    STYLE = "style"
    LAYOUT = "layout"
    CONTENT = "content"
    IMAGE = "image"
    
    @classmethod
    def all(cls) -> List[str]:
        """Get all valid types."""
        return [cls.TEXT, cls.STYLE, cls.LAYOUT, cls.CONTENT, cls.IMAGE]


# ============================================================================
# MAIN SERVICE CLASS
# ============================================================================

class EditService:
    """
    Service for managing AI-powered site edit requests.
    
    Responsibilities:
    - CRUD operations for edit requests
    - Workflow state management
    - Validation and authorization
    - Statistics and analytics
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize edit service.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    # ========================================================================
    # CREATE OPERATIONS
    # ========================================================================
    
    async def create_edit_request(
        self,
        site_id: UUID,
        request_text: str,
        request_type: Optional[str] = None,
        target_section: Optional[str] = None,
        customer_id: Optional[UUID] = None
    ) -> EditRequest:
        """
        Create a new edit request.
        
        Args:
            site_id: ID of the site to edit
            request_text: Natural language description of the edit
            request_type: Type of edit (text, style, layout, etc.)
            target_section: Specific section to target
            customer_id: ID of requesting customer (for authorization)
        
        Returns:
            Created EditRequest instance
        
        Raises:
            NotFoundError: If site doesn't exist
            ForbiddenError: If customer doesn't own the site
            ValidationError: If request is invalid
        """
        # Validate site exists and customer has access
        site = await self._validate_site_access(site_id, customer_id)
        
        # Check if site has active subscription (business rule)
        if site.subscription_status != "active":
            raise ValidationError(
                "Site must have an active subscription to request edits",
                error_code="INACTIVE_SUBSCRIPTION"
            )
        
        # Check for pending requests (rate limiting)
        pending_count = await self._count_pending_requests(site_id)
        if pending_count >= 5:  # Max 5 concurrent requests
            raise ValidationError(
                "Too many pending edit requests. Please wait for current requests to complete.",
                error_code="TOO_MANY_PENDING_REQUESTS"
            )
        
        # Create the edit request
        edit_request = EditRequest(
            site_id=site_id,
            request_text=request_text.strip(),
            request_type=request_type,
            target_section=target_section,
            status=EditRequestStatus.PENDING
        )
        
        self.db.add(edit_request)
        await self.db.commit()
        await self.db.refresh(edit_request)
        
        logger.info(
            f"Created edit request {edit_request.id} for site {site_id}",
            extra={
                "edit_request_id": str(edit_request.id),
                "site_id": str(site_id),
                "request_type": request_type
            }
        )
        
        return edit_request
    
    # ========================================================================
    # READ OPERATIONS
    # ========================================================================
    
    async def get_edit_request(
        self,
        request_id: UUID,
        customer_id: Optional[UUID] = None
    ) -> EditRequest:
        """
        Get an edit request by ID.
        
        Args:
            request_id: ID of the edit request
            customer_id: ID of requesting customer (for authorization)
        
        Returns:
            EditRequest instance
        
        Raises:
            NotFoundError: If request doesn't exist
            ForbiddenError: If customer doesn't own the site
        """
        query = (
            select(EditRequest)
            .options(selectinload(EditRequest.site))
            .where(EditRequest.id == request_id)
        )
        
        result = await self.db.execute(query)
        edit_request = result.scalar_one_or_none()
        
        if not edit_request:
            raise NotFoundError(
                f"Edit request {request_id} not found",
                resource_type="EditRequest",
                resource_id=str(request_id)
            )
        
        # Verify customer access
        if customer_id:
            await self._validate_site_access(edit_request.site_id, customer_id)
        
        return edit_request
    
    async def list_edit_requests(
        self,
        site_id: UUID,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        customer_id: Optional[UUID] = None
    ) -> Tuple[List[EditRequest], int]:
        """
        List edit requests for a site.
        
        Args:
            site_id: Site to get requests for
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip
            customer_id: ID of requesting customer (for authorization)
        
        Returns:
            Tuple of (list of EditRequest, total count)
        
        Raises:
            ForbiddenError: If customer doesn't own the site
        """
        # Verify access
        if customer_id:
            await self._validate_site_access(site_id, customer_id)
        
        # Build query
        query = select(EditRequest).where(EditRequest.site_id == site_id)
        
        if status:
            query = query.where(EditRequest.status == status)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get paginated results
        query = (
            query
            .order_by(desc(EditRequest.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        result = await self.db.execute(query)
        requests = result.scalars().all()
        
        return list(requests), total
    
    async def get_edit_request_stats(
        self,
        site_id: UUID,
        customer_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about edit requests for a site.
        
        Args:
            site_id: Site to get stats for
            customer_id: ID of requesting customer (for authorization)
        
        Returns:
            Dictionary with statistics
        """
        # Verify access
        if customer_id:
            await self._validate_site_access(site_id, customer_id)
        
        # Count by status
        status_counts = {}
        for status in EditRequestStatus.all():
            count_query = select(func.count()).where(
                and_(
                    EditRequest.site_id == site_id,
                    EditRequest.status == status
                )
            )
            result = await self.db.execute(count_query)
            status_counts[status] = result.scalar_one()
        
        # Calculate average times
        avg_times_query = select(
            func.avg(
                func.extract(
                    'epoch',
                    EditRequest.approved_at - EditRequest.created_at
                )
            ).label('avg_approval_time'),
            func.avg(
                func.extract(
                    'epoch',
                    EditRequest.processed_at - EditRequest.created_at
                )
            ).label('avg_processing_time')
        ).where(
            and_(
                EditRequest.site_id == site_id,
                EditRequest.status.in_([
                    EditRequestStatus.DEPLOYED,
                    EditRequestStatus.APPROVED
                ])
            )
        )
        
        result = await self.db.execute(avg_times_query)
        times = result.one_or_none()
        
        # Get most common request type
        most_common_query = (
            select(
                EditRequest.request_type,
                func.count(EditRequest.request_type).label('count')
            )
            .where(EditRequest.site_id == site_id)
            .group_by(EditRequest.request_type)
            .order_by(desc('count'))
            .limit(1)
        )
        
        result = await self.db.execute(most_common_query)
        most_common = result.first()
        
        return {
            "total_requests": sum(status_counts.values()),
            "pending_requests": status_counts[EditRequestStatus.PENDING],
            "approved_requests": status_counts[EditRequestStatus.APPROVED],
            "rejected_requests": status_counts[EditRequestStatus.REJECTED],
            "deployed_requests": status_counts[EditRequestStatus.DEPLOYED],
            "average_approval_time_minutes": (
                times[0] / 60 if times and times[0] else None
            ),
            "average_processing_time_seconds": times[1] if times else None,
            "most_common_request_type": (
                most_common[0] if most_common else None
            )
        }
    
    # ========================================================================
    # UPDATE OPERATIONS
    # ========================================================================
    
    async def update_status(
        self,
        request_id: UUID,
        new_status: str,
        **kwargs
    ) -> EditRequest:
        """
        Update the status of an edit request.
        
        Args:
            request_id: ID of the edit request
            new_status: New status value
            **kwargs: Additional fields to update
        
        Returns:
            Updated EditRequest
        
        Raises:
            NotFoundError: If request doesn't exist
            ValidationError: If status transition is invalid
        """
        edit_request = await self.get_edit_request(request_id)
        
        # Validate status transition
        self._validate_status_transition(edit_request.status, new_status)
        
        # Update status and timestamp
        edit_request.status = new_status
        
        # Update status-specific timestamps
        if new_status == EditRequestStatus.PROCESSING:
            edit_request.processed_at = datetime.utcnow()
        elif new_status == EditRequestStatus.APPROVED:
            edit_request.approved_at = datetime.utcnow()
        elif new_status == EditRequestStatus.DEPLOYED:
            edit_request.deployed_at = datetime.utcnow()
        
        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(edit_request, key):
                setattr(edit_request, key, value)
        
        await self.db.commit()
        await self.db.refresh(edit_request)
        
        logger.info(
            f"Updated edit request {request_id} status: {new_status}",
            extra={
                "edit_request_id": str(request_id),
                "old_status": edit_request.status,
                "new_status": new_status
            }
        )
        
        return edit_request
    
    async def approve_edit(
        self,
        request_id: UUID,
        customer_id: UUID,
        feedback: Optional[str] = None
    ) -> EditRequest:
        """
        Approve an edit request preview.
        
        Args:
            request_id: ID of the edit request
            customer_id: ID of approving customer
            feedback: Optional feedback from customer
        
        Returns:
            Updated EditRequest
        
        Raises:
            NotFoundError: If request doesn't exist
            ForbiddenError: If customer doesn't own the site
            ValidationError: If request is not ready for review
        """
        edit_request = await self.get_edit_request(request_id, customer_id)
        
        # Verify request is ready for review
        if edit_request.status != EditRequestStatus.READY_FOR_REVIEW:
            raise ValidationError(
                f"Cannot approve request in status: {edit_request.status}",
                error_code="INVALID_STATUS_FOR_APPROVAL"
            )
        
        # Approve the request
        edit_request.customer_approved = True
        edit_request.customer_feedback = feedback
        edit_request.approved_at = datetime.utcnow()
        edit_request.status = EditRequestStatus.APPROVED
        
        await self.db.commit()
        await self.db.refresh(edit_request)
        
        logger.info(
            f"Edit request {request_id} approved by customer {customer_id}",
            extra={
                "edit_request_id": str(request_id),
                "customer_id": str(customer_id),
                "has_feedback": bool(feedback)
            }
        )
        
        return edit_request
    
    async def reject_edit(
        self,
        request_id: UUID,
        customer_id: UUID,
        reason: str
    ) -> EditRequest:
        """
        Reject an edit request preview.
        
        Args:
            request_id: ID of the edit request
            customer_id: ID of rejecting customer
            reason: Reason for rejection
        
        Returns:
            Updated EditRequest
        
        Raises:
            NotFoundError: If request doesn't exist
            ForbiddenError: If customer doesn't own the site
            ValidationError: If request is not ready for review
        """
        edit_request = await self.get_edit_request(request_id, customer_id)
        
        # Verify request is ready for review
        if edit_request.status != EditRequestStatus.READY_FOR_REVIEW:
            raise ValidationError(
                f"Cannot reject request in status: {edit_request.status}",
                error_code="INVALID_STATUS_FOR_REJECTION"
            )
        
        # Reject the request
        edit_request.customer_approved = False
        edit_request.rejected_reason = reason
        edit_request.status = EditRequestStatus.REJECTED
        
        await self.db.commit()
        await self.db.refresh(edit_request)
        
        logger.info(
            f"Edit request {request_id} rejected by customer {customer_id}",
            extra={
                "edit_request_id": str(request_id),
                "customer_id": str(customer_id),
                "reason": reason
            }
        )
        
        return edit_request
    
    # ========================================================================
    # DELETE OPERATIONS
    # ========================================================================
    
    async def cancel_edit_request(
        self,
        request_id: UUID,
        customer_id: UUID
    ) -> None:
        """
        Cancel a pending edit request.
        
        Args:
            request_id: ID of the edit request
            customer_id: ID of customer canceling
        
        Raises:
            NotFoundError: If request doesn't exist
            ForbiddenError: If customer doesn't own the site
            ValidationError: If request cannot be canceled
        """
        edit_request = await self.get_edit_request(request_id, customer_id)
        
        # Only allow canceling pending or processing requests
        if edit_request.status not in [
            EditRequestStatus.PENDING,
            EditRequestStatus.PROCESSING
        ]:
            raise ValidationError(
                f"Cannot cancel request in status: {edit_request.status}",
                error_code="CANNOT_CANCEL_REQUEST"
            )
        
        await self.db.delete(edit_request)
        await self.db.commit()
        
        logger.info(
            f"Edit request {request_id} canceled by customer {customer_id}",
            extra={
                "edit_request_id": str(request_id),
                "customer_id": str(customer_id)
            }
        )
    
    # ========================================================================
    # HELPER METHODS (Private)
    # ========================================================================
    
    async def _validate_site_access(
        self,
        site_id: UUID,
        customer_id: Optional[UUID]
    ) -> Site:
        """
        Validate that a site exists and customer has access.
        
        Args:
            site_id: ID of the site
            customer_id: ID of the customer (if None, skips permission check)
        
        Returns:
            Site instance
        
        Raises:
            NotFoundError: If site doesn't exist
            ForbiddenError: If customer doesn't own the site
        """
        query = select(Site).where(Site.id == site_id)
        
        if customer_id:
            query = query.join(Site.customer_user).where(
                Site.customer_user.has(id=customer_id)
            )
        
        result = await self.db.execute(query)
        site = result.scalar_one_or_none()
        
        if not site:
            if customer_id:
                raise ForbiddenError(
                    "You don't have permission to access this site",
                    resource_type="Site",
                    resource_id=str(site_id)
                )
            else:
                raise NotFoundError(
                    f"Site {site_id} not found",
                    resource_type="Site",
                    resource_id=str(site_id)
                )
        
        return site
    
    async def _count_pending_requests(self, site_id: UUID) -> int:
        """Count pending edit requests for a site."""
        query = select(func.count()).where(
            and_(
                EditRequest.site_id == site_id,
                EditRequest.status.in_([
                    EditRequestStatus.PENDING,
                    EditRequestStatus.PROCESSING
                ])
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one()
    
    def _validate_status_transition(
        self,
        current_status: str,
        new_status: str
    ) -> None:
        """
        Validate that a status transition is allowed.
        
        Valid transitions:
        - pending -> processing, failed
        - processing -> ready_for_review, failed
        - ready_for_review -> approved, rejected
        - approved -> deployed
        
        Args:
            current_status: Current status
            new_status: Desired new status
        
        Raises:
            ValidationError: If transition is invalid
        """
        valid_transitions = {
            EditRequestStatus.PENDING: [
                EditRequestStatus.PROCESSING,
                EditRequestStatus.FAILED
            ],
            EditRequestStatus.PROCESSING: [
                EditRequestStatus.READY_FOR_REVIEW,
                EditRequestStatus.FAILED
            ],
            EditRequestStatus.READY_FOR_REVIEW: [
                EditRequestStatus.APPROVED,
                EditRequestStatus.REJECTED
            ],
            EditRequestStatus.APPROVED: [
                EditRequestStatus.DEPLOYED
            ],
            EditRequestStatus.REJECTED: [
                EditRequestStatus.PENDING  # Can retry
            ],
            EditRequestStatus.FAILED: [
                EditRequestStatus.PENDING  # Can retry
            ]
        }
        
        allowed = valid_transitions.get(current_status, [])
        
        if new_status not in allowed:
            raise ValidationError(
                f"Invalid status transition: {current_status} -> {new_status}",
                field="status",
                value=new_status
            )


# ============================================================================
# DEPENDENCY INJECTION HELPER
# ============================================================================

def get_edit_service(db: AsyncSession) -> EditService:
    """
    Get EditService instance (for dependency injection).
    
    Args:
        db: Database session
    
    Returns:
        EditService instance
    """
    return EditService(db)

