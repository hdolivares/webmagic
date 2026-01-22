"""
Geo-Strategy Model - Stores Claude-generated intelligent zone strategies.

Each strategy is tailored to a specific city + business category combination,
optimizing zone placement based on geographic, demographic, and industry factors.
"""
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from models.base import BaseModel


class GeoStrategy(BaseModel):
    """
    AI-generated geographic strategy for optimal business discovery.
    
    Stores Claude's analysis of city geography, business distribution patterns,
    and recommended search zones for maximum coverage efficiency.
    """
    __tablename__ = "geo_strategies"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(10), nullable=False, index=True)
    country = Column(String(10), nullable=False, default="US")
    category = Column(String(100), nullable=False, index=True)
    
    # Geographic metadata
    city_center_lat = Column(Float, nullable=False)
    city_center_lon = Column(Float, nullable=False)
    population = Column(Integer, nullable=True)
    
    # Claude's analysis
    geographic_analysis = Column(Text, nullable=True)
    """Claude's description of city shape, boundaries, natural features"""
    
    business_distribution_analysis = Column(Text, nullable=True)
    """Claude's analysis of where this business type clusters in this city"""
    
    strategy_reasoning = Column(Text, nullable=True)
    """Claude's explanation of the zone placement strategy"""
    
    # The actual strategy
    zones = Column(JSONB, nullable=False)
    """
    List of strategic zones:
    [
      {
        "zone_id": "downtown_core",
        "lat": 34.0522,
        "lon": -118.2437,
        "radius_km": 1.5,
        "priority": "high",
        "reason": "Dense commercial district with high lawyer concentration",
        "estimated_businesses": 150
      },
      ...
    ]
    """
    
    avoid_areas = Column(JSONB, nullable=True)
    """
    Areas to skip:
    [
      {"area": "Pacific Ocean", "reason": "water body"},
      {"area": "Santa Monica Mountains", "reason": "unpopulated wilderness"}
    ]
    """
    
    # Performance estimates
    total_zones = Column(Integer, nullable=False)
    estimated_total_businesses = Column(Integer, nullable=True)
    estimated_searches_needed = Column(Integer, nullable=True)
    coverage_area_km2 = Column(Float, nullable=True)
    
    # Execution tracking
    zones_completed = Column(Integer, nullable=False, default=0)
    businesses_found = Column(Integer, nullable=False, default=0)
    last_scrape_at = Column(DateTime, nullable=True)
    
    # Adaptive learning
    performance_data = Column(JSONB, nullable=True)
    """
    Track actual vs estimated performance:
    {
      "zone_results": [
        {"zone_id": "downtown_core", "expected": 150, "actual": 187, "variance": 24.7},
        ...
      ],
      "avg_variance": 12.3,
      "strategy_accuracy": 87.7
    }
    """
    
    adaptation_notes = Column(Text, nullable=True)
    """Claude's refinement suggestions based on actual results"""
    
    # Strategy metadata
    model_used = Column(String(50), nullable=False, default="claude-sonnet-4-5")
    strategy_version = Column(Integer, nullable=False, default=1)
    is_active = Column(String(20), nullable=False, default="active")  # active, completed, superseded
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_geo_strategy_location', 'city', 'state', 'country'),
        Index('idx_geo_strategy_category', 'category'),
        Index('idx_geo_strategy_active', 'is_active'),
        Index('idx_geo_strategy_lookup', 'city', 'state', 'category', 'is_active'),
    )
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "category": self.category,
            "city_center": {
                "lat": self.city_center_lat,
                "lon": self.city_center_lon
            },
            "population": self.population,
            "analysis": {
                "geographic": self.geographic_analysis,
                "business_distribution": self.business_distribution_analysis,
                "reasoning": self.strategy_reasoning
            },
            "zones": self.zones,
            "avoid_areas": self.avoid_areas,
            "metrics": {
                "total_zones": self.total_zones,
                "zones_completed": self.zones_completed,
                "estimated_businesses": self.estimated_total_businesses,
                "businesses_found": self.businesses_found,
                "coverage_area_km2": self.coverage_area_km2
            },
            "performance": self.performance_data,
            "status": self.is_active,
            "model_used": self.model_used,
            "version": self.strategy_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    def get_next_zone(self):
        """
        Get the next highest-priority unscraped zone.
        
        Returns:
            Zone dict or None if all complete
        """
        if not self.zones or self.zones_completed >= len(self.zones):
            return None
        
        # Zones are already sorted by priority (high → medium → low)
        # Find first zone that hasn't been scraped
        scraped_zone_ids = set()
        if self.performance_data and "zone_results" in self.performance_data:
            scraped_zone_ids = {z["zone_id"] for z in self.performance_data["zone_results"]}
        
        for zone in self.zones:
            if zone["zone_id"] not in scraped_zone_ids:
                return zone
        
        return None
    
    def mark_zone_complete(self, zone_id: str, businesses_found: int, estimated: int = None):
        """
        Mark a zone as completed and update performance tracking.
        
        Args:
            zone_id: Zone identifier
            businesses_found: Actual number of businesses discovered
            estimated: Expected number (from zone's estimated_businesses)
        """
        self.zones_completed += 1
        self.businesses_found += businesses_found
        
        # Initialize performance data if needed
        if not self.performance_data:
            self.performance_data = {"zone_results": []}
        elif "zone_results" not in self.performance_data:
            self.performance_data["zone_results"] = []
        
        # Calculate variance if we have an estimate
        variance = None
        if estimated and estimated > 0:
            variance = ((businesses_found - estimated) / estimated) * 100
        
        # Record result
        self.performance_data["zone_results"].append({
            "zone_id": zone_id,
            "expected": estimated,
            "actual": businesses_found,
            "variance_pct": round(variance, 1) if variance is not None else None,
            "completed_at": datetime.utcnow().isoformat()
        })
        
        # Calculate overall accuracy
        results_with_estimates = [
            r for r in self.performance_data["zone_results"] 
            if r.get("expected") and r.get("actual") is not None
        ]
        
        if results_with_estimates:
            total_expected = sum(r["expected"] for r in results_with_estimates)
            total_actual = sum(r["actual"] for r in results_with_estimates)
            
            if total_expected > 0:
                overall_accuracy = (min(total_actual, total_expected) / total_expected) * 100
                self.performance_data["strategy_accuracy"] = round(overall_accuracy, 1)
        
        self.last_scrape_at = datetime.utcnow()
        
        # Mark as completed if all zones done
        if self.zones_completed >= self.total_zones:
            self.is_active = "completed"
            self.completed_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()

