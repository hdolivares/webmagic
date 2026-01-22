"""
Draft Campaign API Endpoints

Provides endpoints for managing draft campaigns - the review and approval
workflow for businesses scraped in draft mode.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging

from core.database import get_db
from models.user import AdminUser
from api.v1.auth import get_current_user
from services.draft_campaign_service import DraftCampaignService

router = APIRouter(prefix="/draft-campaigns", tags=["draft-campaigns"])
logger = logging.getLogger(__name__)


# Request/Response Models

class DraftCampaignListResponse(BaseModel):
    """Response with list of draft campaigns."""
    campaigns: List[Dict[str, Any]]
    total: int


class DraftCampaignDetailResponse(BaseModel):
    """Response with detailed draft campaign information."""
    campaign: Dict[str, Any]
    businesses: List[Dict[str, Any]]


class ApproveRejectRequest(BaseModel):
    """Request to approve or reject a campaign."""
    campaign_id: str = Field(..., description="Draft campaign UUID")
    review_notes: Optional[str] = Field(None, description="Optional review notes")


class DraftCampaignStatsResponse(BaseModel):
    """Response with draft campaign statistics."""
    pending_campaigns: int
    approved_campaigns: int
    sent_campaigns: int
    rejected_campaigns: int
    total_campaigns: int
    total_pending_leads: int
    total_approved_leads: int
    total_sent_messages: int


# Endpoints

@router.get("/pending", response_model=DraftCampaignListResponse)
async def get_pending_campaigns(
    city: Optional[str] = None,
    state: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get all pending draft campaigns awaiting review.
    
    These are campaigns that have been scraped but no outreach has been sent yet.
    """
    try:
        service = DraftCampaignService(db)
        campaigns = await service.get_pending_campaigns(
            city=city,
            state=state,
            category=category,
            limit=limit
        )
        
        return DraftCampaignListResponse(
            campaigns=[c.to_dict() for c in campaigns],
            total=len(campaigns)
        )
        
    except Exception as e:
        logger.error(f"Failed to get pending campaigns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get campaigns: {str(e)}")


@router.get("/{campaign_id}", response_model=DraftCampaignDetailResponse)
async def get_campaign_detail(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get detailed information about a draft campaign, including all businesses.
    """
    try:
        service = DraftCampaignService(db)
        
        campaign = await service.get_campaign_by_id(UUID(campaign_id))
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        businesses = await service.get_campaign_businesses(UUID(campaign_id))
        
        return DraftCampaignDetailResponse(
            campaign=campaign.to_dict(),
            businesses=[{
                "id": str(b.id),
                "name": b.name,
                "website_url": b.website_url,
                "website_status": b.website_status,
                "phone": b.phone,
                "email": b.email,
                "address": b.address,
                "rating": b.rating,
                "review_count": b.review_count,
                "category": b.category,
                "qualification_score": b.qualification_score
            } for b in businesses]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get campaign detail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get campaign: {str(e)}")


@router.post("/approve")
async def approve_campaign(
    request: ApproveRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Approve a draft campaign.
    
    This marks the campaign as approved. The actual outreach sending
    should be triggered separately (e.g., via a background job).
    """
    try:
        service = DraftCampaignService(db)
        
        campaign = await service.approve_campaign(
            campaign_id=UUID(request.campaign_id),
            reviewed_by=current_user.email,
            review_notes=request.review_notes
        )
        
        return {
            "status": "success",
            "message": f"Campaign approved: {campaign.qualified_leads_count} leads ready for outreach",
            "campaign": campaign.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to approve campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve campaign: {str(e)}")


@router.post("/reject")
async def reject_campaign(
    request: ApproveRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Reject a draft campaign.
    
    This marks the campaign as rejected. No outreach will be sent.
    """
    try:
        service = DraftCampaignService(db)
        
        campaign = await service.reject_campaign(
            campaign_id=UUID(request.campaign_id),
            reviewed_by=current_user.email,
            review_notes=request.review_notes
        )
        
        return {
            "status": "success",
            "message": f"Campaign rejected",
            "campaign": campaign.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reject campaign: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reject campaign: {str(e)}")


@router.get("/stats", response_model=DraftCampaignStatsResponse)
async def get_campaign_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get statistics about all draft campaigns.
    """
    try:
        service = DraftCampaignService(db)
        stats = await service.get_campaign_stats()
        
        return DraftCampaignStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get campaign stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

