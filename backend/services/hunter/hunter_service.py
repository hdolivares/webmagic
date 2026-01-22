"""
Main Hunter orchestration service - coordinates scraping workflow.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from services.hunter.scraper import OutscraperClient
from services.hunter.filters import LeadQualifier
from services.hunter.business_service import BusinessService
from services.hunter.coverage_service import CoverageService
from services.hunter.geo_grid import (
    create_city_grid,
    should_subdivide_city,
    GeoGrid
)
from services.hunter.website_validator import WebsiteValidator
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)


class HunterService:
    """
    Main orchestration service for the Hunter module.
    Coordinates scraping, filtering, and storing leads.
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
    
    async def scrape_location_with_zones(
        self,
        city: str,
        state: str,
        industry: str,
        country: str = "US",
        limit_per_zone: int = 50,
        priority: int = 0,
        population: Optional[int] = None,
        city_lat: Optional[float] = None,
        city_lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Scrape a location with automatic geo-grid subdivision for better coverage.
        
        For cities with 100K+ population, this subdivides the city into geographic
        zones and scrapes each zone independently, ensuring comprehensive coverage.
        
        Args:
            city: City name
            state: State code
            industry: Industry/category
            country: Country code
            limit_per_zone: Maximum results per zone
            priority: Priority level
            population: City population (for grid calculation)
            city_lat: City center latitude
            city_lon: City center longitude
            
        Returns:
            Dictionary with aggregated results from all zones
        """
        logger.info(f"Starting geo-grid scrape: {city}, {state} - {industry}")
        
        # Check if city should be subdivided
        if population and should_subdivide_city(population) and city_lat and city_lon:
            # Create geo-grid zones
            zones = create_city_grid(
                city=city,
                state=state,
                center_lat=city_lat,
                center_lon=city_lon,
                population=population
            )
            
            logger.info(f"City subdivided into {len(zones)} zones for comprehensive coverage")
            
            # Scrape each zone
            all_results = []
            total_scraped = 0
            total_qualified = 0
            total_saved = 0
            
            for zone in zones:
                try:
                    result = await self.scrape_zone(
                        city=city,
                        state=state,
                        industry=industry,
                        country=country,
                        zone=zone,
                        limit=limit_per_zone,
                        priority=priority
                    )
                    
                    all_results.append(result)
                    total_scraped += result.get("scraped", 0)
                    total_qualified += result.get("qualified", 0)
                    total_saved += result.get("saved", 0)
                    
                except Exception as e:
                    logger.error(f"Failed to scrape zone {zone.zone_id}: {str(e)}")
                    continue
            
            return {
                "status": "completed",
                "location": f"{city}, {state}",
                "industry": industry,
                "zones_scraped": len(zones),
                "total_scraped": total_scraped,
                "total_qualified": total_qualified,
                "total_saved": total_saved,
                "zone_results": all_results,
                "message": f"Scraped {len(zones)} zones, found {total_saved} qualified businesses"
            }
        else:
            # Fall back to single-zone scrape
            logger.info("Population below threshold or coordinates missing - using single-zone scrape")
            return await self.scrape_location(
                city=city,
                state=state,
                industry=industry,
                country=country,
                limit=limit_per_zone,
                priority=priority
            )
    
    async def scrape_zone(
        self,
        city: str,
        state: str,
        industry: str,
        zone: GeoGrid,
        country: str = "US",
        limit: int = 50,
        priority: int = 0
    ) -> Dict[str, Any]:
        """
        Scrape a specific geographic zone.
        
        Args:
            city: City name
            state: State code
            industry: Industry/category
            zone: GeoGrid zone to scrape
            country: Country code
            limit: Maximum results
            priority: Priority level
            
        Returns:
            Dictionary with zone scraping results
        """
        logger.info(f"Scraping zone {zone.zone_id}: {zone.zone_name}")
        
        try:
            # Get or create coverage for this zone
            coverage, created = await self.coverage_service.get_or_create_coverage(
                state=state,
                city=city,
                industry=industry,
                country=country,
                priority=priority,
                zone_id=zone.zone_id,
                zone_lat=str(zone.center_lat),
                zone_lon=str(zone.center_lon),
                zone_radius_km=str(zone.radius_km)
            )
            
            # Mark in progress
            await self.coverage_service.mark_in_progress(coverage.id)
            
            # Scrape businesses using geo-coordinates
            scrape_result = await self.scraper.search_businesses(
                query=industry,
                city=city,
                state=state,
                country=country,
                limit=limit,
                zone_lat=zone.center_lat,
                zone_lon=zone.center_lon,
                zone_id=zone.zone_id
            )
            
            raw_businesses = scrape_result.get("businesses", [])
            
            if not raw_businesses:
                await self.coverage_service.mark_completed(
                    coverage.id,
                    lead_count=0,
                    qualified_count=0
                )
                return {
                    "zone_id": zone.zone_id,
                    "scraped": 0,
                    "qualified": 0,
                    "saved": 0
                }
            
            # Filter and qualify
            qualified_businesses = self.qualifier.filter_batch(
                raw_businesses,
                update_in_place=True
            )
            
            # Validate websites for qualified businesses
            await self.validate_websites(qualified_businesses)
            
            # Save to database
            created_businesses = await self.business_service.bulk_create_businesses(
                qualified_businesses,
                coverage_grid_id=coverage.id
            )
            
            # Mark completed
            await self.coverage_service.mark_completed(
                coverage.id,
                lead_count=len(raw_businesses),
                qualified_count=len(qualified_businesses),
                cooldown_hours=168
            )
            
            logger.info(
                f"Zone {zone.zone_id} complete: "
                f"{len(created_businesses)} businesses saved"
            )
            
            return {
                "zone_id": zone.zone_id,
                "coverage_id": str(coverage.id),
                "scraped": len(raw_businesses),
                "qualified": len(qualified_businesses),
                "saved": len(created_businesses),
                "has_more": scrape_result.get("has_more", False)
            }
            
        except Exception as e:
            logger.error(f"Zone scraping failed for {zone.zone_id}: {str(e)}")
            return {
                "zone_id": zone.zone_id,
                "scraped": 0,
                "qualified": 0,
                "saved": 0,
                "error": str(e)
            }
    
    async def validate_websites(self, businesses: List[Dict[str, Any]]) -> None:
        """
        Validate website URLs for businesses and update their data.
        
        Args:
            businesses: List of business dictionaries (modified in place)
        """
        # Extract URLs that need validation
        urls_to_check = []
        business_map = {}
        
        for i, business in enumerate(businesses):
            url = business.get("website_url")
            if url:
                urls_to_check.append(url)
                business_map[url] = i
        
        if not urls_to_check:
            logger.info("No websites to validate")
            return
        
        logger.info(f"Validating {len(urls_to_check)} website URLs...")
        
        # Validate websites
        async with WebsiteValidator(timeout=8) as validator:
            results = await validator.validate_batch(urls_to_check, max_concurrent=10)
        
        # Update business data based on validation results
        valid_count = 0
        invalid_count = 0
        
        for result in results:
            business_idx = business_map.get(result.url)
            if business_idx is not None:
                business = businesses[business_idx]
                
                if result.is_valid:
                    # Website is valid - mark as having a real website
                    business["has_valid_website"] = True
                    business["website_status"] = "valid"
                    valid_count += 1
                else:
                    # Website is invalid - this business needs a website!
                    business["has_valid_website"] = False
                    business["website_status"] = "invalid"
                    business["website_validation_error"] = result.error_message
                    invalid_count += 1
                    
                    # Increase qualification score (no valid website = better lead!)
                    if "qualification_score" in business:
                        business["qualification_score"] = min(100, business["qualification_score"] + 20)
        
        logger.info(
            f"Website validation complete: {valid_count} valid, {invalid_count} invalid/unreachable"
        )
    
    async def scrape_location(
        self,
        city: str,
        state: str,
        industry: str,
        country: str = "US",
        limit: int = 50,
        priority: int = 0
    ) -> Dict[str, Any]:
        """
        Scrape a specific location for an industry.
        Main entry point for scraping operations.
        
        Workflow:
        1. Get or create coverage grid entry
        2. Mark as in_progress
        3. Scrape businesses from Outscraper
        4. Filter/qualify leads
        5. Save to database
        6. Mark coverage as completed
        7. Return results
        
        Args:
            city: City name
            state: State code
            industry: Industry/category
            country: Country code
            limit: Maximum results to scrape
            priority: Priority level for coverage
            
        Returns:
            Dictionary with results summary
        """
        logger.info(f"Starting scrape: {city}, {state} - {industry}")
        
        try:
            # 1. Get or create coverage
            coverage, created = await self.coverage_service.get_or_create_coverage(
                state=state,
                city=city,
                industry=industry,
                country=country,
                priority=priority
            )
            
            if created:
                logger.info(f"Created new coverage entry: {coverage.id}")
            else:
                logger.info(f"Using existing coverage entry: {coverage.id}")
            
            # 2. Mark in progress
            await self.coverage_service.mark_in_progress(coverage.id)
            
            # 3. Scrape businesses
            logger.info(f"Scraping from Outscraper (limit: {limit})...")
            scrape_result = await self.scraper.search_businesses(
                query=industry,
                city=city,
                state=state,
                country=country,
                limit=limit
            )
            
            raw_businesses = scrape_result.get("businesses", [])
            
            if not raw_businesses:
                logger.warning("No businesses found")
                await self.coverage_service.mark_completed(
                    coverage.id,
                    lead_count=0,
                    qualified_count=0
                )
                return {
                    "coverage_id": str(coverage.id),
                    "status": "completed",
                    "scraped": 0,
                    "qualified": 0,
                    "saved": 0,
                    "message": "No businesses found"
                }
            
            logger.info(f"Scraped {len(raw_businesses)} businesses")
            
            # 4. Filter and qualify
            logger.info("Filtering and qualifying leads...")
            qualified_businesses = self.qualifier.filter_batch(
                raw_businesses,
                update_in_place=True
            )
            
            # 4.5. Validate websites
            logger.info("Validating website URLs...")
            await self.validate_websites(qualified_businesses)
            
            logger.info(
                f"Qualified {len(qualified_businesses)}/{len(raw_businesses)} businesses "
                f"({len(qualified_businesses)/len(raw_businesses)*100:.1f}%)"
            )
            
            # 5. Save to database
            logger.info("Saving businesses to database...")
            created_businesses = await self.business_service.bulk_create_businesses(
                qualified_businesses,
                coverage_grid_id=coverage.id
            )
            
            logger.info(f"Saved {len(created_businesses)} new businesses")
            
            # 6. Mark coverage as completed
            await self.coverage_service.mark_completed(
                coverage.id,
                lead_count=len(raw_businesses),
                qualified_count=len(qualified_businesses),
                cooldown_hours=168  # 7 days
            )
            
            # 7. Prepare results
            results = {
                "coverage_id": str(coverage.id),
                "status": "completed",
                "location": f"{city}, {state}, {country}",
                "industry": industry,
                "scraped": len(raw_businesses),
                "qualified": len(qualified_businesses),
                "saved": len(created_businesses),
                "qualification_rate": (
                    len(qualified_businesses) / len(raw_businesses) * 100
                    if raw_businesses else 0
                ),
                "message": f"Successfully scraped and saved {len(created_businesses)} businesses"
            }
            
            # Add some sample businesses to results
            if created_businesses:
                results["sample_businesses"] = [
                    {
                        "id": str(b.id),
                        "name": b.name,
                        "email": b.email,
                        "rating": float(b.rating) if b.rating else None,
                        "qualification_score": b.qualification_score
                    }
                    for b in created_businesses[:5]  # First 5
                ]
            
            logger.info(f"Scraping completed successfully: {results['message']}")
            return results
            
        except ExternalAPIException as e:
            logger.error(f"Scraping failed: {str(e)}")
            
            # Mark coverage as pending again if it exists
            if 'coverage' in locals():
                await self.coverage_service.update_coverage(
                    coverage.id,
                    {"status": "pending"}
                )
            
            return {
                "status": "failed",
                "error": str(e),
                "message": "Scraping failed"
            }
        
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {str(e)}", exc_info=True)
            
            # Mark coverage as pending again
            if 'coverage' in locals():
                await self.coverage_service.update_coverage(
                    coverage.id,
                    {"status": "pending"}
                )
            
            return {
                "status": "failed",
                "error": str(e),
                "message": "Unexpected error during scraping"
            }
    
    async def scrape_next_target(self, limit: int = 50) -> Optional[Dict[str, Any]]:
        """
        Automatically scrape the next highest-priority target.
        
        Args:
            limit: Maximum results per scrape
            
        Returns:
            Scraping results or None if no targets available
        """
        logger.info("Looking for next scraping target...")
        
        # Get next target from coverage grid
        targets = await self.coverage_service.get_next_target(
            limit=1,
            exclude_cooldown=True
        )
        
        if not targets:
            logger.info("No scraping targets available")
            return None
        
        target = targets[0]
        
        # Scrape the target
        return await self.scrape_location(
            city=target.city,
            state=target.state,
            industry=target.industry,
            country=target.country,
            limit=limit,
            priority=target.priority
        )
    
    async def get_scraping_report(self) -> Dict[str, Any]:
        """
        Get comprehensive scraping report.
        
        Returns:
            Dictionary with scraping statistics
        """
        coverage_stats = await self.coverage_service.get_stats()
        business_stats = await self.business_service.get_stats()
        
        return {
            "coverage": coverage_stats,
            "businesses": business_stats,
            "summary": {
                "territories_tracked": coverage_stats["total_territories"],
                "territories_pending": coverage_stats["pending"],
                "total_leads_scraped": coverage_stats["total_leads"],
                "total_leads_qualified": coverage_stats["total_qualified"],
                "total_businesses_in_db": business_stats["total_leads"],
                "businesses_with_email": business_stats["with_email"],
                "businesses_without_website": business_stats["without_website"]
            }
        }
