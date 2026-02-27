"""
Coverage Campaign Management API.

Endpoints for planning, tracking, and managing systematic business discovery campaigns.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from typing import Optional, List
from datetime import datetime

from core.database import get_db
from api.deps import get_current_user
from models.coverage import CoverageGrid
from models.business import Business
from models.geo_strategy import GeoStrategy
from models.user import AdminUser
from pydantic import BaseModel
from scripts.business_categories import BUSINESS_CATEGORIES

router = APIRouter(prefix="/coverage/campaigns", tags=["coverage-campaigns"])


# ============================================
# SCHEMAS
# ============================================

class CampaignStats(BaseModel):
    """Overall campaign statistics."""
    # Coverage-grid level (scraped rows)
    total_grids: int
    pending_grids: int
    in_progress_grids: int
    completed_grids: int
    failed_grids: int
    total_businesses_found: int
    total_locations: int
    total_categories: int
    completion_percentage: float
    estimated_cost: float
    actual_cost: float
    # Strategy (zone plan) level — more accurate scope picture
    total_strategies: int
    total_zones: int
    zones_completed: int
    zones_completion_pct: float
    strategy_cities: int
    strategy_categories: int
    # Full available universe (from dropdown data)
    available_categories: int


class LocationCoverage(BaseModel):
    """Coverage statistics for a specific location."""
    location: str
    state: str
    total_categories: int
    completed_categories: int
    pending_categories: int
    total_businesses: int
    completion_percentage: float
    last_scraped: Optional[datetime]


class CategoryCoverage(BaseModel):
    """Coverage statistics for a specific category."""
    category: str
    total_locations: int
    completed_locations: int
    pending_locations: int
    total_businesses: int
    completion_percentage: float
    avg_businesses_per_location: float


class GridDetail(BaseModel):
    """Detailed grid information."""
    id: str
    location: str
    state: str
    category: str
    status: str
    priority: int
    businesses_found: int
    estimated_businesses: int
    last_scraped: Optional[datetime]
    next_scheduled: Optional[datetime]
    error_message: Optional[str]


# ============================================
# ENDPOINTS
# ============================================

@router.get("/stats", response_model=CampaignStats)
async def get_campaign_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get overall campaign statistics.
    """
    # Count grids by status
    result = await db.execute(
        select(
            CoverageGrid.status,
            func.count(CoverageGrid.id).label("count")
        ).group_by(CoverageGrid.status)
    )
    status_counts = {row.status: row.count for row in result}
    
    # Total grids
    total = sum(status_counts.values())
    
    # Count unique locations and categories from coverage_grid
    locations_result = await db.execute(
        select(func.count(func.distinct(func.concat(CoverageGrid.city, ':', CoverageGrid.state))))
    )
    total_locations = locations_result.scalar() or 0

    # Fix: the column is `industry`, not `industry_category`
    categories_result = await db.execute(
        select(func.count(func.distinct(CoverageGrid.industry)))
    )
    total_categories = categories_result.scalar() or 0

    # Count total businesses found
    businesses_result = await db.execute(
        select(func.count(Business.id))
    )
    total_businesses = businesses_result.scalar() or 0

    # Calculate grid-level completion percentage
    completed = status_counts.get("completed", 0)
    completion_pct = (completed / total * 100) if total > 0 else 0.0

    # Estimate costs (assuming $0.50 per search)
    estimated_cost = total * 0.50
    actual_cost = (completed + status_counts.get("failed", 0)) * 0.50

    # ── Strategy (zone-plan) level stats ──────────────────────────────────────
    # GeoStrategy rows represent the full planned scope: each strategy covers
    # total_zones zones for one city × category pair. These numbers give a
    # much more accurate picture of how much work remains.
    strategy_agg = await db.execute(
        select(
            func.count(GeoStrategy.id).label("total_strategies"),
            func.sum(GeoStrategy.total_zones).label("total_zones"),
            func.sum(GeoStrategy.zones_completed).label("zones_completed"),
            func.count(func.distinct(func.concat(GeoStrategy.city, ':', GeoStrategy.state))).label("cities"),
            func.count(func.distinct(GeoStrategy.category)).label("categories"),
        ).where(GeoStrategy.is_active == True)  # noqa: E712
    )
    strat_row = strategy_agg.first()
    total_strategies = strat_row.total_strategies or 0
    total_zones = int(strat_row.total_zones or 0)
    zones_done = int(strat_row.zones_completed or 0)
    strategy_cities = strat_row.cities or 0
    strategy_categories = strat_row.categories or 0
    zones_completion_pct = round((zones_done / total_zones * 100) if total_zones > 0 else 0.0, 2)

    return CampaignStats(
        total_grids=total,
        pending_grids=status_counts.get("pending", 0),
        in_progress_grids=status_counts.get("in_progress", 0),
        completed_grids=completed,
        failed_grids=status_counts.get("failed", 0),
        total_businesses_found=total_businesses,
        total_locations=total_locations,
        total_categories=total_categories,
        completion_percentage=round(completion_pct, 2),
        estimated_cost=estimated_cost,
        actual_cost=actual_cost,
        total_strategies=total_strategies,
        total_zones=total_zones,
        zones_completed=zones_done,
        zones_completion_pct=zones_completion_pct,
        strategy_cities=strategy_cities,
        strategy_categories=strategy_categories,
        available_categories=len(BUSINESS_CATEGORIES),
    )


