"""
Geo-Grid API Endpoints

Provides API routes for geo-grid based business discovery, which subdivides
large cities into zones for comprehensive coverage.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging

from api.deps import get_db, get_current_user
from models.user import AdminUser
from services.hunter.geo_grid import create_city_grid
from services.hunter.hunter_service import HunterService
from services.hunter.coverage_service import CoverageService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coverage/geo-grid", tags=["geo-grid"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class GeoGridScrapeRequest(BaseModel):
    """Request to scrape a location with geo-grid subdivision"""
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State code (e.g., CA, TX)")
    industry: str = Field(..., description="Business industry/category")
    population: int = Field(..., description="City population")
    city_lat: float = Field(..., description="City center latitude")
    city_lon: float = Field(..., description="City center longitude")
    limit_per_zone: int = Field(50, description="Maximum results per zone")
    priority: int = Field(8, ge=1, le=10, description="Priority level (1-10)")


class ZoneResult(BaseModel):
    """Result from a single zone scrape"""
    zone_id: str
    coverage_id: Optional[str] = None
    scraped: int
    qualified: int
    saved: int
    has_more: bool = False
    error: Optional[str] = None


class GeoGridScrapeResponse(BaseModel):
    """Complete geo-grid scrape response"""
    status: str  # 'completed', 'failed', 'partial'
    location: str
    industry: str
    zones_scraped: int
    total_scraped: int
    total_qualified: int
    total_saved: int
    zone_results: List[ZoneResult]
    message: Optional[str] = None
    error: Optional[str] = None


class StrategyComparison(BaseModel):
    """Strategy comparison data"""
    city: str
    state: str
    population: int
    traditional: Dict[str, Any]
    geo_grid: Dict[str, Any]
    recommendation: str


# ============================================
# ENDPOINTS
# ============================================

@router.post("/scrape", response_model=GeoGridScrapeResponse)
async def scrape_with_geo_grid(
    request: GeoGridScrapeRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Scrape a city using geo-grid subdivision.
    
    Automatically breaks down large cities into zones for comprehensive coverage.
    Each zone is scraped independently to maximize business discovery.
    """
    try:
        logger.info(
            f"Starting geo-grid scrape: {request.city}, {request.state} - {request.industry}"
        )
        
        # Initialize services
        hunter_service = HunterService(db)
        
        # Execute geo-grid scrape
        result = await hunter_service.scrape_location_with_zones(
            city=request.city,
            state=request.state,
            industry=request.industry,
            population=request.population,
            city_lat=request.city_lat,
            city_lon=request.city_lon,
            limit_per_zone=request.limit_per_zone,
            priority=request.priority
        )
        
        # Transform result to response format
        zone_results = [
            ZoneResult(
                zone_id=zr.get("zone_id", ""),
                coverage_id=zr.get("coverage_id"),
                scraped=zr.get("scraped", 0),
                qualified=zr.get("qualified", 0),
                saved=zr.get("saved", 0),
                has_more=zr.get("has_more", False),
                error=zr.get("error")
            )
            for zr in result.get("zone_results", [])
        ]
        
        return GeoGridScrapeResponse(
            status=result.get("status", "failed"),
            location=f"{request.city}, {request.state}",
            industry=request.industry,
            zones_scraped=result.get("zones_scraped", 0),
            total_scraped=result.get("total_scraped", 0),
            total_qualified=result.get("total_qualified", 0),
            total_saved=result.get("total_saved", 0),
            zone_results=zone_results,
            message=result.get("message"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Geo-grid scrape failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare", response_model=StrategyComparison)
async def compare_strategies(
    city: str = Query(..., description="City name"),
    state: str = Query(..., description="State code"),
    population: int = Query(..., description="City population"),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Compare traditional vs geo-grid strategy for a location.
    
    Returns cost and coverage comparison to help decide which approach to use.
    """
    try:
        import math
        
        # Calculate traditional approach (single search)
        traditional_searches = 1
        traditional_radius_km = 25  # Standard search radius
        traditional_coverage_km2 = math.pi * (traditional_radius_km ** 2)
        traditional_expected_results = 50  # API limit
        traditional_cost = traditional_searches * 0.50
        
        # Calculate geo-grid approach
        grid_config = create_city_grid(
            city_name=city,
            state_code=state,
            center_lat=0,  # Not needed for comparison
            center_lon=0,
            population=population
        )
        
        geo_grid_searches = grid_config["total_zones"]
        geo_grid_coverage_km2 = grid_config["approx_coverage_km2"]
        geo_grid_expected_results = geo_grid_searches * 50
        geo_grid_cost = geo_grid_searches * 0.50
        
        # Determine recommendation
        # Use geo-grid if population > 100k or if coverage is significantly better
        recommendation = "geo_grid" if population > 100000 else "traditional"
        
        return StrategyComparison(
            city=city,
            state=state,
            population=population,
            traditional={
                "searches": traditional_searches,
                "expected_results": traditional_expected_results,
                "coverage_km2": traditional_coverage_km2,
                "cost": traditional_cost
            },
            geo_grid={
                "grid_size": grid_config["grid_size"],
                "total_zones": geo_grid_searches,
                "searches": geo_grid_searches,
                "expected_results": geo_grid_expected_results,
                "coverage_km2": geo_grid_coverage_km2,
                "cost": geo_grid_cost
            },
            recommendation=recommendation
        )
        
    except Exception as e:
        logger.error(f"Strategy comparison failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_geo_grid_stats(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get geo-grid statistics and metrics.
    
    Returns overall stats about geo-grid usage and performance.
    """
    try:
        coverage_service = CoverageService(db)
        
        # Query coverage grids with zone information
        from models.coverage import CoverageGrid
        
        total_zones = db.query(CoverageGrid).filter(
            CoverageGrid.zone_id.isnot(None)
        ).count()
        
        zones_with_data = db.query(CoverageGrid).filter(
            CoverageGrid.zone_id.isnot(None),
            CoverageGrid.lead_count > 0
        ).count()
        
        zones_pending = db.query(CoverageGrid).filter(
            CoverageGrid.zone_id.isnot(None),
            CoverageGrid.status == "pending"
        ).count()
        
        # Calculate average businesses per zone
        from sqlalchemy import func
        avg_result = db.query(
            func.avg(CoverageGrid.lead_count)
        ).filter(
            CoverageGrid.zone_id.isnot(None),
            CoverageGrid.lead_count > 0
        ).scalar()
        
        avg_businesses_per_zone = float(avg_result) if avg_result else 0.0
        
        # Count unique cities with zones
        total_cities_subdivided = db.query(
            func.count(func.distinct(CoverageGrid.city))
        ).filter(
            CoverageGrid.zone_id.isnot(None)
        ).scalar() or 0
        
        return {
            "total_zones": total_zones,
            "zones_with_data": zones_with_data,
            "zones_pending": zones_pending,
            "avg_businesses_per_zone": round(avg_businesses_per_zone, 1),
            "total_cities_subdivided": total_cities_subdivided
        }
        
    except Exception as e:
        logger.error(f"Failed to get geo-grid stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_geo_grid_coverage(
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    has_zones: Optional[bool] = Query(None, description="Filter for entries with zones"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get coverage grids with zone information.
    
    Returns paginated list of coverage grids, optionally filtered.
    """
    try:
        from models.coverage import CoverageGrid
        
        # Build query
        query = db.query(CoverageGrid)
        
        # Apply filters
        if city:
            query = query.filter(CoverageGrid.city.ilike(f"%{city}%"))
        if state:
            query = query.filter(CoverageGrid.state == state.upper())
        if industry:
            query = query.filter(CoverageGrid.industry.ilike(f"%{industry}%"))
        if has_zones is not None:
            if has_zones:
                query = query.filter(CoverageGrid.zone_id.isnot(None))
            else:
                query = query.filter(CoverageGrid.zone_id.is_(None))
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        grids = query.order_by(
            CoverageGrid.priority.desc(),
            CoverageGrid.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        # Transform to dict
        grid_dicts = [
            {
                "id": str(grid.id),
                "country": grid.country,
                "state": grid.state,
                "city": grid.city,
                "industry": grid.industry,
                "zone_id": grid.zone_id,
                "zone_lat": str(grid.zone_lat) if grid.zone_lat else None,
                "zone_lon": str(grid.zone_lon) if grid.zone_lon else None,
                "zone_radius_km": str(grid.zone_radius_km) if grid.zone_radius_km else None,
                "status": grid.status,
                "priority": grid.priority,
                "lead_count": grid.lead_count,
                "qualified_count": grid.qualified_count,
                "qualification_rate": (
                    grid.qualified_count / grid.lead_count * 100
                    if grid.lead_count > 0 else None
                ),
                "last_scraped_at": grid.last_scraped_at.isoformat() if grid.last_scraped_at else None,
                "cooldown_until": grid.cooldown_until.isoformat() if grid.cooldown_until else None,
                "created_at": grid.created_at.isoformat(),
                "updated_at": grid.updated_at.isoformat()
            }
            for grid in grids
        ]
        
        return {
            "grids": grid_dicts,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Failed to get geo-grid coverage: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

