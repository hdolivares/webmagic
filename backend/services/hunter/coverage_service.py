"""
Coverage Grid service for managing scraping territories.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from uuid import UUID
from datetime import datetime, timedelta
import logging

from models.coverage import CoverageGrid
from core.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class CoverageService:
    """Service for coverage grid management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_coverage(
        self,
        state: str,
        city: str,
        industry: str,
        country: str = "US",
        priority: int = 0,
        **kwargs
    ) -> CoverageGrid:
        """
        Create a new coverage grid entry.
        
        Args:
            state: State code (e.g., "TX", "CA")
            city: City name
            industry: Industry/category
            country: Country code (default: "US")
            priority: Priority level (0-100)
            **kwargs: Additional fields
            
        Returns:
            Created CoverageGrid instance
        """
        try:
            # Log kwargs for debugging type issues
            logger.debug(f"Creating coverage with kwargs: {kwargs}")
            
            # Type validation for common issues
            if "zone_lat" in kwargs and kwargs["zone_lat"] is not None and not isinstance(kwargs["zone_lat"], str):
                logger.warning(f"zone_lat should be string, got {type(kwargs['zone_lat']).__name__}: {kwargs['zone_lat']}")
            if "zone_lon" in kwargs and kwargs["zone_lon"] is not None and not isinstance(kwargs["zone_lon"], str):
                logger.warning(f"zone_lon should be string, got {type(kwargs['zone_lon']).__name__}: {kwargs['zone_lon']}")
            if "zone_radius_km" in kwargs and kwargs["zone_radius_km"] is not None and not isinstance(kwargs["zone_radius_km"], str):
                logger.warning(f"zone_radius_km should be string, got {type(kwargs['zone_radius_km']).__name__}: {kwargs['zone_radius_km']}")
            
            # Use a savepoint so a constraint violation (e.g., duplicate key) only
            # rolls back this insert — not any enclosing transaction.
            async with self.db.begin_nested():
                coverage = CoverageGrid(
                    state=state,
                    city=city,
                    country=country,
                    industry=industry,
                    priority=priority,
                    **kwargs
                )
                
                self.db.add(coverage)
                await self.db.flush()
                await self.db.refresh(coverage)
            
            logger.info(f"Created coverage: {coverage.full_key}")
            return coverage
            
        except Exception as e:
            logger.error(f"Error creating coverage: {str(e)}")
            logger.error(f"Coverage params - state={state}, city={city}, industry={industry}, kwargs={kwargs}")
            raise DatabaseException(f"Failed to create coverage: {str(e)}")
    
    async def get_coverage(self, coverage_id: UUID) -> Optional[CoverageGrid]:
        """Get coverage by ID."""
        result = await self.db.execute(
            select(CoverageGrid).where(CoverageGrid.id == coverage_id)
        )
        return result.scalar_one_or_none()
    
    async def get_coverage_by_key(
        self,
        state: str,
        city: str,
        industry: str,
        country: str = "US",
        zone_id: Optional[str] = None
    ) -> Optional[CoverageGrid]:
        """Get coverage by location, industry, and optionally zone."""
        conditions = [
            CoverageGrid.country == country,
            CoverageGrid.state == state,
            CoverageGrid.city == city,
            CoverageGrid.industry == industry
        ]
        
        # If zone_id provided, include it in the search
        if zone_id:
            conditions.append(CoverageGrid.zone_id == zone_id)
        else:
            # If no zone_id, match entries without a zone
            conditions.append(CoverageGrid.zone_id.is_(None))
        
        result = await self.db.execute(
            select(CoverageGrid).where(and_(*conditions))
        )
        return result.scalar_one_or_none()
    
    async def get_or_create_coverage(
        self,
        state: str,
        city: str,
        industry: str,
        country: str = "US",
        **kwargs
    ) -> tuple[CoverageGrid, bool]:
        """
        Get existing coverage or create if not exists.
        
        Returns:
            Tuple of (coverage, created_bool)
        """
        # Extract zone_id if present to check for existing zone
        zone_id = kwargs.get("zone_id")
        
        existing = await self.get_coverage_by_key(
            state, city, industry, country, zone_id=zone_id
        )
        if existing:
            return existing, False
        
        coverage = await self.create_coverage(
            state, city, industry, country, **kwargs
        )
        return coverage, True
    
    async def list_coverage(
        self,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> tuple[List[CoverageGrid], int]:
        """
        List coverage entries with pagination and filters.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters (e.g., {"status": "pending", "priority__gte": 50})
            
        Returns:
            Tuple of (coverage list, total count)
        """
        # Build query
        query = select(CoverageGrid)
        count_query = select(func.count(CoverageGrid.id))
        
        # Apply filters
        if filters:
            conditions = self._build_filter_conditions(filters)
            if conditions:
                query = query.where(and_(*conditions))
                count_query = count_query.where(and_(*conditions))
        
        # Add ordering (priority desc, then by created_at)
        query = query.order_by(
            CoverageGrid.priority.desc(),
            CoverageGrid.created_at.desc()
        )
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        coverage_entries = result.scalars().all()
        
        return list(coverage_entries), total
    
    async def update_coverage(
        self,
        coverage_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[CoverageGrid]:
        """Update coverage fields."""
        try:
            updates["updated_at"] = datetime.utcnow()
            
            await self.db.execute(
                update(CoverageGrid)
                .where(CoverageGrid.id == coverage_id)
                .values(**updates)
            )
            await self.db.flush()
            
            return await self.get_coverage(coverage_id)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating coverage: {str(e)}")
            raise DatabaseException(f"Failed to update coverage: {str(e)}")
    
    async def get_next_target(
        self,
        limit: int = 1,
        exclude_cooldown: bool = True
    ) -> Optional[List[CoverageGrid]]:
        """
        Get next coverage target(s) to scrape based on priority and status.
        
        Priority order:
        1. Status = pending (never scraped)
        2. Status = completed but not on cooldown
        3. Highest priority score
        4. Oldest last_scraped_at
        
        Args:
            limit: Number of targets to return
            exclude_cooldown: Exclude entries on cooldown
            
        Returns:
            List of CoverageGrid instances or None if no targets available
        """
        query = select(CoverageGrid)
        
        # Exclude in_progress to avoid concurrent scraping
        conditions = [CoverageGrid.status != "in_progress"]
        
        # Exclude cooldown if requested
        if exclude_cooldown:
            now = datetime.utcnow()
            conditions.append(
                or_(
                    CoverageGrid.cooldown_until.is_(None),
                    CoverageGrid.cooldown_until < now
                )
            )
        
        query = query.where(and_(*conditions))
        
        # Order by: pending first, then by priority, then by oldest scraped
        query = query.order_by(
            CoverageGrid.status == "pending",  # pending first (True sorts before False)
            CoverageGrid.priority.desc(),
            CoverageGrid.last_scraped_at.asc().nullsfirst()
        ).limit(limit)
        
        result = await self.db.execute(query)
        targets = result.scalars().all()
        
        if targets:
            logger.info(f"Selected {len(targets)} scraping target(s)")
            for target in targets:
                logger.info(
                    f"  - {target.city}, {target.state} - {target.industry} "
                    f"(priority: {target.priority}, status: {target.status})"
                )
            return list(targets)
        
        logger.warning("No scraping targets available")
        return None
    
    async def mark_in_progress(self, coverage_id: UUID) -> bool:
        """Mark coverage as in_progress."""
        return await self.update_coverage(
            coverage_id,
            {"status": "in_progress"}
        ) is not None
    
    async def mark_completed(
        self,
        coverage_id: UUID,
        lead_count: int,
        qualified_count: int,
        cooldown_hours: int = 168  # 7 days default
    ) -> bool:
        """
        Mark coverage as completed and set cooldown.
        
        Args:
            coverage_id: Coverage ID
            lead_count: Number of leads scraped
            qualified_count: Number of qualified leads
            cooldown_hours: Hours until can be rescraped (default: 7 days)
        """
        cooldown_until = datetime.utcnow() + timedelta(hours=cooldown_hours)
        
        return await self.update_coverage(
            coverage_id,
            {
                "status": "completed",
                "last_scraped_at": datetime.utcnow(),
                "cooldown_until": cooldown_until,
                "lead_count": lead_count,
                "qualified_count": qualified_count
            }
        ) is not None
    
    async def increment_metrics(
        self,
        coverage_id: UUID,
        sites: int = 0,
        conversions: int = 0
    ) -> bool:
        """Increment site_count and conversion_count."""
        coverage = await self.get_coverage(coverage_id)
        if not coverage:
            return False
        
        updates = {}
        if sites > 0:
            updates["site_count"] = coverage.site_count + sites
        if conversions > 0:
            updates["conversion_count"] = coverage.conversion_count + conversions
        
        if updates:
            await self.update_coverage(coverage_id, updates)
        
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get coverage statistics."""
        # Total territories
        total_result = await self.db.execute(
            select(func.count(CoverageGrid.id))
        )
        total = total_result.scalar()
        
        # By status
        by_status = {}
        status_result = await self.db.execute(
            select(CoverageGrid.status, func.count(CoverageGrid.id))
            .group_by(CoverageGrid.status)
        )
        for status, count in status_result:
            by_status[status] = count
        
        # Total leads and qualified
        metrics_result = await self.db.execute(
            select(
                func.sum(CoverageGrid.lead_count),
                func.sum(CoverageGrid.qualified_count)
            )
        )
        total_leads, total_qualified = metrics_result.first()
        
        # Average qualification rate
        avg_qual_rate = 0
        if total_leads and total_leads > 0:
            avg_qual_rate = (total_qualified / total_leads) * 100
        
        # By state (top 10)
        by_state = {}
        state_result = await self.db.execute(
            select(CoverageGrid.state, func.count(CoverageGrid.id))
            .group_by(CoverageGrid.state)
            .order_by(func.count(CoverageGrid.id).desc())
            .limit(10)
        )
        for state, count in state_result:
            by_state[state] = count
        
        # By industry (top 10)
        by_industry = {}
        industry_result = await self.db.execute(
            select(CoverageGrid.industry, func.count(CoverageGrid.id))
            .group_by(CoverageGrid.industry)
            .order_by(func.count(CoverageGrid.id).desc())
            .limit(10)
        )
        for industry, count in industry_result:
            by_industry[industry] = count
        
        return {
            "total_territories": total,
            "pending": by_status.get("pending", 0),
            "in_progress": by_status.get("in_progress", 0),
            "completed": by_status.get("completed", 0),
            "cooldown": by_status.get("cooldown", 0),
            "total_leads": total_leads or 0,
            "total_qualified": total_qualified or 0,
            "avg_qualification_rate": avg_qual_rate,
            "by_state": by_state,
            "by_industry": by_industry
        }
    
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> List:
        """Build SQLAlchemy filter conditions from dict."""
        conditions = []
        
        for key, value in filters.items():
            if "__" in key:
                field_name, operator = key.split("__", 1)
                field = getattr(CoverageGrid, field_name, None)
                if field is None:
                    continue
                
                if operator == "gte":
                    conditions.append(field >= value)
                elif operator == "lte":
                    conditions.append(field <= value)
                elif operator == "gt":
                    conditions.append(field > value)
                elif operator == "lt":
                    conditions.append(field < value)
                elif operator == "ne":
                    conditions.append(field != value)
                elif operator == "in":
                    conditions.append(field.in_(value))
            else:
                field = getattr(CoverageGrid, key, None)
                if field is not None:
                    conditions.append(field == value)
        
        return conditions