@router.get("/locations", response_model=List[LocationCoverage])
async def get_location_coverage(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    state: Optional[str] = Query(None),
    min_completion: Optional[float] = Query(None, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get coverage statistics grouped by location.
    """
    # Build query
    query = select(
        CoverageGrid.city.label("location"),
        CoverageGrid.state,
        func.count(CoverageGrid.id).label("total_categories"),
        func.sum(
            case((CoverageGrid.status == "completed", 1), else_=0)
        ).label("completed_categories"),
        func.sum(
            case((CoverageGrid.status == "pending", 1), else_=0)
        ).label("pending_categories"),
        func.sum(CoverageGrid.lead_count).label("total_businesses"),
        func.max(CoverageGrid.last_scraped_at).label("last_scraped")
    ).group_by(
        CoverageGrid.city,
        CoverageGrid.state
    )
    
    # Apply filters
    if state:
        query = query.where(CoverageGrid.state == state)
    
    # Execute query
    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    
    locations = []
    for row in result:
        total = row.total_categories or 0
        completed = row.completed_categories or 0
        completion_pct = (completed / total * 100) if total > 0 else 0.0
        
        # Apply completion filter
        if min_completion is not None and completion_pct < min_completion:
            continue
        
        locations.append(LocationCoverage(
            location=row.location,
            state=row.state,
            total_categories=total,
            completed_categories=completed,
            pending_categories=row.pending_categories or 0,
            total_businesses=row.total_businesses or 0,
            completion_percentage=round(completion_pct, 2),
            last_scraped=row.last_scraped
        ))
    
    return locations


@router.get("/categories", response_model=List[CategoryCoverage])
async def get_category_coverage(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    min_completion: Optional[float] = Query(None, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get coverage statistics grouped by category.
    """
    query = select(
        CoverageGrid.industry_category,
        func.count(CoverageGrid.id).label("total_locations"),
        func.sum(
            case((CoverageGrid.status == "completed", 1), else_=0)
        ).label("completed_locations"),
        func.sum(
            case((CoverageGrid.status == "pending", 1), else_=0)
        ).label("pending_locations"),
        func.sum(CoverageGrid.lead_count).label("total_businesses"),
        func.avg(CoverageGrid.lead_count).label("avg_businesses")
    ).group_by(
        CoverageGrid.industry_category
    )
    
    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    
    categories = []
    for row in result:
        total = row.total_locations or 0
        completed = row.completed_locations or 0
        completion_pct = (completed / total * 100) if total > 0 else 0.0
        
        if min_completion is not None and completion_pct < min_completion:
            continue
        
        # Use "Uncategorized" as default for null categories
        category_name = row.industry_category if row.industry_category else "Uncategorized"
        
        categories.append(CategoryCoverage(
            category=category_name,
            total_locations=total,
            completed_locations=completed,
            pending_locations=row.pending_locations or 0,
            total_businesses=row.total_businesses or 0,
            completion_percentage=round(completion_pct, 2),
            avg_businesses_per_location=round(row.avg_businesses or 0, 1)
        ))
    
    return categories


@router.get("/grids", response_model=List[GridDetail])
async def get_grid_details(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    location: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority_min: Optional[int] = Query(None, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get detailed grid entries with filters.
    """
    query = select(CoverageGrid)
    
    # Apply filters
    filters = []
    if location:
        filters.append(CoverageGrid.location.ilike(f"%{location}%"))
    if category:
        filters.append(CoverageGrid.industry_category.ilike(f"%{category}%"))
    if status:
        filters.append(CoverageGrid.status == status)
    if priority_min:
        filters.append(CoverageGrid.priority >= priority_min)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Order by priority desc, then by location
    query = query.order_by(
        CoverageGrid.priority.desc(),
        CoverageGrid.location,
        CoverageGrid.industry_category
    )
    
    result = await db.execute(query.offset(skip).limit(limit))
    grids = result.scalars().all()
    
    return [
        GridDetail(
            id=str(grid.id),
            location=grid.city,
            state=grid.state,
            category=grid.industry,
            status=grid.status,
            priority=grid.priority,
            businesses_found=grid.lead_count or 0,
            estimated_businesses=grid.estimated_businesses or 0,
            last_scraped=grid.last_scraped_at,
            next_scheduled=grid.next_scheduled,
            error_message=grid.error_message
        )
        for grid in grids
    ]


@router.post("/start-batch")
async def start_batch_scrape(
    priority_min: int = Query(7, ge=1, le=10, description="Minimum priority to include"),
    limit: int = Query(100, ge=1, le=500, description="Max grids to queue"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Start a batch scrape campaign for high-priority pending grids.
    """
    from tasks.scraping import scrape_grid_task
    
    # Find pending grids with high priority
    result = await db.execute(
        select(CoverageGrid)
        .where(
            and_(
                CoverageGrid.status == "pending",
                CoverageGrid.priority >= priority_min
            )
        )
        .order_by(CoverageGrid.priority.desc())
        .limit(limit)
    )
    grids = result.scalars().all()
    
    # Queue scraping tasks
    queued_count = 0
    for grid in grids:
        # Update status to in_progress
        grid.status = "in_progress"
        grid.next_scheduled = datetime.utcnow()
        
        # Queue Celery task
        scrape_grid_task.delay(str(grid.id))
        queued_count += 1
    
    await db.commit()
    
    return {
        "success": True,
        "queued_tasks": queued_count,
        "message": f"Queued {queued_count} scraping tasks with priority >= {priority_min}"
    }


@router.post("/test-searches")
async def test_manual_searches(
    count: int = Query(..., ge=1, le=25, description="Number of searches to run"),
    priority_min: int = Query(7, ge=1, le=10, description="Minimum priority"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Manual testing endpoint - run a specific number of searches and return immediate results.
    This is synchronous and perfect for testing before enabling autopilot.
    
    Returns detailed results for each search including:
    - Location and industry searched
    - Number of businesses found
    - Qualified vs total leads
    - Sample business names
    """
    from services.hunter.hunter_service import HunterService
    import asyncio
    
    # Find highest-priority pending grids
    result = await db.execute(
        select(CoverageGrid)
        .where(
            and_(
                CoverageGrid.status == "pending",
                CoverageGrid.priority >= priority_min
            )
        )
        .order_by(CoverageGrid.priority.desc())
        .limit(count)
    )
    grids = result.scalars().all()
    
    if not grids:
        return {
            "success": False,
            "message": f"No pending grids found with priority >= {priority_min}",
            "searches_completed": 0,
            "results": []
        }
    
    # Run searches synchronously
    hunter_service = HunterService(db)
    results = []
    successful = 0
    failed = 0
    
    for grid in grids:
        try:
            # Mark as in progress
            grid.status = "in_progress"
            await db.commit()
            
            # Run scrape
            scrape_result = await hunter_service.scrape_location(
                city=grid.city,
                state=grid.state,
                industry=grid.industry,
                country=grid.country,
                limit=50,  # Get 50 results per search
                priority=grid.priority
            )
            
            # Record result
            results.append({
                "grid_id": str(grid.id),
                "location": f"{grid.city}, {grid.state}",
                "industry": grid.industry,
                "status": "success",
                "businesses_found": scrape_result.get("scraped", 0),
                "qualified": scrape_result.get("qualified", 0),
                "saved": scrape_result.get("saved", 0),
                "qualification_rate": scrape_result.get("qualification_rate", 0),
                "sample_businesses": scrape_result.get("sample_businesses", [])[:3]
            })
            successful += 1
            
        except Exception as e:
            # Record failure
            grid.status = "failed"
            grid.error_message = str(e)
            await db.commit()
            
            results.append({
                "grid_id": str(grid.id),
                "location": f"{grid.city}, {grid.state}",
                "industry": grid.industry,
                "status": "failed",
                "error": str(e)
            })
            failed += 1
    
    return {
        "success": True,
        "searches_completed": successful,
        "searches_failed": failed,
        "total_requested": count,
        "message": f"Completed {successful}/{count} test searches successfully",
        "results": results
    }
