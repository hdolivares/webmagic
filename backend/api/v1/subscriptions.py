"""
Subscription API Endpoints

Handles monthly subscription management ($95/month).

Author: WebMagic Team
Date: January 21, 2026
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.database import get_db
from core.customer_security import get_current_customer, get_current_active_customer
from core.exceptions import NotFoundError, ValidationError, ConflictError
from api.schemas.subscription import (
    SubscriptionActivateRequest,
    SubscriptionActivateResponse,
    SubscriptionResponse,
    SubscriptionCancelRequest,
    SubscriptionCancelResponse,
    SubscriptionStatisticsResponse
)
from api.schemas.customer_auth import MessageResponse, ErrorResponse
from models.site_models import CustomerUser
from services.subscription_service import get_subscription_service
from services.emails.email_service import get_email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post(
    "/activate",
    response_model=SubscriptionActivateResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Site not found"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        409: {"model": ErrorResponse, "description": "Already subscribed"}
    },
    summary="Activate monthly subscription",
    description="Activate $95/month subscription for site hosting and features."
)
async def activate_subscription(
    request: SubscriptionActivateRequest,
    current_customer: CustomerUser = Depends(get_current_active_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Activate $95/month subscription.
    
    **Requirements:**
    - Email must be verified
    - Must own a site
    - Site must be in 'owned' status
    
    **Process:**
    1. Create subscription in Recurrente
    2. Return payment URL (if needed)
    3. Webhook activates after payment confirmed
    
    **After Activation:**
    - Site status: owned → active
    - Custom domain enabled
    - AI edits enabled
    - Billing starts
    """
    try:
        if not current_customer.site_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You don't own a site yet. Purchase a site first."
            )
        
        subscription_service = get_subscription_service()
        
        # Create subscription
        result = await subscription_service.create_subscription(
            db=db,
            site_id=current_customer.site_id,
            customer_id=current_customer.id,
            payment_method_token=request.payment_method_token
        )
        
        logger.info(
            f"Subscription activation initiated for customer {current_customer.email}"
        )
        
        return SubscriptionActivateResponse(
            subscription_id=result["subscription_id"],
            payment_url=result.get("payment_url"),
            status=result["status"],
            monthly_amount=result["monthly_amount"],
            message="Subscription created successfully! Please complete payment to activate."
        )
    
    except (NotFoundError, ValidationError, ConflictError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Subscription activation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate subscription. Please try again."
        )


@router.get(
    "/status",
    response_model=SubscriptionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Site not found"}
    },
    summary="Get subscription status",
    description="Get current subscription status for authenticated customer."
)
async def get_subscription_status(
    current_customer: CustomerUser = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscription status.
    
    Returns subscription details including:
    - Status (active, past_due, cancelled, etc.)
    - Billing dates
    - Grace period info
    """
    try:
        if not current_customer.site_id:
            # No site, no subscription
            return SubscriptionResponse(
                subscription_id=None,
                status="none",
                monthly_amount=95.00,
                started_at=None,
                next_billing_date=None,
                ends_at=None,
                grace_period_ends=None,
                is_active=False,
                is_past_due=False,
                is_cancelled=False
            )
        
        subscription_service = get_subscription_service()
        status_data = await subscription_service.get_subscription_status(
            db=db,
            site_id=current_customer.site_id
        )
        
        return SubscriptionResponse(**status_data)
    
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Get subscription status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription status."
        )


@router.post(
    "/cancel",
    response_model=SubscriptionCancelResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No subscription found"},
        400: {"model": ErrorResponse, "description": "Cannot cancel"}
    },
    summary="Cancel subscription",
    description="Cancel monthly subscription (immediate or at period end)."
)
async def cancel_subscription(
    request: SubscriptionCancelRequest,
    current_customer: CustomerUser = Depends(get_current_active_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel subscription.
    
    **Options:**
    - `immediate=False` (default): Cancel at end of billing period
    - `immediate=True`: Cancel immediately (lose remaining time)
    
    **After Cancellation:**
    - Billing stops
    - Site downgrade: active → owned
    - Custom domain disabled
    - AI edits disabled
    """
    try:
        if not current_customer.site_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No site found"
            )
        
        subscription_service = get_subscription_service()
        
        site = await subscription_service.cancel_subscription(
            db=db,
            site_id=current_customer.site_id,
            immediate=request.immediate,
            reason=request.reason
        )
        
        # Send cancellation email
        email_service = get_email_service()
        await email_service.send_subscription_cancelled_email(
            to_email=current_customer.email,
            customer_name=current_customer.full_name or current_customer.email.split('@')[0],
            site_title=site.site_title or site.slug,
            immediate=request.immediate,
            ends_at=site.subscription_ends_at
        )
        
        logger.info(
            f"Subscription cancelled for customer {current_customer.email}, "
            f"immediate={request.immediate}"
        )
        
        message = (
            "Subscription cancelled immediately. Access removed."
            if request.immediate
            else f"Subscription will cancel on {site.subscription_ends_at.date()}. "
                 "You'll have access until then."
        )
        
        return SubscriptionCancelResponse(
            subscription_id=site.subscription_id,
            status=site.subscription_status,
            ends_at=site.subscription_ends_at,
            message=message,
            immediate=request.immediate
        )
    
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Cancel subscription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription."
        )


