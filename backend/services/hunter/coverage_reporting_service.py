"""
Coverage Reporting Service.

Generates comprehensive coverage statistics and reports with detailed
breakdowns of scraping results, qualification rates, and website generation progress.
"""
import logging
from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models.coverage import CoverageGrid
from models.business import Business
from models.geo_strategy import GeoStrategy

logger = logging.getLogger(__name__)


class CoverageReportingService:
    """
    Generates coverage reports and statistics.
    
    Provides comprehensive breakdowns of scraping results, qualification rates,
    and website generation progress for display on the coverage page.
    
    Key Features:
    - Per-zone detailed statistics
    - Strategy-wide aggregated metrics
    - Persistent scrape result display
    - Website generation progress tracking
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize coverage reporting service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_zone_statistics(self, zone_id: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a specific zone.
        
        Args:
            zone_id: Zone identifier (e.g., "la_downtown")
            
        Returns:
            Dict with comprehensive zone metrics:
            {
                "zone_id": "la_downtown",
                "coverage_id": "uuid",
                "status": "completed",
                "total_businesses": 50,
                "qualified_leads": 35,
                "with_websites": 20,
                "without_websites": 15,
                "invalid_websites": 5,
                "websites_generated": 10,
                "generation_in_progress": 5,
                "generation_pending": 10,
                "last_scraped_at": "2026-02-04T...",
                "last_scrape_details": {...},
                "avg_rating": 4.5,
                "avg_qualification_score": 72.3,
                "qualification_rate": 70.0,
                "website_coverage_rate": 40.0
            }
        """
        # Get coverage entry
        # NOTE: Using .scalars().first() instead of .scalar_one_or_none() to handle 
        # legacy duplicate zone_ids (before category was added to zone_id generation)
        result = await self.db.execute(
            select(CoverageGrid)
            .where(CoverageGrid.zone_id == zone_id)
            .order_by(CoverageGrid.created_at.desc())  # Get most recent if duplicates exist
        )
        coverage = result.scalars().first()
        
        if not coverage:
            logger.warning(f"Zone not found: {zone_id}")
            return {'error': 'Zone not found', 'zone_id': zone_id}
        
        # Get businesses for this zone
        businesses_result = await self.db.execute(
            select(Business).where(Business.coverage_grid_id == coverage.id)
        )
        businesses = businesses_result.scalars().all()
        
        # Calculate statistics
        total_businesses = len(businesses)
        with_websites = coverage.businesses_with_websites or 0
        without_websites = coverage.businesses_without_websites or 0
        invalid_websites = coverage.invalid_websites or 0
        websites_generated = coverage.websites_generated or 0
        generation_in_progress = coverage.generation_in_progress or 0
        
        # Calculate generation pending (need websites but not yet generated/in progress)
        generation_pending = max(0, without_websites - websites_generated - generation_in_progress)
        
        # Calculate rates
        qualification_rate = None
        if coverage.last_scrape_size and coverage.last_scrape_size > 0:
            qualification_rate = round(
                (coverage.qualified_count / coverage.last_scrape_size) * 100, 1
            )
        
        website_coverage_rate = None
        if total_businesses > 0:
            website_coverage_rate = round(
                ((with_websites + websites_generated) / total_businesses) * 100, 1
            )
        
        return {
            'zone_id': zone_id,
            'coverage_id': str(coverage.id),
            'status': coverage.status,
            'total_businesses': total_businesses,
            'qualified_leads': coverage.qualified_count or 0,
            'with_websites': with_websites,
            'without_websites': without_websites,
            'invalid_websites': invalid_websites,
            'websites_generated': websites_generated,
            'generation_in_progress': generation_in_progress,
            'generation_pending': generation_pending,
            'last_scraped_at': coverage.last_scraped_at.isoformat() if coverage.last_scraped_at else None,
            'last_scrape_details': coverage.last_scrape_details,
            'avg_rating': float(coverage.avg_rating) if coverage.avg_rating else None,
            'avg_qualification_score': float(coverage.avg_qualification_score) if coverage.avg_qualification_score else None,
            'qualification_rate': qualification_rate,
            'website_coverage_rate': website_coverage_rate,
            'raw_data': {
                'lead_count': coverage.lead_count,
                'last_scrape_size': coverage.last_scrape_size,
                'scrape_count': coverage.scrape_count
            }
        }
    
    async def get_strategy_overview(self, strategy_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive overview of a geo-strategy.
        
        Args:
            strategy_id: GeoStrategy UUID
            
        Returns:
            Dict with strategy-wide statistics:
            {
                "strategy_id": "uuid",
                "city": "Los Angeles",
                "state": "CA",
                "category": "plumbers",
                "status": "active",
                "zones": {
                    "total": 18,
                    "completed": 5,
                    "in_progress": 1,
                    "pending": 12
                },
                "businesses": {
                    "total": 250,
                    "qualified": 180,
                    "with_websites": 100,
                    "without_websites": 80,
                    "websites_generated": 30,
                    "generation_pending": 50
                },
                "performance": {
                    "avg_businesses_per_zone": 50.0,
                    "completion_rate": 27.8,
                    "qualification_rate": 72.0,
                    "website_coverage_rate": 52.0
                },
                "zone_details": [...]
            }
        """
        # Get strategy
        result = await self.db.execute(
            select(GeoStrategy).where(GeoStrategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            logger.warning(f"Strategy not found: {strategy_id}")
            return {'error': 'Strategy not found', 'strategy_id': str(strategy_id)}
        
        # Get all coverage entries for this strategy
        coverage_result = await self.db.execute(
            select(CoverageGrid).where(
                and_(
                    CoverageGrid.city == strategy.city,
                    CoverageGrid.state == strategy.state,
                    CoverageGrid.industry == strategy.category
                )
            )
        )
        coverage_entries = coverage_result.scalars().all()
        
        # Aggregate statistics
        total_zones = strategy.total_zones
        zones_completed = strategy.zones_completed
        zones_in_progress = 1 if strategy.zones_completed < total_zones else 0
        zones_pending = total_zones - zones_completed - zones_in_progress
        
        total_businesses = sum(c.lead_count for c in coverage_entries)
        total_qualified = sum(c.qualified_count or 0 for c in coverage_entries)
        total_with_websites = sum(c.businesses_with_websites or 0 for c in coverage_entries)
        total_without_websites = sum(c.businesses_without_websites or 0 for c in coverage_entries)
        total_websites_generated = sum(c.websites_generated or 0 for c in coverage_entries)
        total_generation_in_progress = sum(c.generation_in_progress or 0 for c in coverage_entries)
        
        generation_pending = max(0, total_without_websites - total_websites_generated - total_generation_in_progress)
        
        # Calculate rates
        avg_businesses_per_zone = round(total_businesses / zones_completed, 1) if zones_completed > 0 else 0
        completion_rate = round((zones_completed / total_zones) * 100, 1) if total_zones > 0 else 0
        qualification_rate = round((total_qualified / total_businesses) * 100, 1) if total_businesses > 0 else 0
        website_coverage_rate = round(
            ((total_with_websites + total_websites_generated) / total_businesses) * 100, 1
        ) if total_businesses > 0 else 0
        
        # Per-zone breakdown
        zone_details = []
        for zone in strategy.zones:
            zone_id = zone.get('zone_id')
            zone_stats = await self.get_zone_statistics(zone_id)
            if 'error' not in zone_stats:
                zone_details.append(zone_stats)
        
        return {
            'strategy_id': str(strategy_id),
            'city': strategy.city,
            'state': strategy.state,
            'category': strategy.category,
            'status': strategy.is_active,
            'zones': {
                'total': total_zones,
                'completed': zones_completed,
                'in_progress': zones_in_progress,
                'pending': zones_pending
            },
            'businesses': {
                'total': total_businesses,
                'qualified': total_qualified,
                'with_websites': total_with_websites,
                'without_websites': total_without_websites,
                'websites_generated': total_websites_generated,
                'generation_in_progress': total_generation_in_progress,
                'generation_pending': generation_pending
            },
            'performance': {
                'avg_businesses_per_zone': avg_businesses_per_zone,
                'completion_rate': completion_rate,
                'qualification_rate': qualification_rate,
                'website_coverage_rate': website_coverage_rate
            },
            'zone_details': zone_details
        }
    
    async def get_coverage_breakdown(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get coverage breakdown with optional filters.
        
        Args:
            city: Filter by city (optional)
            state: Filter by state (optional)
            category: Filter by category/industry (optional)
            
        Returns:
            Dict with aggregated coverage breakdown
        """
        # Build query with filters
        conditions = []
        if city:
            conditions.append(CoverageGrid.city == city)
        if state:
            conditions.append(CoverageGrid.state == state)
        if category:
            conditions.append(CoverageGrid.industry == category)
        
        query = select(CoverageGrid)
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        coverage_entries = result.scalars().all()
        
        if not coverage_entries:
            return {
                'total_zones': 0,
                'message': 'No coverage data found'
            }
        
        # Aggregate
        total_businesses = sum(c.lead_count for c in coverage_entries)
        qualified_leads = sum(c.qualified_count or 0 for c in coverage_entries)
        with_websites = sum(c.businesses_with_websites or 0 for c in coverage_entries)
        without_websites = sum(c.businesses_without_websites or 0 for c in coverage_entries)
        invalid_websites = sum(c.invalid_websites or 0 for c in coverage_entries)
        websites_generated = sum(c.websites_generated or 0 for c in coverage_entries)
        generation_pending = max(0, without_websites - websites_generated)
        
        return {
            'total_zones': len(coverage_entries),
            'total_businesses': total_businesses,
            'qualified_leads': qualified_leads,
            'with_websites': with_websites,
            'without_websites': without_websites,
            'invalid_websites': invalid_websites,
            'websites_generated': websites_generated,
            'generation_pending': generation_pending,
            'filters': {
                'city': city,
                'state': state,
                'category': category
            }
        }

