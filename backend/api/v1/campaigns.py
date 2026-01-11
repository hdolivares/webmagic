"""
Campaigns API endpoints - email outreach management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from core.database import get_db
from api.deps import get_current_user
from api.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignStats,
    BulkCampaignCreate,
    EmailTestRequest
)
from services.pitcher.campaign_service import CampaignService
from services.pitcher.email_sender import EmailSender
from services.pitcher.tracking import EmailTracker
from models.user import AdminUser

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Create a new email campaign."""
    service = CampaignService(db)
    
    campaign = await service.create_campaign(
        business_id=campaign_data.business_id,
        site_id=campaign_data.site_id,
        variant=campaign_data.variant,
        scheduled_for=campaign_data.scheduled_for
    )
    
    await db.commit()
    
    return CampaignResponse.model_validate(campaign)


@router.post("/bulk", response_model=dict)
async def create_bulk_campaigns(
    bulk_data: BulkCampaignCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Create campaigns for multiple businesses in background."""
    service = CampaignService(db)
    
    # Create campaigns in background
    async def create_task():
        campaigns = await service.bulk_create_campaigns(
            business_ids=bulk_data.business_ids,
            variant=bulk_data.variant
        )
        await db.commit()
    
    background_tasks.add_task(create_task)
    
    return {
        "status": "processing",
        "message": f"Creating {len(bulk_data.business_ids)} campaigns",
        "business_count": len(bulk_data.business_ids)
    }


@router.get("/", response_model=CampaignListResponse)
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    business_id: Optional[UUID] = Query(None, description="Filter by business"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """List all campaigns with pagination."""
    service = CampaignService(db)
    
    skip = (page - 1) * page_size
    campaigns, total = await service.list_campaigns(
        skip=skip,
        limit=page_size,
        status=status,
        business_id=business_id
    )
    
    pages = (total + page_size - 1) // page_size
    
    return CampaignListResponse(
        campaigns=[CampaignResponse.model_validate(c) for c in campaigns],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/stats", response_model=CampaignStats)
async def get_campaign_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get campaign statistics."""
    service = CampaignService(db)
    stats = await service.get_stats()
    return CampaignStats(**stats)


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get a specific campaign by ID."""
    service = CampaignService(db)
    campaign = await service.get_campaign(campaign_id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return CampaignDetailResponse.model_validate(campaign)


@router.post("/{campaign_id}/send")
async def send_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Send a campaign email."""
    service = CampaignService(db)
    
    success = await service.send_campaign(campaign_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send campaign")
    
    return {
        "status": "sent",
        "campaign_id": str(campaign_id),
        "message": "Campaign sent successfully"
    }


@router.get("/pending/list")
async def list_pending_campaigns(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get pending campaigns ready to be sent."""
    service = CampaignService(db)
    campaigns = await service.get_pending_campaigns(limit=limit)
    
    return {
        "count": len(campaigns),
        "campaigns": [CampaignResponse.model_validate(c) for c in campaigns]
    }


@router.post("/test-email")
async def send_test_email(
    test_data: EmailTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Send a test email to verify email configuration."""
    sender = EmailSender()
    
    try:
        result = await sender.send_test_email(
            to_email=test_data.to_email,
            subject=test_data.subject
        )
        
        return {
            "status": "sent",
            "message": f"Test email sent to {test_data.to_email}",
            "provider": result.get("provider"),
            "message_id": result.get("message_id")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test email: {str(e)}"
        )


# Tracking endpoints (public - no auth required)
@router.get("/track/open/{campaign_id}")
async def track_email_open(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Track email open (tracking pixel endpoint)."""
    tracker = EmailTracker(db)
    await tracker.record_open(campaign_id)
    
    # Return 1x1 transparent PNG
    from fastapi.responses import Response
    import base64
    
    # 1x1 transparent PNG
    pixel = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    
    return Response(content=pixel, media_type="image/png")


@router.get("/track/click/{campaign_id}")
async def track_email_click(
    campaign_id: UUID,
    link_id: Optional[str] = Query(None),
    redirect_url: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Track email click and redirect."""
    tracker = EmailTracker(db)
    await tracker.record_click(campaign_id, link_id=link_id)
    
    # Redirect to destination
    if redirect_url:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=redirect_url)
    
    return {"status": "tracked"}
