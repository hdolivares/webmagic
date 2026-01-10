"""
Coverage Grid and Scraping API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from core.database import get_db
from api.deps import get_current_user
from api.schemas.coverage import (
    CoverageResponse,
    CoverageListResponse,
    CoverageStats,
    CoverageUpdate,
    CoverageCreate,
    ScrapeRequest,
    ScrapeResponse
)
from services.hunter.coverage_service import CoverageService
from services.hunter.hunter_service import HunterService
from models.user import AdminUser

router = APIRouter(prefix="/coverage", tags=["coverage"])


@router.get("/", response_model=CoverageListResponse)
async def list_coverage(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    state: Optional[str] = Query(None, description="Filter by state"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    List coverage grid entries with pagination and filters.
    Requires authentication.
    """
    service = CoverageService(db)
    
    # Build filters
    filters = {}
    if status:
        filters["status"] = status
    if state:
        filters["state"] = state
    if industry:
        filters["industry"] = industry
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    # Get coverage entries
    coverage_entries, total = await service.list_coverage(
        skip=skip,
        limit=page_size,
        filters=filters if filters else None
    )
    
    # Calculate total pages
    pages = (total + page_size - 1) // page_size
    
    # Add computed properties to responses
    responses = []
    for entry in coverage_entries:
        response = CoverageResponse.model_validate(entry)
        response.conversion_rate = entry.conversion_rate
        response.qualification_rate = entry.qualification_rate
        responses.append(response)
    
    return CoverageListResponse(
        coverage_entries=responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/stats", response_model=CoverageStats)
async def get_coverage_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get coverage grid statistics.
    Requires authentication.
    """
    service = CoverageService(db)
    stats = await service.get_stats()
    return CoverageStats(**stats)


@router.get("/next-target")
async def get_next_target(
    limit: int = Query(1, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get next scraping target(s) based on priority.
    Requires authentication.
    """
    service = CoverageService(db)
    targets = await service.get_next_target(limit=limit, exclude_cooldown=True)
    
    if not targets:
        return {
            "message": "No scraping targets available",
            "targets": []
        }
    
    return {
        "message": f"Found {len(targets)} target(s)",
        "targets": [CoverageResponse.model_validate(t) for t in targets]
    }


@router.get("/{coverage_id}", response_model=CoverageResponse)
async def get_coverage(
    coverage_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get a specific coverage entry by ID.
    Requires authentication.
    """
    service = CoverageService(db)
    coverage = await service.get_coverage(coverage_id)
    
    if not coverage:
        raise HTTPException(status_code=404, detail="Coverage entry not found")
    
    response = CoverageResponse.model_validate(coverage)
    response.conversion_rate = coverage.conversion_rate
    response.qualification_rate = coverage.qualification_rate
    
    return response


@router.post("/", response_model=CoverageResponse, status_code=201)
async def create_coverage(
    coverage_data: CoverageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Create a new coverage entry.
    Requires authentication.
    """
    service = CoverageService(db)
    
    # Check if already exists
    existing = await service.get_coverage_by_key(
        state=coverage_data.state,
        city=coverage_data.city,
        industry=coverage_data.industry,
        country=coverage_data.country
    )
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Coverage entry already exists for this location and industry"
        )
    
    # Create new coverage
    coverage = await service.create_coverage(**coverage_data.model_dump())
    await db.commit()
    
    return CoverageResponse.model_validate(coverage)


@router.patch("/{coverage_id}", response_model=CoverageResponse)
async def update_coverage(
    coverage_id: UUID,
    updates: CoverageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Update a coverage entry.
    Requires authentication.
    """
    service = CoverageService(db)
    
    # Get existing coverage
    existing = await service.get_coverage(coverage_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Coverage entry not found")
    
    # Apply updates
    update_dict = updates.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated = await service.update_coverage(coverage_id, update_dict)
    await db.commit()
    
    return CoverageResponse.model_validate(updated)


# Scraping endpoints
@router.post("/scrape", response_model=dict)
async def scrape_location(
    scrape_request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Trigger scraping for a specific location and industry.
    Returns immediately and runs scraping in background.
    Requires authentication.
    """
    hunter = HunterService(db)
    
    # Run scraping in background
    async def scrape_task():
        result = await hunter.scrape_location(
            city=scrape_request.city,
            state=scrape_request.state,
            industry=scrape_request.industry,
            country=scrape_request.country,
            limit=scrape_request.limit
        )
        # Commit after scraping
        await db.commit()
        return result
    
    background_tasks.add_task(scrape_task)
    
    return {
        "status": "accepted",
        "message": f"Scraping started for {scrape_request.city}, {scrape_request.state} - {scrape_request.industry}",
        "location": f"{scrape_request.city}, {scrape_request.state}",
        "industry": scrape_request.industry,
        "limit": scrape_request.limit
    }


@router.post("/scrape-next", response_model=dict)
async def scrape_next_target(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Automatically scrape the next highest-priority target.
    Runs synchronously and returns results.
    Requires authentication.
    """
    hunter = HunterService(db)
    
    result = await hunter.scrape_next_target(limit=limit)
    
    if not result:
        return {
            "status": "no_targets",
            "message": "No scraping targets available"
        }
    
    # Commit after scraping
    await db.commit()
    
    return result


@router.get("/report/scraping")
async def get_scraping_report(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get comprehensive scraping report with statistics.
    Requires authentication.
    """
    hunter = HunterService(db)
    report = await hunter.get_scraping_report()
    return report
