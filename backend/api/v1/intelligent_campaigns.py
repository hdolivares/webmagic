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

from core.database import get_db, AsyncSessionLocal
from models.user import AdminUser
from api.v1.auth import get_current_user
from services.hunter.hunter_service import HunterService
from services.hunter.geo_strategy_service import GeoStrategyService
from services.hunter.coverage_reporting_service import CoverageReportingService
from services.draft_campaign_service import DraftCampaignService

router = APIRouter(prefix="/intelligent-campaigns", tags=["intelligent-campaigns"])
logger = logging.getLogger(__name__)


# Helper Functions

async def _handle_draft_mode(
    db: AsyncSession,
    strategy: Any,
    scrape_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle draft mode: Save scraped businesses to draft campaign for review.
    
    Args:
        db: Database session
        strategy: GeoStrategy instance
        scrape_result: Result from scraping operation
        
    Returns:
        Modified scrape result with draft campaign information
    """
    draft_service = DraftCampaignService(db)
    
    # Extract zone information from result
    zone_scraped = scrape_result.get('zone_scraped', {})
    results = scrape_result.get('results', {})
    
    # Get business IDs from the scrape (assuming they're in the result)
    # Note: This will need to be populated by the scraping service
    business_ids = scrape_result.get('business_ids', [])
    
    # Create draft campaign
    draft_campaign = await draft_service.create_draft_campaign(
        strategy_id=UUID(scrape_result['strategy_id']),
        city=strategy.city,
        state=strategy.state,
        category=strategy.category,
        zone_id=zone_scraped.get('zone_id', 'unknown'),
        zone_lat=zone_scraped.get('lat'),
        zone_lon=zone_scraped.get('lon'),
        zone_radius_km=zone_scraped.get('radius_km'),
        business_ids=business_ids,
        total_businesses_found=results.get('raw_businesses', 0),
        qualified_leads_count=results.get('qualified_leads', 0)
    )
    
    # Add draft campaign info to result
    scrape_result['draft_mode'] = True
    scrape_result['draft_campaign_id'] = str(draft_campaign.id)
    scrape_result['status'] = 'draft_created'
    scrape_result['message'] = (
        f"Draft campaign created with {results.get('qualified_leads', 0)} qualified leads. "
        "Review and approve to send outreach."
    )
    
    logger.info(
        f"Created draft campaign {draft_campaign.id}: "
        f"{results.get('qualified_leads', 0)} leads saved for review"
    )
    
    return scrape_result


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
    """Request to scrape a zone in a strategy."""
    strategy_id: str = Field(..., description="Strategy UUID")
    zone_id: Optional[str] = Field(None, description="Specific zone to scrape (if None, scrapes next zone)")
    force_rescrape: bool = Field(default=False, description="If True, allows re-scraping already-scraped zones")
    limit_per_zone: int = Field(default=50, description="Maximum businesses per zone")
    draft_mode: bool = Field(default=False, description="If True, save businesses for review without sending messages")


class BatchScrapeRequest(BaseModel):
    """Request to scrape multiple zones in a strategy."""
    strategy_id: str = Field(..., description="Strategy UUID")
    limit_per_zone: int = Field(default=50, description="Maximum businesses per zone")
    max_zones: Optional[int] = Field(None, description="Maximum zones to scrape (None = all remaining)")
    draft_mode: bool = Field(default=False, description="If True, save businesses for review without sending messages")


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
    scraped_zone_ids: List[str] = []  # List of zone_ids that have been scraped


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
        
        # Get list of scraped zone IDs
        scraped_zone_ids = []
        if strategy.performance_data and "zone_results" in strategy.performance_data:
            scraped_zone_ids = [z["zone_id"] for z in strategy.performance_data["zone_results"]]
        
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
            next_zone=next_zone,
            scraped_zone_ids=scraped_zone_ids
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
    
    If draft_mode=True, businesses are saved for review without sending outreach.
    If draft_mode=False (default), outreach is sent automatically.
    """
    try:
        hunter_service = HunterService(db)
        geo_strategy_service = GeoStrategyService(db)
        
        # Get strategy
        strategy = await geo_strategy_service.get_strategy_by_id(request.strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        mode_label = "DRAFT MODE" if request.draft_mode else "LIVE MODE"
        zone_label = f"zone {request.zone_id}" if request.zone_id else "next zone"
        force_label = " (FORCE RESCRAPE)" if request.force_rescrape else ""
        logger.info(
            f"Scraping {zone_label} for strategy {request.strategy_id} ({mode_label}{force_label}): "
            f"{strategy.city}, {strategy.state} - {strategy.category}"
        )
        
        # Handle force rescrape: clear zone from performance_data if requested
        if request.force_rescrape and request.zone_id:
            if strategy.performance_data and "zone_results" in strategy.performance_data:
                strategy.performance_data["zone_results"] = [
                    z for z in strategy.performance_data["zone_results"] 
                    if z["zone_id"] != request.zone_id
                ]
                strategy.zones_completed = len(strategy.performance_data.get("zone_results", []))
                await db.commit()
                logger.info(f"Cleared zone {request.zone_id} from strategy for rescraping")
        
        # Execute scrape
        result = await hunter_service.scrape_with_intelligent_strategy(
            city=strategy.city,
            state=strategy.state,
            category=strategy.category,
            country=strategy.country,
            limit_per_zone=request.limit_per_zone,
            center_lat=strategy.city_center_lat,
            center_lon=strategy.city_center_lon,
            zone_id=request.zone_id  # Pass specific zone if provided
        )
        
        # Handle draft mode vs live mode
        if request.draft_mode:
            result = await _handle_draft_mode(
                db=db,
                strategy=strategy,
                scrape_result=result
            )
        else:
            # Live mode: Send outreach automatically
            # TODO: Implement automatic outreach sending
            logger.info(f"Live mode: Would send outreach to {result['results']['qualified_leads']} leads")
        
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
        
        # Run in background — must use a fresh session, not the request-scoped one
        strategy_id = request.strategy_id
        limit_per_zone = request.limit_per_zone
        max_zones = request.max_zones

        async def execute_batch():
            async with AsyncSessionLocal() as db_session:
                try:
                    hunter_service = HunterService(db_session)
                    await hunter_service.scrape_all_zones_for_strategy(
                        strategy_id=strategy_id,
                        limit_per_zone=limit_per_zone,
                        max_zones=max_zones
                    )
                except Exception as exc:
                    logger.error(f"Batch scrape background task failed: {exc}", exc_info=True)

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
        
        # Get list of scraped zone IDs
        scraped_zone_ids = []
        if strategy.performance_data and "zone_results" in strategy.performance_data:
            scraped_zone_ids = [z["zone_id"] for z in strategy.performance_data["zone_results"]]
        
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
            next_zone=next_zone,
            scraped_zone_ids=scraped_zone_ids
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


# Phase 3: Coverage Reporting Endpoints

@router.get("/zones/{zone_id}/statistics")
async def get_zone_statistics(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get detailed statistics for a specific zone.
    
    Returns comprehensive metrics including:
    - Total businesses, qualified leads
    - Website metrics (with/without/invalid/generated)
    - Generation progress
    - Qualification and coverage rates
    - Last scrape details (persistent)
    """
    try:
        reporting_service = CoverageReportingService(db)
        stats = await reporting_service.get_zone_statistics(zone_id)
        
        if 'error' in stats:
            raise HTTPException(status_code=404, detail=stats['error'])
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get zone statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/{strategy_id}/overview")
async def get_strategy_overview(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get comprehensive overview of a geo-strategy.
    
    Returns strategy-wide aggregated metrics including:
    - Zone progress (total, completed, pending)
    - Business totals and website metrics
    - Performance rates (qualification, coverage)
    - Per-zone breakdown with details
    """
    try:
        from uuid import UUID
        strategy_uuid = UUID(strategy_id)
        
        reporting_service = CoverageReportingService(db)
        overview = await reporting_service.get_strategy_overview(strategy_uuid)
        
        if 'error' in overview:
            raise HTTPException(status_code=404, detail=overview['error'])
        
        return overview
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid strategy ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coverage/breakdown")
async def get_coverage_breakdown(
    city: Optional[str] = None,
    state: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    """
    Get coverage breakdown with optional filters.
    
    Query parameters:
    - city: Filter by city (optional)
    - state: Filter by state (optional)
    - category: Filter by category/industry (optional)
    
    Returns aggregated coverage statistics across filtered zones.
    """
    try:
        reporting_service = CoverageReportingService(db)
        breakdown = await reporting_service.get_coverage_breakdown(
            city=city,
            state=state,
            category=category
        )
        
        return breakdown
        
    except Exception as e:
        logger.error(f"Failed to get coverage breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))