@router.post(
    "/reactivate",
    response_model=SubscriptionActivateResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Site not found"},
        400: {"model": ErrorResponse, "description": "Cannot reactivate"}
    },
    summary="Reactivate cancelled subscription",
    description="Reactivate a previously cancelled subscription."
)
async def reactivate_subscription(
    current_customer: CustomerUser = Depends(get_current_active_customer),
    db: AsyncSession = Depends(get_db)
):
    """
    Reactivate subscription.
    
    Available for:
    - Cancelled subscriptions
    - Expired subscriptions
    
    Creates new subscription with same terms.
    """
    try:
        if not current_customer.site_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No site found"
            )
        
        subscription_service = get_subscription_service()
        
        result = await subscription_service.reactivate_subscription(
            db=db,
            site_id=current_customer.site_id
        )
        
        logger.info(f"Subscription reactivated for customer {current_customer.email}")
        
        return SubscriptionActivateResponse(
            subscription_id=result["subscription_id"],
            payment_url=result.get("payment_url"),
            status=result.get("status", "pending"),
            monthly_amount=95.00,
            message="Subscription reactivated successfully!"
        )
    
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Reactivate subscription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate subscription."
        )


# Admin endpoint
@router.get(
    "/admin/statistics",
    response_model=SubscriptionStatisticsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"}
    },
    summary="Get subscription statistics",
    description="Get subscription statistics for admin dashboard."
)
async def get_subscription_statistics(
    db: AsyncSession = Depends(get_db)
    # TODO: Add admin authentication
):
    """
    Get subscription statistics.
    
    **Admin only.**
    
    Returns:
    - Active subscriptions count
    - Past due count
    - Cancelled count
    - MRR (Monthly Recurring Revenue)
    - Churn rate
    """
    try:
        from sqlalchemy import select, func
        from models.site_models import Site
        
        # Count by status
        active_result = await db.execute(
            select(func.count(Site.id)).where(Site.subscription_status == "active")
        )
        total_active = active_result.scalar()
        
        past_due_result = await db.execute(
            select(func.count(Site.id)).where(Site.subscription_status == "past_due")
        )
        total_past_due = past_due_result.scalar()
        
        cancelled_result = await db.execute(
            select(func.count(Site.id)).where(Site.subscription_status == "cancelled")
        )
        total_cancelled = cancelled_result.scalar()
        
        # Calculate MRR
        mrr_result = await db.execute(
            select(func.sum(Site.monthly_amount)).where(
                Site.subscription_status.in_(["active", "past_due"])
            )
        )
        mrr = float(mrr_result.scalar() or 0)
        
        # Calculate churn rate (simplified)
        total_ever = total_active + total_past_due + total_cancelled
        churn_rate = (total_cancelled / total_ever) if total_ever > 0 else 0
        
        return SubscriptionStatisticsResponse(
            total_active=total_active,
            total_past_due=total_past_due,
            total_cancelled=total_cancelled,
            monthly_recurring_revenue=mrr,
            churn_rate=churn_rate,
            recent_subscriptions=[]
        )
    
    except Exception as e:
        logger.error(f"Get subscription statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics."
        )
