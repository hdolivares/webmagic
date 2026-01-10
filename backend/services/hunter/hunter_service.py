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
            raw_businesses = await self.scraper.search_businesses(
                query=industry,
                city=city,
                state=state,
                country=country,
                limit=limit
            )
            
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
