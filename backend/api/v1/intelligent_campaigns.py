"""
Intelligent Campaign API - Claude-powered geo-strategy endpoints.

User selects city, Claude handles everything else:
- Optimal zone placement
- Business category selection
- Adaptive refinement
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging

from database import get_db
from models.user import AdminUser
from api.v1.auth import get_current_user
from services.hunter.hunter_service import HunterService
from services.hunter.geo_strategy_service import GeoStrategyService

router = APIRouter(prefix="/intelligent-campaigns", tags=["intelligent-campaigns"])
logger = logging.getLogger(__name__)


# Request/Response Models

class CreateStrategyRequest(BaseModel):
    """Request to create a new intelligent strategy."""
    city: str = Field(..., description="City name (e.g., 'Los Angeles')")
    state: str = Field(..., description="State code (e.g., 'CA')")
    category: str = Field(..., description="Business category (e.g., 'plumbers')")
    country: str = Field(default="US", description="Country code")
    population: Optional[int] = Field(None, description="City population (helps Claude's analysis)")
    center_lat: Optional[float] = Field(None, description="City center latitude (will geocode if not provided)")
    center_lon: Optional[float] = Field(None, description="City center longitude (will geocode if not provided)")
    force_regenerate: bool = Field(default=False, description="Force new strategy even if one exists")


class ScrapeZoneRequest(BaseModel):
    """Request to scrape the next zone in a strategy."""
    strategy_id: str = Field(..., description="Strategy UUID")
    limit_per_zone: int = Field(default=50, description="Maximum businesses per zone")


class BatchScrapeRequest(BaseModel):
    """Request to scrape multiple zones in a strategy."""
    strategy_id: str = Field(..., description="Strategy UUID")
    limit_per_zone: int = Field(default=50, description="Maximum businesses per zone")
    max_zones: Optional[int] = Field(None, description="Maximum zones to scrape (None = all remaining)")


class StrategyResponse(BaseModel):
    """Response with strategy details."""
    strategy_id: str
    city: str
    state: str
    category: str
    status: str
    total_zones: int
    zones_completed: int
    zones_remaining: int
    businesses_found: int
    estimated_total_businesses: Optional[int]
    coverage_area_km2: Optional[float]
    strategy_accuracy: Optional[float]
    geographic_analysis: Optional[str]
    business_distribution_analysis: Optional[str]
    zones: List[Dict[str, Any]]
    next_zone: Optional[Dict[str, Any]]


class ScrapeResultResponse(BaseModel):
    """Response from scraping a zone."""
    strategy_id: str
    status: str
    zone_scraped: Dict[str, Any]
    results: Dict[str, Any]
    progress: Dict[str, Any]
    next_zone_preview: Optional[Dict[str, Any]]


# Endpoints

@router.post("/strategies", response_model=StrategyResponse)
async def create_strategy(
    request: CreateStrategyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Create a new intelligent geo-strategy using Claude.
    
    Claude analyzes the city's geography and business distribution patterns
    to generate an optimal zone placement strategy.
    
    **User provides:** City + Business Category  
    **Claude determines:** Optimal zone placement, priorities, and estimates
    """
    try:
        logger.info(
            f"Creating intelligent strategy for {request.category} in "
            f"{request.city}, {request.state}"
        )
        
        geo_strategy_service = GeoStrategyService(db)
        
        strategy = await geo_strategy_service.get_or_create_strategy(
            city=request.city,
            state=request.state,
            category=request.category,
            country=request.country,
            force_regenerate=request.force_regenerate,
            population=request.population,
            center_lat=request.center_lat,
            center_lon=request.center_lon
        )
        
        next_zone = strategy.get_next_zone()
        
        return StrategyResponse(
            strategy_id=str(strategy.id),
            city=strategy.city,
            state=strategy.state,
            category=strategy.category,
            status=strategy.is_active,
            total_zones=strategy.total_zones,
            zones_completed=strategy.zones_completed,
            zones_remaining=strategy.total_zones - strategy.zones_completed,
            businesses_found=strategy.businesses_found,
            estimated_total_businesses=strategy.estimated_total_businesses,
            coverage_area_km2=strategy.coverage_area_km2,
            strategy_accuracy=strategy.performance_data.get("strategy_accuracy") if strategy.performance_data else None,
            geographic_analysis=strategy.geographic_analysis,
            business_distribution_analysis=strategy.business_distribution_analysis,
            zones=strategy.zones,
            next_zone=next_zone
        )
        
    except Exception as e:
        logger.error(f"Failed to create strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Strategy creation failed: {str(e)}")


