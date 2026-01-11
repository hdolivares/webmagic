"""
Generated Sites API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
import logging

from core.database import get_db
from api.deps import get_current_user
from api.schemas.site import (
    SiteGenerateRequest,
    SiteResponse,
    SiteDetailResponse,
    SiteListResponse,
    SiteGenerationResult,
    SiteUpdate,
    SiteStats
)
from services.hunter.business_service import BusinessService
from services.creative.site_service import SiteService
from services.creative.orchestrator import CreativeOrchestrator
from models.user import AdminUser

router = APIRouter(prefix="/sites", tags=["sites"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=SiteGenerationResult)
async def generate_site(
    request: SiteGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Generate a new website for a business.
    Runs the complete AI pipeline (Analyst → Concept → Director → Architect).
    """
    business_service = BusinessService(db)
    site_service = SiteService(db)
    
    # Get business
    business = await business_service.get_business(request.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check if site already exists
    existing_sites = await site_service.get_sites_by_business(
        request.business_id,
        status="live"
    )
    
    if existing_sites and not request.force_regenerate:
        raise HTTPException(
            status_code=400,
            detail="Site already exists for this business. Use force_regenerate=true to regenerate."
        )
    
    # Generate site in background
    async def generate_task():
        try:
            # Initialize orchestrator
            orchestrator = CreativeOrchestrator(db)
            
            # Prepare business data
            business_data = {
                "id": str(business.id),
                "name": business.name,
                "category": business.category,
                "city": business.city,
                "state": business.state,
                "country": business.country,
                "phone": business.phone,
                "email": business.email,
                "rating": float(business.rating) if business.rating else 0,
                "review_count": business.review_count,
                "reviews_data": [],  # TODO: Add actual reviews
                "photos_urls": business.photos_urls or []
            }
            
            # Run generation pipeline
            results = await orchestrator.generate_website(business_data)
            
            # Extract website code
            website = results.get("website", {})
            
            # Generate subdomain
            subdomain = await site_service.generate_subdomain(business.name)
            
            # Create site record
            site = await site_service.create_site(
                business_id=business.id,
                subdomain=subdomain,
                html_content=website.get("html", ""),
                css_content=website.get("css", ""),
                js_content=website.get("js", ""),
                design_brief=results.get("design_brief", {}),
                assets_urls=website.get("assets_needed", []),
                status="preview"
            )
            
            # Update business status
            await business_service.update_business(
                business.id,
                {"website_status": "generated"}
            )
            
            await db.commit()
            
            logger.info(f"Site generated successfully: {subdomain}")
            
        except Exception as e:
            logger.error(f"Site generation failed: {str(e)}", exc_info=True)
            await db.rollback()
    
    background_tasks.add_task(generate_task)
    
    return SiteGenerationResult(
        site_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
        status="generating",
        message=f"Site generation started for {business.name}",
        duration_ms=None,
        summary=None
    )


@router.get("/", response_model=SiteListResponse)
async def list_sites(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """List all generated sites with pagination."""
    service = SiteService(db)
    
    skip = (page - 1) * page_size
    sites, total = await service.list_sites(
        skip=skip,
        limit=page_size,
        status=status
    )
    
    pages = (total + page_size - 1) // page_size
    
    return SiteListResponse(
        sites=[SiteResponse.model_validate(s) for s in sites],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/stats", response_model=SiteStats)
async def get_site_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get site statistics."""
    service = SiteService(db)
    stats = await service.get_stats()
    return SiteStats(**stats)


@router.get("/{site_id}", response_model=SiteDetailResponse)
async def get_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Get a specific site by ID with full content."""
    service = SiteService(db)
    site = await service.get_site(site_id)
    
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    return SiteDetailResponse.model_validate(site)


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: UUID,
    updates: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Update a site."""
    service = SiteService(db)
    
    # Get existing site
    existing = await service.get_site(site_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Site not found")
    
    # Apply updates
    update_dict = updates.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated = await service.update_site(site_id, update_dict)
    await db.commit()
    
    return SiteResponse.model_validate(updated)


@router.post("/{site_id}/deploy")
async def deploy_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """Deploy site to live status."""
    service = SiteService(db)
    
    site = await service.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    await service.update_site(
        site_id,
        {
            "status": "live",
            "deployed_at": datetime.utcnow()
        }
    )
    await db.commit()
    
    return {
        "message": "Site deployed successfully",
        "site_id": str(site_id),
        "url": site.full_url
    }


from datetime import datetime
