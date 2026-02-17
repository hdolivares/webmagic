"""
URL Shortener Admin API - CRUD, analytics, and configuration.

All endpoints require admin authentication.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from models.user import AdminUser
from services.shortener import ShortLinkService
from services.system_settings_service import SystemSettingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shortener", tags=["URL Shortener"])


# ── Request / Response schemas ───────────────────────────────


class CreateShortLinkRequest(BaseModel):
    """Create a new short link."""
    destination_url: str = Field(..., min_length=1, description="Full destination URL")
    link_type: str = Field("custom", description="Link type: site_preview, campaign, custom, other")
    custom_slug: Optional[str] = Field(None, description="Optional custom slug (must be unique)")
    business_id: Optional[UUID] = None
    site_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None


class ShortLinkResponse(BaseModel):
    """Short link details."""
    id: str
    slug: str
    destination_url: str
    short_url: str
    link_type: str
    is_active: bool
    expires_at: Optional[str]
    click_count: int
    last_clicked_at: Optional[str]
    business_id: Optional[str]
    site_id: Optional[str]
    campaign_id: Optional[str]
    created_at: str


class ShortenerStatsResponse(BaseModel):
    """Aggregate shortener statistics."""
    total_links: int
    active_links: int
    total_clicks: int
    links_by_type: dict


class ShortenerConfigResponse(BaseModel):
    """Current shortener configuration."""
    domain: str
    protocol: str
    slug_length: int
    default_expiry_days: int
    enabled: bool


# ── Helpers ──────────────────────────────────────────────────

def _serialize_link(link, domain: str, protocol: str) -> dict:
    """Convert a ShortLink ORM object to a serialisable dict."""
    short_url = ShortLinkService._build_short_url(link.slug, domain, protocol) if domain else f"/r/{link.slug}"
    return {
        "id": str(link.id),
        "slug": link.slug,
        "destination_url": link.destination_url,
        "short_url": short_url,
        "link_type": link.link_type,
        "is_active": link.is_active,
        "expires_at": link.expires_at.isoformat() if link.expires_at else None,
        "click_count": link.click_count,
        "last_clicked_at": link.last_clicked_at.isoformat() if link.last_clicked_at else None,
        "business_id": str(link.business_id) if link.business_id else None,
        "site_id": str(link.site_id) if link.site_id else None,
        "campaign_id": str(link.campaign_id) if link.campaign_id else None,
        "created_at": link.created_at.isoformat() if link.created_at else None,
    }


# ── Endpoints ────────────────────────────────────────────────


@router.post("/links")
async def create_short_link(
    request: CreateShortLinkRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new short link manually."""
    try:
        short_url = await ShortLinkService.create_short_link(
            db,
            destination_url=request.destination_url,
            link_type=request.link_type,
            custom_slug=request.custom_slug,
            business_id=request.business_id,
            site_id=request.site_id,
            campaign_id=request.campaign_id,
        )
        await db.commit()
        return {"success": True, "short_url": short_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create short link: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create short link: {str(e)}")


@router.get("/links")
async def list_short_links(
    link_type: Optional[str] = Query(None, description="Filter by link type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List short links with pagination and optional filters."""
    try:
        result = await ShortLinkService.list_links(
            db,
            link_type=link_type,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )
        config = await ShortLinkService._get_shortener_config(db)

        return {
            "items": [
                _serialize_link(link, config["domain"], config["protocol"])
                for link in result["items"]
            ],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        }
    except Exception as e:
        logger.error("Failed to list short links: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/links/{link_id}")
async def get_short_link(
    link_id: UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single short link with full details."""
    link = await ShortLinkService.get_link_by_id(db, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Short link not found")

    config = await ShortLinkService._get_shortener_config(db)
    return _serialize_link(link, config["domain"], config["protocol"])


@router.delete("/links/{link_id}")
async def deactivate_short_link(
    link_id: UUID,
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate (soft-delete) a short link."""
    success = await ShortLinkService.deactivate(db, link_id)
    if not success:
        raise HTTPException(status_code=404, detail="Short link not found")
    return {"success": True, "message": "Short link deactivated"}


@router.get("/stats")
async def get_shortener_stats(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate shortener statistics."""
    try:
        stats = await ShortLinkService.get_stats(db)
        return stats
    except Exception as e:
        logger.error("Failed to get shortener stats: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_shortener_config(
    current_user: AdminUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current shortener configuration."""
    try:
        config = await ShortLinkService._get_shortener_config(db)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
