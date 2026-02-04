"""
Main Hunter orchestration service - coordinates scraping workflow.
Now enhanced with Claude-powered intelligent zone placement strategies.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
import logging

from services.hunter.scraper import OutscraperClient
from services.hunter.filters import LeadQualifier
from services.hunter.business_service import BusinessService
from services.hunter.coverage_service import CoverageService
from services.hunter.geo_strategy_service import GeoStrategyService
from services.hunter.website_validator import WebsiteValidator
from services.hunter.website_validation_service import WebsiteValidationService
from services.hunter.website_generation_queue_service import WebsiteGenerationQueueService
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)


class HunterService:
    """
    Main orchestration service for the Hunter module.
    
    Now uses Claude to generate intelligent zone placement strategies
    for maximum business discovery with minimum redundancy.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        scraper: Optional[OutscraperClient] = None,
        qualifier: Optional[LeadQualifier] = None
    ):
        """
        Initialize Hunter service.
        
        Args:
            db: Database session
            scraper: Outscraper client (creates new if None)
            qualifier: Lead qualifier (creates new if None)
        """
        self.db = db
        self.scraper = scraper or OutscraperClient()
        self.qualifier = qualifier or LeadQualifier(
            min_score=50,
            require_no_website=True,
            require_email=False
        )
        self.business_service = BusinessService(db)
        self.coverage_service = CoverageService(db)
        self.geo_strategy_service = GeoStrategyService(db)
        self.website_validator = WebsiteValidator()
        # New Phase 2 services
        self.generation_queue_service = WebsiteGenerationQueueService(db)
    
    async def scrape_with_intelligent_strategy(
        self,
        city: str,
        state: str,
        category: str,
        country: str = "US",
        limit_per_zone: int = 50,
        population: Optional[int] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        force_new_strategy: bool = False
    ) -> Dict[str, Any]:
        """
        Scrape a city using Claude-generated intelligent zone placement strategy.
        
        This is the NEW recommended method that replaces scrape_location_with_zones.
        Claude analyzes the city's geography and business distribution patterns to
        place zones optimally, avoiding wasted searches and ensuring complete coverage.
        
        Args:
            city: City name
            state: State code
            category: Business category
            country: Country code
            limit_per_zone: Maximum results per zone
            population: City population (optional, helps Claude's analysis)
            center_lat: City center latitude (will geocode if not provided)
            center_lon: City center longitude (will geocode if not provided)
            force_new_strategy: Generate new strategy even if one exists
            
        Returns:
            Dictionary with results:
            {
                "strategy_id": "uuid",
                "total_zones": 18,
                "zones_scraped": 1,
                "zones_remaining": 17,
                "businesses_found": 47,
                "qualified_leads": 12,
                "zone_results": {...},
                "strategy_status": "active|completed"
            }
        """
        logger.info(f"Starting intelligent strategy scrape: {city}, {state} - {category}")
        
        # Get or create strategy using Claude
        strategy = await self.geo_strategy_service.get_or_create_strategy(
            city=city,
            state=state,
            category=category,
            country=country,
            force_regenerate=force_new_strategy,
            population=population,
            center_lat=center_lat,
            center_lon=center_lon
        )
        
        logger.info(
            f"Using strategy {strategy.id}: {strategy.total_zones} zones, "
            f"{strategy.zones_completed} already completed"
        )
        
        # Get next zone to scrape
        next_zone = strategy.get_next_zone()
        if not next_zone:
            logger.info(f"Strategy {strategy.id} is complete - all zones scraped")
            return {
                "strategy_id": str(strategy.id),
                "status": "completed",
                "message": "All zones in this strategy have been scraped",
                "total_zones": strategy.total_zones,
                "zones_completed": strategy.zones_completed,
                "total_businesses_found": strategy.businesses_found
            }
        
        zone_id = next_zone["zone_id"]
        zone_lat = next_zone["lat"]
        zone_lon = next_zone["lon"]
        zone_radius = next_zone["radius_km"]
        
        logger.info(
            f"Scraping zone {zone_id} ({zone_lat}, {zone_lon}) "
            f"radius {zone_radius}km, priority: {next_zone.get('priority')}"
        )
        
        # Scrape the zone
        try:
            logger.info(
                f"Scraper params: zone_lat={zone_lat} (type: {type(zone_lat).__name__}), "
                f"zone_lon={zone_lon} (type: {type(zone_lon).__name__}), "
                f"zone_radius={zone_radius} (type: {type(zone_radius).__name__})"
            )
            
            results = await self.scraper.search_businesses(
                query=category,
                city=city,
                state=state,
                country=country,
                limit=limit_per_zone,
                zone_lat=zone_lat,
                zone_lon=zone_lon,
                zone_id=zone_id
            )
            
            raw_businesses = results.get("businesses", [])
            logger.info(f"Zone {zone_id} returned {len(raw_businesses)} businesses from scraper")
            logger.debug(f"Scraper result keys: {list(results.keys())}")
            
            # Process and qualify leads
            qualified_count = 0
            new_businesses = 0
            businesses_with_websites = 0
            businesses_without_websites = 0
            invalid_websites = 0
            businesses_needing_generation = []
            
            # Create validation service with async context
            async with WebsiteValidationService(self.db) as validation_service:
                for biz_data in raw_businesses:
                    try:
                        # Validate website if present (old validator for backwards compatibility)
                        website_url = biz_data.get("website")
                        website_status = "unknown"
                        
                        if website_url:
                            website_status = await self.website_validator.validate_website(website_url)
                            biz_data["website_status"] = website_status
                        
                        # Qualify the lead
                        qualification_result = self.qualifier.qualify(biz_data)
                        is_qualified = qualification_result["qualified"]
                        score = qualification_result["score"]
                        reasons = qualification_result["reasons"]
                        
                        # Store if qualified
                        if is_qualified:
                            business = await self.business_service.create_or_update_business(
                                data=biz_data,
                                source="outscraper_gmaps",
                                discovery_city=city,
                                discovery_state=state,
                                discovery_zone_id=zone_id,
                                discovery_zone_lat=zone_lat,
                                discovery_zone_lon=zone_lon,
                                lead_score=score,
                                qualification_reasons=reasons
                            )
                            
                            if business:
                                qualified_count += 1
                                if hasattr(business, '_is_new') and business._is_new:
                                    new_businesses += 1
                                
                                # **NEW Phase 2: Validate website using comprehensive validation service**
                                validation_result = await validation_service.validate_business_website(
                                    {
                                        "id": str(business.id),
                                        "name": business.name,
                                        "website_url": business.website_url,
                                        "gmb_place_id": business.gmb_place_id
                                    },
                                    store_result=True
                                )
                                
                                # Track website metrics
                                if validation_result.status == "valid":
                                    businesses_with_websites += 1
                                elif validation_result.status in ["invalid", "missing"]:
                                    businesses_without_websites += 1
                                    if validation_result.status == "invalid":
                                        invalid_websites += 1
                                    
                                    # Queue for generation if recommended
                                    if validation_result.recommendation == "generate":
                                        businesses_needing_generation.append(business.id)
                                        logger.debug(f"Business {business.name} queued for website generation")
                        
                    except Exception as e:
                        logger.error(f"Error processing business: {e}")
                        continue
            
            # **NEW Phase 2: Queue businesses for website generation**
            if businesses_needing_generation:
                queue_result = await self.generation_queue_service.queue_multiple(
                    business_ids=businesses_needing_generation,
                    priority=7  # High priority for newly scraped businesses
                )
                logger.info(
                    f"Queued {queue_result['queued']}/{len(businesses_needing_generation)} "
                    f"businesses for website generation"
                )
            
            # Update coverage tracking
            # Convert floats to strings for database schema compatibility
            coverage, created = await self.coverage_service.get_or_create_coverage(
                city=city,
                state=state,
                industry=category,
                country=country,
                zone_id=zone_id,
                zone_lat=str(zone_lat) if zone_lat is not None else None,
                zone_lon=str(zone_lon) if zone_lon is not None else None,
                zone_radius_km=str(zone_radius) if zone_radius is not None else None
            )
            
            # **NEW Phase 2: Store detailed scrape metrics**
            last_scrape_details = {
                "raw_businesses": len(raw_businesses),
                "qualified_leads": qualified_count,
                "new_businesses": new_businesses,
                "existing_businesses": qualified_count - new_businesses,
                "with_websites": businesses_with_websites,
                "without_websites": businesses_without_websites,
                "invalid_websites": invalid_websites,
                "queued_for_generation": len(businesses_needing_generation),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Calculate average metrics
            from sqlalchemy import select, func
            from models.business import Business
            
            # Get businesses for this coverage zone to calculate averages
            zone_businesses_query = select(
                func.avg(Business.qualification_score).label("avg_score"),
                func.avg(Business.rating).label("avg_rating")
            ).where(Business.coverage_grid_id == coverage.id)
            
            result = await self.db.execute(zone_businesses_query)
            averages = result.first()
            avg_qualification_score = float(averages.avg_score) if averages.avg_score else None
            avg_rating = float(averages.avg_rating) if averages.avg_rating else None
            
            # Update with comprehensive scraping results
            await self.coverage_service.update_coverage(
                coverage_id=coverage.id,
                updates={
                    "status": "completed",
                    "lead_count": qualified_count,
                    "qualified_count": qualified_count,
                    "last_scrape_size": len(raw_businesses),
                    "last_scraped_at": datetime.utcnow(),
                    # New Phase 2 metrics
                    "businesses_with_websites": businesses_with_websites,
                    "businesses_without_websites": businesses_without_websites,
                    "invalid_websites": invalid_websites,
                    "generation_in_progress": len(businesses_needing_generation),
                    "avg_qualification_score": avg_qualification_score,
                    "avg_rating": avg_rating,
                    "last_scrape_details": last_scrape_details
                }
            )
            
            # Mark zone complete in strategy
            await self.geo_strategy_service.mark_zone_complete(
                strategy_id=str(strategy.id),
                zone_id=zone_id,
                businesses_found=qualified_count
            )
            
            # Refresh strategy to get updated stats
            await self.db.refresh(strategy)
            
            logger.info(
                f"Zone {zone_id} complete: {qualified_count} qualified from {len(raw_businesses)} raw "
                f"({strategy.zones_completed}/{strategy.total_zones} zones done)"
            )
            
            # Prepare enhanced response with Phase 2 metrics
            return {
                "strategy_id": str(strategy.id),
                "status": "active" if strategy.zones_completed < strategy.total_zones else "completed",
                "city": city,
                "state": state,
                "category": category,
                "zone_scraped": {
                    "zone_id": zone_id,
                    "priority": next_zone.get("priority"),
                    "lat": zone_lat,
                    "lon": zone_lon,
                    "radius_km": zone_radius,
                    "reason": next_zone.get("reason")
                },
                "results": {
                    "raw_businesses": len(raw_businesses),
                    "qualified_leads": qualified_count,
                    "new_businesses": new_businesses,
                    # **NEW Phase 2: Website metrics**
                    "with_websites": businesses_with_websites,
                    "without_websites": businesses_without_websites,
                    "invalid_websites": invalid_websites,
                    "queued_for_generation": len(businesses_needing_generation)
                },
                "progress": {
                    "total_zones": strategy.total_zones,
                    "zones_completed": strategy.zones_completed,
                    "zones_remaining": strategy.total_zones - strategy.zones_completed,
                    "total_businesses_found": strategy.businesses_found,
                    "estimated_total_businesses": strategy.estimated_total_businesses,
                    "completion_pct": round((strategy.zones_completed / strategy.total_zones) * 100, 1)
                },
                "next_zone_preview": strategy.get_next_zone()
            }
            
        except Exception as e:
            logger.error(f"Error scraping zone {zone_id}: {e}")
            raise ExternalAPIException(f"Failed to scrape zone: {str(e)}")
    
    async def scrape_all_zones_for_strategy(
        self,
        strategy_id: str,
        limit_per_zone: int = 50,
        max_zones: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Continue scraping zones for an existing strategy until complete (or max reached).
        
        This is useful for background tasks that want to execute an entire strategy.
        
        Args:
            strategy_id: Strategy UUID
            limit_per_zone: Maximum results per zone
            max_zones: Maximum zones to scrape in this batch (None = all)
            
        Returns:
            Summary of batch execution
        """
        strategy = await self.geo_strategy_service.get_strategy_by_id(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        logger.info(
            f"Starting batch execution for strategy {strategy_id}: "
            f"{strategy.city}, {strategy.state} - {strategy.category}"
        )
        
        zones_scraped = 0
        total_businesses = 0
        total_qualified = 0
        
        while True:
            # Check if we've hit the max
            if max_zones and zones_scraped >= max_zones:
                logger.info(f"Reached max zones limit ({max_zones})")
                break
            
            # Get next zone
            next_zone = strategy.get_next_zone()
            if not next_zone:
                logger.info(f"Strategy {strategy_id} complete - no more zones")
                break
            
            # Scrape the zone
            try:
                result = await self.scrape_with_intelligent_strategy(
                    city=strategy.city,
                    state=strategy.state,
                    category=strategy.category,
                    country=strategy.country,
                    limit_per_zone=limit_per_zone,
                    center_lat=strategy.city_center_lat,
                    center_lon=strategy.city_center_lon
                )
                
                zones_scraped += 1
                total_businesses += result["results"]["raw_businesses"]
                total_qualified += result["results"]["qualified_leads"]
                
                # Refresh strategy
                await self.db.refresh(strategy)
                
            except Exception as e:
                logger.error(f"Error in batch execution for zone {next_zone['zone_id']}: {e}")
                # Continue with next zone even if one fails
                continue
        
        return {
            "strategy_id": strategy_id,
            "city": strategy.city,
            "state": strategy.state,
            "category": strategy.category,
            "batch_results": {
                "zones_scraped_in_batch": zones_scraped,
                "businesses_found_in_batch": total_businesses,
                "qualified_in_batch": total_qualified
            },
            "overall_progress": {
                "total_zones": strategy.total_zones,
                "zones_completed": strategy.zones_completed,
                "zones_remaining": strategy.total_zones - strategy.zones_completed,
                "total_businesses_found": strategy.businesses_found,
                "completion_pct": round((strategy.zones_completed / strategy.total_zones) * 100, 1)
            },
            "status": strategy.is_active
        }
    
    async def get_strategy_status(self, strategy_id: str) -> Dict[str, Any]:
        """
        Get current status of a strategy.
        
        Args:
            strategy_id: Strategy UUID
            
        Returns:
            Status dictionary
        """
        strategy = await self.geo_strategy_service.get_strategy_by_id(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        return strategy.to_dict()
    
    async def list_active_strategies(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List active strategies with optional filters.
        
        Args:
            city: Filter by city
            state: Filter by state
            category: Filter by category
            
        Returns:
            List of strategy dictionaries
        """
        strategies = await self.geo_strategy_service.list_strategies(
            city=city,
            state=state,
            category=category,
            status="active"
        )
        
        return [s.to_dict() for s in strategies]
    
    # Legacy method - kept for backward compatibility
    async def scrape_location(
        self,
        city: str,
        state: str,
        industry: str,
        country: str = "US",
        limit: int = 50,
        priority: int = 0,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        LEGACY: Simple single-query scraping without intelligent strategy.
        
        For new code, use scrape_with_intelligent_strategy instead.
        This method is kept for backward compatibility.
        """
        logger.warning(
            f"Using legacy scrape_location for {industry} in {city}, {state}. "
            "Consider using scrape_with_intelligent_strategy for better coverage."
        )
        
        # Use the old simple approach
        results = await self.scraper.search_businesses(
            query=industry,
            city=city,
            state=state,
            country=country,
            limit=limit,
            offset=offset
        )
        
        raw_businesses = results.get("businesses", [])
        
        # Process businesses
        qualified_count = 0
        for biz_data in raw_businesses:
            try:
                # Validate website
                website_url = biz_data.get("website")
                if website_url:
                    website_status = await self.website_validator.validate_website(website_url)
                    biz_data["website_status"] = website_status
                
                # Qualify
                qualification_result = self.qualifier.qualify(biz_data)
                is_qualified = qualification_result["qualified"]
                score = qualification_result["score"]
                reasons = qualification_result["reasons"]
                
                if is_qualified:
                    await self.business_service.create_or_update_business(
                        data=biz_data,
                        source="outscraper_gmaps",
                        discovery_city=city,
                        discovery_state=state,
                        lead_score=score,
                        qualification_reasons=reasons
                    )
                    qualified_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing business: {e}")
                continue
        
        # Update coverage
        await self.coverage_service.update_or_create_coverage(
            city=city,
            state=state,
            country=country,
            industry=industry,
            priority=priority,
            total_found=len(raw_businesses),
            qualified=qualified_count
        )
        
        return {
            "city": city,
            "state": state,
            "industry": industry,
            "results": {
                "total_found": len(raw_businesses),
                "qualified_leads": qualified_count
            }
        }