@router.post("/scrape-zone", response_model=ScrapeResultResponse)
async def scrape_next_zone(
    request: ScrapeZoneRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Scrape the next zone in an intelligent strategy.
    
    Claude has already determined the optimal zone to scrape next based on
    priority and coverage needs. This endpoint executes that zone.
    """
    try:
        hunter_service = HunterService(db)
        geo_strategy_service = GeoStrategyService(db)
        
        # Get strategy
        strategy = await geo_strategy_service.get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        logger.info(
            f"Scraping next zone for strategy {request.strategy_id}: "
            f"{strategy.city}, {strategy.state} - {strategy.category}"
        )
        
        # Execute scrape
        result = await hunter_service.scrape_with_intelligent_strategy(
            city=strategy.city,
            state=strategy.state,
            category=strategy.category,
            country=strategy.country,
            limit_per_zone=request.limit_per_zone,
            center_lat=strategy.city_center_lat,
            center_lon=strategy.city_center_lon
        )
        
        return ScrapeResultResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to scrape zone: {e}")
        raise HTTPException(status_code=500, detail=f"Zone scraping failed: {str(e)}")


@router.post("/batch-scrape")
async def batch_scrape_strategy(
    request: BatchScrapeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Scrape multiple zones (or all remaining zones) in a strategy.
    
    This runs in the background and continues until the strategy is complete
    or the max_zones limit is reached.
    """
    try:
        geo_strategy_service = GeoStrategyService(db)
        
        # Verify strategy exists
        strategy = await geo_strategy_service.get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        logger.info(
            f"Starting batch scrape for strategy {request.strategy_id}: "
            f"max_zones={request.max_zones or 'all'}"
        )
        
        # Run in background
        async def execute_batch():
            async with get_db() as db_session:
                hunter_service = HunterService(db_session)
                await hunter_service.scrape_all_zones_for_strategy(
                    strategy_id=request.strategy_id,
                    limit_per_zone=request.limit_per_zone,
                    max_zones=request.max_zones
                )
        
        background_tasks.add_task(execute_batch)
        
        return {
            "status": "started",
            "strategy_id": request.strategy_id,
            "message": f"Batch scraping started for {strategy.city}, {strategy.state} - {strategy.category}",
            "max_zones": request.max_zones or "all remaining"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start batch scrape: {e}")
        raise HTTPException(status_code=500, detail=f"Batch scrape failed: {str(e)}")


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get details of a specific strategy.
    """
    try:
        geo_strategy_service = GeoStrategyService(db)
        strategy = await geo_strategy_service.get_strategy_by_id(strategy_id)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        next_zone = strategy.get_next_zone()
        
        return StrategyResponse(
            strategy_id=str(strategy.id),
            city=strategy.city,
            state=strategy.state,
            category=strategy.category,
            status=strategy.is_active,
            total_zones=strategy.total_zones,
            zones_completed=strategy.zones_completed,
            zones_remaining=strategy.total_zones - strategy.zones_completed,
            businesses_found=strategy.businesses_found,
            estimated_total_businesses=strategy.estimated_total_businesses,
            coverage_area_km2=strategy.coverage_area_km2,
            strategy_accuracy=strategy.performance_data.get("strategy_accuracy") if strategy.performance_data else None,
            geographic_analysis=strategy.geographic_analysis,
            business_distribution_analysis=strategy.business_distribution_analysis,
            zones=strategy.zones,
            next_zone=next_zone
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def list_strategies(
    city: Optional[str] = None,
    state: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    List strategies with optional filters.
    """
    try:
        geo_strategy_service = GeoStrategyService(db)
        strategies = await geo_strategy_service.list_strategies(
            city=city,
            state=state,
            category=category,
            status=status
        )
        
        return {
            "strategies": [s.to_dict() for s in strategies],
            "total": len(strategies)
        }
        
    except Exception as e:
        logger.error(f"Failed to list strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/{strategy_id}/refine")
async def refine_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Ask Claude to refine a strategy based on actual performance data.
    
    Claude analyzes the results from completed zones and suggests:
    - New zones to add (where high densities were discovered)
    - Adjustments to existing zones
    - Zones to potentially remove
    """
    try:
        geo_strategy_service = GeoStrategyService(db)
        
        refinements = await geo_strategy_service.refine_strategy(strategy_id)
        
        return {
            "strategy_id": strategy_id,
            "refinements": refinements,
            "message": "Strategy refinement complete"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to refine strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_strategy_stats(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get overall statistics about intelligent strategies.
    """
    try:
        geo_strategy_service = GeoStrategyService(db)
        stats = await geo_strategy_service.get_strategy_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

