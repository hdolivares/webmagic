"""
Tests for Edit Service

Comprehensive test suite for AI-powered edit requests.
Tests cover CRUD operations, workflow, and business logic.

Author: WebMagic Team
Date: January 21, 2026
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from decimal import Decimal

from services.edit_service import (
    EditService,
    EditRequestStatus,
    EditRequestType
)
from models.site_models import (
    Site,
    SiteVersion,
    EditRequest,
    CustomerUser
)
from core.exceptions import (
    ResourceNotFoundError,
    PermissionDeniedError,
    BusinessLogicError,
    ValidationError
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def test_customer(db_session):
    """Create a test customer user."""
    customer = CustomerUser(
        email="test@example.com",
        password_hash="hashed_password",
        full_name="Test Customer",
        email_verified=True
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
async def test_site(db_session, test_customer):
    """Create a test site with active subscription."""
    site = Site(
        slug="test-site",
        status="active",
        subscription_status="active",
        purchased_at=datetime.utcnow(),
        site_title="Test Site"
    )
    db_session.add(site)
    await db_session.commit()
    await db_session.refresh(site)
    
    # Link customer to site
    test_customer.site_id = site.id
    await db_session.commit()
    
    return site


@pytest.fixture
async def test_version(db_session, test_site):
    """Create a test site version."""
    version = SiteVersion(
        site_id=test_site.id,
        version_number=1,
        html_content="<html><body><h1>Test</h1></body></html>",
        css_content="h1 { color: red; }",
        is_current=True
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)
    
    # Update site current version
    test_site.current_version_id = version.id
    await db_session.commit()
    
    return version


@pytest.fixture
def edit_service(db_session):
    """Create EditService instance."""
    return EditService(db_session)


# ============================================================================
# CREATE TESTS
# ============================================================================

@pytest.mark.asyncio
class TestCreateEditRequest:
    """Tests for creating edit requests."""
    
    async def test_create_basic_edit_request(
        self,
        edit_service,
        test_site,
        test_customer
    ):
        """Test creating a basic edit request."""
        edit_request = await edit_service.create_edit_request(
            site_id=test_site.id,
            request_text="Change button color to blue",
            request_type=EditRequestType.STYLE,
            customer_id=test_customer.id
        )
        
        assert edit_request.id is not None
        assert edit_request.site_id == test_site.id
        assert edit_request.request_text == "Change button color to blue"
        assert edit_request.request_type == EditRequestType.STYLE
        assert edit_request.status == EditRequestStatus.PENDING
    
    async def test_create_without_type(
        self,
        edit_service,
        test_site,
        test_customer
    ):
        """Test creating edit request without specifying type."""
        edit_request = await edit_service.create_edit_request(
            site_id=test_site.id,
            request_text="Make the header bigger",
            customer_id=test_customer.id
        )
        
        assert edit_request.request_type is None
        assert edit_request.status == EditRequestStatus.PENDING
    
    async def test_create_fails_for_inactive_subscription(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test that edit request fails for inactive subscription."""
        test_site.subscription_status = "cancelled"
        await db_session.commit()
        
        with pytest.raises(BusinessLogicError) as exc:
            await edit_service.create_edit_request(
                site_id=test_site.id,
                request_text="Change something",
                customer_id=test_customer.id
            )
        
        assert "active subscription" in str(exc.value).lower()
    
    async def test_create_fails_for_wrong_customer(
        self,
        edit_service,
        test_site
    ):
        """Test that edit request fails for wrong customer."""
        wrong_customer_id = uuid4()
        
        with pytest.raises(PermissionDeniedError):
            await edit_service.create_edit_request(
                site_id=test_site.id,
                request_text="Change something",
                customer_id=wrong_customer_id
            )
    
    async def test_create_fails_when_too_many_pending(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test rate limiting: max 5 pending requests."""
        # Create 5 pending requests
        for i in range(5):
            request = EditRequest(
                site_id=test_site.id,
                request_text=f"Request {i}",
                status=EditRequestStatus.PENDING
            )
            db_session.add(request)
        await db_session.commit()
        
        # 6th should fail
        with pytest.raises(BusinessLogicError) as exc:
            await edit_service.create_edit_request(
                site_id=test_site.id,
                request_text="Too many requests",
                customer_id=test_customer.id
            )
        
        assert "too many" in str(exc.value).lower()


# ============================================================================
# READ TESTS
# ============================================================================

@pytest.mark.asyncio
class TestGetEditRequest:
    """Tests for retrieving edit requests."""
    
    async def test_get_existing_request(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test getting an existing edit request."""
        # Create request
        request = EditRequest(
            site_id=test_site.id,
            request_text="Test request",
            status=EditRequestStatus.PENDING
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        # Retrieve it
        retrieved = await edit_service.get_edit_request(
            request_id=request.id,
            customer_id=test_customer.id
        )
        
        assert retrieved.id == request.id
        assert retrieved.request_text == "Test request"
    
    async def test_get_nonexistent_request(self, edit_service):
        """Test getting a nonexistent request raises error."""
        fake_id = uuid4()
        
        with pytest.raises(ResourceNotFoundError):
            await edit_service.get_edit_request(fake_id)
    
    async def test_list_requests_for_site(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test listing edit requests for a site."""
        # Create multiple requests
        for i in range(3):
            request = EditRequest(
                site_id=test_site.id,
                request_text=f"Request {i}",
                status=EditRequestStatus.PENDING
            )
            db_session.add(request)
        await db_session.commit()
        
        # List them
        requests, total = await edit_service.list_edit_requests(
            site_id=test_site.id,
            customer_id=test_customer.id
        )
        
        assert len(requests) == 3
        assert total == 3
    
    async def test_list_with_status_filter(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test listing with status filter."""
        # Create requests with different statuses
        for status in [
            EditRequestStatus.PENDING,
            EditRequestStatus.PROCESSING,
            EditRequestStatus.APPROVED
        ]:
            request = EditRequest(
                site_id=test_site.id,
                request_text=f"Request {status}",
                status=status
            )
            db_session.add(request)
        await db_session.commit()
        
        # Filter by status
        requests, total = await edit_service.list_edit_requests(
            site_id=test_site.id,
            status=EditRequestStatus.PENDING,
            customer_id=test_customer.id
        )
        
        assert len(requests) == 1
        assert requests[0].status == EditRequestStatus.PENDING
    
    async def test_get_stats(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test getting edit request statistics."""
        # Create requests with various statuses
        for status in [
            EditRequestStatus.PENDING,
            EditRequestStatus.APPROVED,
            EditRequestStatus.DEPLOYED
        ]:
            request = EditRequest(
                site_id=test_site.id,
                request_text=f"Request {status}",
                status=status,
                request_type=EditRequestType.STYLE
            )
            db_session.add(request)
        await db_session.commit()
        
        # Get stats
        stats = await edit_service.get_edit_request_stats(
            site_id=test_site.id,
            customer_id=test_customer.id
        )
        
        assert stats["total_requests"] == 3
        assert stats["pending_requests"] == 1
        assert stats["approved_requests"] == 1
        assert stats["deployed_requests"] == 1
        assert stats["most_common_request_type"] == EditRequestType.STYLE


# ============================================================================
# UPDATE TESTS
# ============================================================================

@pytest.mark.asyncio
class TestUpdateEditRequest:
    """Tests for updating edit requests."""
    
    async def test_update_status(
        self,
        edit_service,
        test_site,
        db_session
    ):
        """Test updating request status."""
        request = EditRequest(
            site_id=test_site.id,
            request_text="Test request",
            status=EditRequestStatus.PENDING
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        # Update status
        updated = await edit_service.update_status(
            request_id=request.id,
            new_status=EditRequestStatus.PROCESSING
        )
        
        assert updated.status == EditRequestStatus.PROCESSING
        assert updated.processed_at is not None
    
    async def test_invalid_status_transition(
        self,
        edit_service,
        test_site,
        db_session
    ):
        """Test that invalid status transitions are rejected."""
        request = EditRequest(
            site_id=test_site.id,
            request_text="Test request",
            status=EditRequestStatus.PENDING
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        # Try invalid transition: pending -> approved (must go through processing first)
        with pytest.raises(ValidationError):
            await edit_service.update_status(
                request_id=request.id,
                new_status=EditRequestStatus.APPROVED
            )
    
    async def test_approve_edit(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test approving an edit request."""
        request = EditRequest(
            site_id=test_site.id,
            request_text="Test request",
            status=EditRequestStatus.READY_FOR_REVIEW
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        # Approve it
        approved = await edit_service.approve_edit(
            request_id=request.id,
            customer_id=test_customer.id,
            feedback="Looks great!"
        )
        
        assert approved.status == EditRequestStatus.APPROVED
        assert approved.customer_approved is True
        assert approved.customer_feedback == "Looks great!"
        assert approved.approved_at is not None
    
    async def test_approve_fails_wrong_status(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test that approval fails if status is wrong."""
        request = EditRequest(
            site_id=test_site.id,
            request_text="Test request",
            status=EditRequestStatus.PENDING  # Wrong status
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        with pytest.raises(BusinessLogicError):
            await edit_service.approve_edit(
                request_id=request.id,
                customer_id=test_customer.id
            )
    
    async def test_reject_edit(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test rejecting an edit request."""
        request = EditRequest(
            site_id=test_site.id,
            request_text="Test request",
            status=EditRequestStatus.READY_FOR_REVIEW
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        # Reject it
        rejected = await edit_service.reject_edit(
            request_id=request.id,
            customer_id=test_customer.id,
            reason="Color is too bright"
        )
        
        assert rejected.status == EditRequestStatus.REJECTED
        assert rejected.customer_approved is False
        assert rejected.rejected_reason == "Color is too bright"


# ============================================================================
# DELETE TESTS
# ============================================================================

@pytest.mark.asyncio
class TestCancelEditRequest:
    """Tests for canceling edit requests."""
    
    async def test_cancel_pending_request(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test canceling a pending request."""
        request = EditRequest(
            site_id=test_site.id,
            request_text="Test request",
            status=EditRequestStatus.PENDING
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        request_id = request.id
        
        # Cancel it
        await edit_service.cancel_edit_request(
            request_id=request_id,
            customer_id=test_customer.id
        )
        
        # Verify it's deleted
        with pytest.raises(ResourceNotFoundError):
            await edit_service.get_edit_request(request_id)
    
    async def test_cancel_fails_approved_request(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test that canceling approved request fails."""
        request = EditRequest(
            site_id=test_site.id,
            request_text="Test request",
            status=EditRequestStatus.APPROVED
        )
        db_session.add(request)
        await db_session.commit()
        await db_session.refresh(request)
        
        with pytest.raises(BusinessLogicError):
            await edit_service.cancel_edit_request(
                request_id=request.id,
                customer_id=test_customer.id
            )


# ============================================================================
# WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
class TestEditRequestWorkflow:
    """Tests for complete edit request workflows."""
    
    async def test_complete_approval_workflow(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test complete workflow from creation to approval."""
        # 1. Create request
        request = await edit_service.create_edit_request(
            site_id=test_site.id,
            request_text="Change button color",
            request_type=EditRequestType.STYLE,
            customer_id=test_customer.id
        )
        assert request.status == EditRequestStatus.PENDING
        
        # 2. Process it
        request = await edit_service.update_status(
            request_id=request.id,
            new_status=EditRequestStatus.PROCESSING
        )
        assert request.status == EditRequestStatus.PROCESSING
        
        # 3. Ready for review
        request = await edit_service.update_status(
            request_id=request.id,
            new_status=EditRequestStatus.READY_FOR_REVIEW,
            ai_confidence=Decimal("0.85")
        )
        assert request.status == EditRequestStatus.READY_FOR_REVIEW
        
        # 4. Approve
        request = await edit_service.approve_edit(
            request_id=request.id,
            customer_id=test_customer.id,
            feedback="Perfect!"
        )
        assert request.status == EditRequestStatus.APPROVED
        
        # 5. Deploy
        request = await edit_service.update_status(
            request_id=request.id,
            new_status=EditRequestStatus.DEPLOYED
        )
        assert request.status == EditRequestStatus.DEPLOYED
        assert request.deployed_at is not None
    
    async def test_rejection_workflow(
        self,
        edit_service,
        test_site,
        test_customer,
        db_session
    ):
        """Test workflow with rejection."""
        # Create and process
        request = await edit_service.create_edit_request(
            site_id=test_site.id,
            request_text="Change something",
            customer_id=test_customer.id
        )
        
        request = await edit_service.update_status(
            request_id=request.id,
            new_status=EditRequestStatus.PROCESSING
        )
        
        request = await edit_service.update_status(
            request_id=request.id,
            new_status=EditRequestStatus.READY_FOR_REVIEW
        )
        
        # Reject
        request = await edit_service.reject_edit(
            request_id=request.id,
            customer_id=test_customer.id,
            reason="Not what I wanted"
        )
        
        assert request.status == EditRequestStatus.REJECTED
        assert request.customer_approved is False


# ============================================================================
# HELPER TESTS
# ============================================================================

@pytest.mark.asyncio
class TestEditServiceHelpers:
    """Tests for helper methods."""
    
    async def test_validate_site_access(
        self,
        edit_service,
        test_site,
        test_customer
    ):
        """Test site access validation."""
        # Should succeed
        site = await edit_service._validate_site_access(
            test_site.id,
            test_customer.id
        )
        assert site.id == test_site.id
        
        # Should fail with wrong customer
        with pytest.raises(PermissionDeniedError):
            await edit_service._validate_site_access(
                test_site.id,
                uuid4()
            )
    
    async def test_count_pending_requests(
        self,
        edit_service,
        test_site,
        db_session
    ):
        """Test counting pending requests."""
        # Create 3 pending, 2 completed
        for i in range(3):
            request = EditRequest(
                site_id=test_site.id,
                request_text=f"Pending {i}",
                status=EditRequestStatus.PENDING
            )
            db_session.add(request)
        
        for i in range(2):
            request = EditRequest(
                site_id=test_site.id,
                request_text=f"Completed {i}",
                status=EditRequestStatus.DEPLOYED
            )
            db_session.add(request)
        
        await db_session.commit()
        
        # Count should be 3
        count = await edit_service._count_pending_requests(test_site.id)
        assert count == 3

