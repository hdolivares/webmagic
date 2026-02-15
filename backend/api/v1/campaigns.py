"""
Campaigns API endpoints - multi-channel outreach management (Email + SMS).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

from core.database import get_db
from api.deps import get_current_user
from api.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignStats,
    BulkCampaignCreate,
    EmailTestRequest,
    ReadyBusinessResponse,
    ReadyBusinessesListResponse,
    SMSPreviewRequest,
    SMSPreviewResponse,
    BulkCampaignCreateResponse
)
from services.pitcher.campaign_service import CampaignService
from services.pitcher.email_sender import EmailSender
from services.pitcher.tracking import EmailTracker
from services.sms import SMSGenerator
from services.system_settings_service import SystemSettingsService
from models.user import AdminUser
from models.business import Business
from models.site import GeneratedSite
from sqlalchemy import select, and_

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


@router.post("/bulk", response_model=BulkCampaignCreateResponse)
async def create_bulk_campaigns(
    bulk_data: BulkCampaignCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Create campaigns for multiple businesses.
    
    Supports both email and SMS campaigns with intelligent channel selection.
    Optionally send immediately or schedule for later.
    """
    service = CampaignService(db)
    
    campaigns = []
    by_channel = {"email": 0, "sms": 0}
    total_sms_cost = 0.0
    
    # Create campaigns for each business
    for business_id in bulk_data.business_ids:
        try:
            campaign = await service.create_campaign(
                business_id=business_id,
                channel=bulk_data.channel,
                variant=bulk_data.variant,
                scheduled_for=bulk_data.scheduled_for
            )
            campaigns.append(campaign.id)
            
            # Track channel usage
            by_channel[campaign.channel] = by_channel.get(campaign.channel, 0) + 1
            
            # Calculate SMS cost
            if campaign.channel == "sms" and campaign.sms_body:
                segments = len(campaign.sms_body) // 160 + (1 if len(campaign.sms_body) % 160 else 0)
                total_sms_cost += segments * 0.0079  # Twilio US rate
                
        except Exception as e:
            logger.warning(f"Failed to create campaign for {business_id}: {e}")
            continue
    
    await db.commit()
    
    # Send immediately if requested
    if bulk_data.send_immediately:
        async def send_task():
            for campaign_id in campaigns:
                try:
                    await service.send_campaign(campaign_id)
                except Exception as e:
                    logger.error(f"Failed to send campaign {campaign_id}: {e}")
        
        background_tasks.add_task(send_task)
    
    return BulkCampaignCreateResponse(
        status="success" if campaigns else "partial",
        message=f"Created {len(campaigns)}/{len(bulk_data.business_ids)} campaigns",
        total_queued=len(campaigns),
        by_channel=by_channel,
        estimated_sms_cost=round(total_sms_cost, 4),
        campaigns_created=campaigns
    )


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


# Static paths MUST be declared before /{campaign_id} or "ready-businesses" is matched as campaign_id (422)
@router.get("/ready-businesses")
async def get_ready_businesses(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get businesses with completed generated sites ready for campaigns.
    
    Returns businesses that:
    - Have a completed generated site
    - Don't already have an existing website
    - Meet qualification criteria (score >= 70)
    - Have at least one contact method (email or phone)
    - Are located in the United States (US only - SMS integration limitation)
    
    Returns plain JSON (no response_model) to avoid Pydantic V2 response validation issues.
    """
    from fastapi.responses import JSONResponse
    
    result = await db.execute(
        select(Business, GeneratedSite)
        .join(GeneratedSite, GeneratedSite.business_id == Business.id)
        .where(
            and_(
                Business.website_validation_status == 'triple_verified',
                Business.website_url.is_(None),
                Business.qualification_score >= 70,
                GeneratedSite.status == 'completed',
                Business.country == 'US'  # SMS integration only works for US
            )
        )
        .order_by(GeneratedSite.created_at.desc())
    )
    
    businesses_with_sites = result.all()
    ready_businesses = []
    with_email = 0
    with_phone = 0
    sms_only = 0
    email_only = 0
    
    for business, site in businesses_with_sites:
        has_email = bool(business.email)
        has_phone = bool(business.phone)
        if not has_email and not has_phone:
            continue
        available_channels = []
        if has_email:
            available_channels.append("email")
            with_email += 1
        if has_phone:
            available_channels.append("sms")
            with_phone += 1
        if has_email and not has_phone:
            email_only += 1
        elif has_phone and not has_email:
            sms_only += 1
        recommended_channel = "email" if has_email else "sms"
        site_url = f"https://sites.lavish.solutions/{site.subdomain}"
        ready_businesses.append({
            "id": str(business.id),
            "name": business.name or "",
            "category": business.category,
            "city": business.city,
            "state": business.state,
            "country": business.country or "US",
            "phone": business.phone,
            "email": business.email,
            "rating": float(business.rating) if business.rating is not None else None,
            "review_count": business.review_count,
            "qualification_score": business.qualification_score,
            "site_id": str(site.id),
            "site_subdomain": site.subdomain,
            "site_url": site_url,
            "site_created_at": site.created_at.isoformat() if site.created_at else None,
            "available_channels": available_channels,
            "recommended_channel": recommended_channel,
        })
    
    return JSONResponse(content={
        "businesses": ready_businesses,
        "total": len(ready_businesses),
        "with_email": with_email,
        "with_phone": with_phone,
        "sms_only": sms_only,
        "email_only": email_only,
    })


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


# ============================================================================
# CAMPAIGN CREATION UI (preview-sms; ready-businesses is above, before /{campaign_id})
# ============================================================================

@router.post("/preview-sms", response_model=SMSPreviewResponse)
async def preview_sms_message(
    preview_request: SMSPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Preview SMS message for a business before sending.
    
    Uses AI to generate the SMS with the specified tone variant,
    and returns character count, segment count, and estimated cost.
    """
    # Get business and site
    result = await db.execute(
        select(Business, GeneratedSite)
        .join(GeneratedSite, GeneratedSite.business_id == Business.id)
        .where(
            and_(
                Business.id == preview_request.business_id,
                GeneratedSite.status == 'completed'
            )
        )
    )
    
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Business not found or site not completed"
        )
    
    business, site = row
    
    if not business.phone:
        raise HTTPException(
            status_code=400,
            detail="Business has no phone number for SMS"
        )
    
    # Build site URL
    site_url = f"https://sites.lavish.solutions/{site.subdomain}"
    
    # Prepare business data
    business_data = {
        "name": business.name,
        "category": business.category,
        "city": business.city,
        "state": business.state,
        "rating": float(business.rating) if business.rating else 0
    }
    
    # Use custom template from Settings > Messaging if set
    templates = await SystemSettingsService.get_messaging_templates(db)
    template_key = f"messaging_sms_template_{preview_request.variant}"
    raw = (templates or {}).get(template_key)
    custom_template = (raw.strip() if raw else "") or None

    generator = SMSGenerator()
    sms_body = await generator.generate_sms(
        business_data=business_data,
        site_url=site_url,
        variant=preview_request.variant,
        custom_template=custom_template,
    )
    
    # Calculate metrics
    char_count = len(sms_body)
    segment_count = SMSGenerator.estimate_segments(sms_body)
    estimated_cost = SMSGenerator.estimate_cost(sms_body)
    
    return SMSPreviewResponse(
        business_id=business.id,
        business_name=business.name,
        sms_body=sms_body,
        character_count=char_count,
        segment_count=segment_count,
        estimated_cost=estimated_cost,
        site_url=site_url,
        variant=preview_request.variant
    )
