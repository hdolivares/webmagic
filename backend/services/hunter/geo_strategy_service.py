"""
Geo-Strategy Service - Manages intelligent zone placement strategies.

Handles strategy creation, retrieval, execution tracking, and adaptive refinement.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from datetime import datetime
import logging

from models.geo_strategy import GeoStrategy
from services.hunter.geo_strategy_agent import GeoStrategyAgent
from services.hunter.metro_city_strategy import generate_city_based_strategy
from services.geocoding_service import geocoding_service

logger = logging.getLogger(__name__)


class GeoStrategyService:
    """
    Service for managing Claude-powered geographic strategies.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize geo-strategy service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.agent = GeoStrategyAgent()
    
    async def get_or_create_strategy(
        self,
        city: str,
        state: str,
        category: str,
        country: str = "US",
        force_regenerate: bool = False,
        population: Optional[int] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None
    ) -> GeoStrategy:
        """
        Get existing strategy or generate a new one using Claude.
        
        Args:
            city: City name
            state: State code
            category: Business category
            country: Country code
            force_regenerate: Force creation of new strategy even if one exists
            population: City population (optional)
            center_lat: City center latitude (optional, will geocode if not provided)
            center_lon: City center longitude (optional, will geocode if not provided)
        
        Returns:
            GeoStrategy instance (existing or newly created)
        """
        # Check for existing active strategy
        if not force_regenerate:
            existing = await self.get_active_strategy(city, state, category, country)
            if existing:
                logger.info(
                    f"Using existing strategy for {category} in {city}, {state} "
                    f"({existing.zones_completed}/{existing.total_zones} zones complete)"
                )
                return existing
        
        # Geocode city if coordinates or population not provided
        if center_lat is None or center_lon is None or population is None:
            logger.info(f"Geocoding {city}, {state} to get coordinates and population")
            city_data = await geocoding_service.geocode_city(city, state, country)
            if city_data:
                if center_lat is None:
                    center_lat = city_data.latitude
                if center_lon is None:
                    center_lon = city_data.longitude
                if population is None:
                    population = city_data.population
                    logger.info(f"Auto-detected population for {city}, {state}: {population:,}")
            else:
                raise ValueError(f"Could not geocode {city}, {state}")
        
        # If regenerating, mark old strategies as superseded
        if force_regenerate:
            await self._supersede_old_strategies(city, state, category, country)
        
        # Generate new strategy using city-based approach (not Claude)
        # Outscraper ignores coordinates, so we use predefined city lists
        logger.info(f"Generating city-based strategy for {category} in {city}, {state}")
        
        strategy_data = generate_city_based_strategy(
            metro_area=city,
            state=state,
            category=category,
            center_lat=center_lat,
            center_lon=center_lon
        )
        
        # Add model info
        strategy_data["model_used"] = "city-based-v1"
        
        # Create database record
        strategy = GeoStrategy(
            city=city,
            state=state,
            country=country,
            category=category,
            city_center_lat=center_lat,
            city_center_lon=center_lon,
            population=population,
            geographic_analysis=strategy_data.get("geographic_analysis"),
            business_distribution_analysis=strategy_data.get("business_distribution_analysis"),
            strategy_reasoning=strategy_data.get("strategy_reasoning"),
            zones=strategy_data.get("zones"),
            avoid_areas=strategy_data.get("avoid_areas"),
            total_zones=strategy_data.get("total_zones"),
            estimated_total_businesses=strategy_data.get("estimated_total_businesses"),
            estimated_searches_needed=strategy_data.get("estimated_searches_needed"),
            coverage_area_km2=strategy_data.get("coverage_area_km2"),
            model_used=strategy_data.get("model_used", "claude-sonnet-4-5"),
            is_active="active"
        )
        
        self.db.add(strategy)
        await self.db.commit()
        await self.db.refresh(strategy)
        
        logger.info(
            f"Created strategy with {strategy.total_zones} zones, "
            f"estimated {strategy.estimated_total_businesses} businesses"
        )
        
        return strategy
    
    async def get_active_strategy(
        self,
        city: str,
        state: str,
        category: str,
        country: str = "US"
    ) -> Optional[GeoStrategy]:
        """
        Get the active strategy for a city + category combination.
        
        Args:
            city: City name
            state: State code
            category: Business category
            country: Country code
        
        Returns:
            Active GeoStrategy or None
        """
        stmt = select(GeoStrategy).where(
            and_(
                GeoStrategy.city == city,
                GeoStrategy.state == state,
                GeoStrategy.country == country,
                GeoStrategy.category == category,
                GeoStrategy.is_active == "active"
            )
        ).order_by(desc(GeoStrategy.created_at))
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_strategy_by_id(self, strategy_id: str) -> Optional[GeoStrategy]:
        """
        Get strategy by ID.
        
        Args:
            strategy_id: Strategy UUID
        
        Returns:
            GeoStrategy or None
        """
        stmt = select(GeoStrategy).where(GeoStrategy.id == strategy_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_next_zone(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the next zone to scrape from a strategy.
        
        Args:
            strategy_id: Strategy UUID
        
        Returns:
            Zone dictionary or None if all complete
        """
        strategy = await self.get_strategy_by_id(strategy_id)
        if not strategy:
            return None
        
        return strategy.get_next_zone()
    
    async def mark_zone_complete(
        self,
        strategy_id: str,
        zone_id: str,
        businesses_found: int
    ) -> GeoStrategy:
        """
        Mark a zone as completed and update strategy metrics.
        
        Args:
            strategy_id: Strategy UUID
            zone_id: Zone identifier
            businesses_found: Number of businesses discovered
        
        Returns:
            Updated GeoStrategy
        """
        strategy = await self.get_strategy_by_id(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        # Find zone to get estimate
        zone = next((z for z in strategy.zones if z["zone_id"] == zone_id), None)
        estimated = zone.get("estimated_businesses") if zone else None
        
        # Update strategy
        strategy.mark_zone_complete(zone_id, businesses_found, estimated)
        
        await self.db.commit()
        await self.db.refresh(strategy)
        
        logger.info(
            f"Marked zone {zone_id} complete: {businesses_found} businesses found, "
            f"{strategy.zones_completed}/{strategy.total_zones} zones done"
        )
        
        # Check if strategy needs refinement (after 5 zones or every 10)
        if strategy.zones_completed in [5, 10, 20, 30]:
            await self._trigger_refinement(strategy)
        
        return strategy
    
    async def refine_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """
        Use Claude to refine a strategy based on actual performance.
        
        Args:
            strategy_id: Strategy UUID
        
        Returns:
            Refinement suggestions dictionary
        """
        strategy = await self.get_strategy_by_id(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")
        
        if not strategy.performance_data or not strategy.performance_data.get("zone_results"):
            logger.warning(f"No performance data available for strategy {strategy_id}")
            return {"message": "Insufficient data for refinement"}
        
        logger.info(f"Refining strategy {strategy_id} based on {strategy.zones_completed} completed zones")
        
        # Get refinement suggestions from Claude
        refinements = await self.agent.refine_strategy(
            original_strategy=strategy.to_dict(),
            performance_data=strategy.performance_data
        )
        
        # Store refinement notes
        strategy.adaptation_notes = refinements.get("analysis", "")
        
        # TODO: Optionally auto-apply refinements (add new zones, adjust priorities)
        # For now, we'll just log and store the suggestions
        
        await self.db.commit()
        
        logger.info(
            f"Strategy refinement complete: {len(refinements.get('new_zones', []))} "
            f"new zones suggested"
        )
        
        return refinements
    
    async def list_strategies(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[GeoStrategy]:
        """
        List strategies with optional filters.
        
        Args:
            city: Filter by city
            state: Filter by state
            category: Filter by category
            status: Filter by status (active, completed, superseded)
            limit: Maximum results
        
        Returns:
            List of GeoStrategy instances
        """
        stmt = select(GeoStrategy)
        
        conditions = []
        if city:
            conditions.append(GeoStrategy.city == city)
        if state:
            conditions.append(GeoStrategy.state == state)
        if category:
            conditions.append(GeoStrategy.category == category)
        if status:
            conditions.append(GeoStrategy.is_active == status)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(desc(GeoStrategy.created_at)).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_strategy_stats(self) -> Dict[str, Any]:
        """
        Get overall statistics about geo-strategies.
        
        Returns:
            Dictionary with stats
        """
        # Count strategies by status
        stmt = select(GeoStrategy)
        result = await self.db.execute(stmt)
        strategies = result.scalars().all()
        
        stats = {
            "total_strategies": len(strategies),
            "active": sum(1 for s in strategies if s.is_active == "active"),
            "completed": sum(1 for s in strategies if s.is_active == "completed"),
            "superseded": sum(1 for s in strategies if s.is_active == "superseded"),
            "total_zones": sum(s.total_zones for s in strategies),
            "zones_completed": sum(s.zones_completed for s in strategies),
            "businesses_found": sum(s.businesses_found for s in strategies),
            "cities_covered": len(set((s.city, s.state) for s in strategies)),
            "categories_covered": len(set(s.category for s in strategies))
        }
        
        # Calculate average accuracy for completed strategies
        completed_with_accuracy = [
            s for s in strategies
            if s.performance_data and "strategy_accuracy" in s.performance_data
        ]
        
        if completed_with_accuracy:
            avg_accuracy = sum(
                s.performance_data["strategy_accuracy"]
                for s in completed_with_accuracy
            ) / len(completed_with_accuracy)
            stats["avg_strategy_accuracy"] = round(avg_accuracy, 1)
        
        return stats
    
    async def _supersede_old_strategies(
        self,
        city: str,
        state: str,
        category: str,
        country: str
    ):
        """Mark old strategies as superseded."""
        stmt = select(GeoStrategy).where(
            and_(
                GeoStrategy.city == city,
                GeoStrategy.state == state,
                GeoStrategy.country == country,
                GeoStrategy.category == category,
                GeoStrategy.is_active == "active"
            )
        )
        
        result = await self.db.execute(stmt)
        old_strategies = result.scalars().all()
        
        for strategy in old_strategies:
            strategy.is_active = "superseded"
            strategy.updated_at = datetime.utcnow()
        
        if old_strategies:
            await self.db.commit()
            logger.info(f"Superseded {len(old_strategies)} old strategies")
    
    async def _trigger_refinement(self, strategy: GeoStrategy):
        """
        Automatically trigger refinement check at key milestones.
        
        Args:
            strategy: GeoStrategy to potentially refine
        """
        try:
            logger.info(
                f"Checking refinement for strategy {strategy.id} "
                f"at {strategy.zones_completed} zones completed"
            )
            
            # Only refine if we have meaningful data
            if strategy.zones_completed >= 5:
                await self.refine_strategy(str(strategy.id))
        except Exception as e:
            logger.error(f"Auto-refinement failed: {e}")
            # Don't fail the main operation if refinement fails

