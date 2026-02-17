"""
Public redirect handler for the URL shortener.

Mounted at the top level (not under /api/v1/) so that short URLs
resolve via a simple path like GET /r/{slug}.

With Nginx, the short domain (e.g., wm.gt) rewrites:
    https://wm.gt/a1B2c3  ->  GET /r/a1B2c3  on the backend

This keeps the /r/ prefix invisible to end users while avoiding
route conflicts with the API router.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.shortener import ShortLinkService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Redirect"])


@router.get("/r/{slug}")
async def redirect_short_link(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve a short link slug and redirect (302) to the destination URL.

    Public endpoint — no authentication required.
    Increments the link's click counter on each successful redirect.

    Returns:
        302 redirect to the destination URL.
        404 if the slug is unknown, inactive, or expired.
    """
    destination = await ShortLinkService.resolve(db, slug)

    if destination is None:
        logger.debug("Short link not found or not resolvable: %s", slug)
        raise HTTPException(status_code=404, detail="Link not found or has expired")

    return RedirectResponse(url=destination, status_code=302)
