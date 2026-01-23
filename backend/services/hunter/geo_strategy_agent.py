"""
Geo-Strategy Agent - Uses Claude to generate intelligent zone placement strategies.

This agent analyzes city geography, business distribution patterns, and demographic data
to create optimized search zone strategies for maximum business discovery efficiency.
"""
from typing import Dict, Any, List, Optional
import json
import logging
from anthropic import AsyncAnthropic

from core.config import get_settings
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)
settings = get_settings()


class GeoStrategyAgent:
    """
    AI agent that generates intelligent geographic search strategies.
    
    Uses Claude to analyze:
    - City shape and boundaries (coastlines, mountains, rivers)
    - Population density distribution
    - Business category clustering patterns
    - Optimal zone placement for maximum coverage
    """
    
    def __init__(self, model: str = "claude-sonnet-4-5"):
        """
        Initialize the geo-strategy agent.
        
        Args:
            model: Claude model to use for strategy generation
        """
        self.model = model
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        logger.info(f"Initialized GeoStrategyAgent with model {model}")
    
    async def generate_strategy(
        self,
        city: str,
        state: str,
        country: str,
        category: str,
        center_lat: float,
        center_lon: float,
        population: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an intelligent zone placement strategy for a city + category.
        
        Args:
            city: City name (e.g., "Los Angeles")
            state: State code (e.g., "CA")
            country: Country code (e.g., "US")
            category: Business category (e.g., "plumbers", "lawyers")
            center_lat: City center latitude
            center_lon: City center longitude
            population: City population (if known)
            context: Additional context (previous scraping results, constraints)
        
        Returns:
            Strategy dictionary with zones, analysis, and estimates
        """
        logger.info(f"Generating strategy for {category} in {city}, {state}")
        
        # Build system and user prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            city, state, country, category,
            center_lat, center_lon, population, context
        )
        
        try:
            # Call Claude
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=65536,  # Max for Claude Sonnet 4.5
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Extract response
            response_text = message.content[0].text
            
            # Parse JSON response
            strategy = self._parse_strategy_response(response_text)
            
            # Add metadata
            strategy["model_used"] = self.model
            strategy["city"] = city
            strategy["state"] = state
            strategy["country"] = country
            strategy["category"] = category
            strategy["city_center_lat"] = center_lat
            strategy["city_center_lon"] = center_lon
            strategy["population"] = population
            
            logger.info(
                f"Generated strategy with {len(strategy.get('zones', []))} zones "
                f"covering ~{strategy.get('coverage_area_km2', 0):.1f} km²"
            )
            
            return strategy
            
        except Exception as e:
            logger.error(f"Strategy generation failed: {e}")
            raise ExternalAPIException(f"Failed to generate geo-strategy: {str(e)}")
    
    async def refine_strategy(
        self,
        original_strategy: Dict[str, Any],
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Refine an existing strategy based on actual scraping results.
        
        Uses Claude to analyze performance data and suggest improvements:
        - Add zones where high densities were discovered
        - Remove or expand zones with low yields
        - Adjust priority based on actual business distribution
        
        Args:
            original_strategy: The original Claude-generated strategy
            performance_data: Actual results from executed zones
        
        Returns:
            Refined strategy with adjusted zones and updated analysis
        """
        logger.info(
            f"Refining strategy for {original_strategy.get('city')} - "
            f"{original_strategy.get('category')}"
        )
        
        system_prompt = self._build_refinement_system_prompt()
        user_prompt = self._build_refinement_user_prompt(
            original_strategy, performance_data
        )
        
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=65536,  # Max for Claude Sonnet 4.5
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            response_text = message.content[0].text
            refinements = self._parse_refinement_response(response_text)
            
            logger.info(
                f"Strategy refinement suggests {len(refinements.get('new_zones', []))} "
                f"new zones and {len(refinements.get('adjust_zones', []))} adjustments"
            )
            
            return refinements
            
        except Exception as e:
            logger.error(f"Strategy refinement failed: {e}")
            raise ExternalAPIException(f"Failed to refine strategy: {str(e)}")
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for strategy generation."""
        return """You are a geographic strategy expert specializing in optimizing business discovery campaigns.

Your role is to analyze cities and generate intelligent zone placement strategies that maximize business discovery while minimizing redundant searches.

Key Considerations:
1. **City Geography**: Identify natural boundaries (oceans, mountains, rivers), uninhabited areas, and populated regions
2. **Business Distribution**: Different business types cluster differently:
   - Lawyers/Financial: Downtown business districts
   - Contractors/Plumbers: Uniform across residential areas
   - Restaurants: Entertainment districts, commercial corridors
   - Medical: Suburban residential areas, medical centers
   - Auto Services: Industrial corridors, highway access
3. **Population Density**: Dense urban cores need tighter spacing (1-2km radius), suburbs need wider (4-5km)
4. **Search Efficiency**: Google Maps shows ~50-100 businesses per search, biased toward the search coordinates
5. **Coverage Optimization**: Balance comprehensive coverage with cost efficiency

Your Strategy Should:
- Place zones to cover ALL populated areas
- AVOID unpopulated areas (water, mountains, parks, industrial zones for service businesses)
- Vary zone radius based on density (1.5km urban, 4-5km suburban)
- Prioritize high-value areas (downtown for lawyers, residential for plumbers)
- Estimate businesses per zone based on category + density
- Provide clear reasoning for each zone placement

Output Format:
Return a JSON object with:
{
  "geographic_analysis": "Description of city shape, boundaries, key features",
  "business_distribution_analysis": "Where this business type clusters in this city",
  "strategy_reasoning": "Why these zones were chosen",
  "zones": [
    {
      "zone_id": "unique_identifier",
      "lat": 34.0522,
      "lon": -118.2437,
      "radius_km": 1.5,
      "priority": "high|medium|low",
      "reason": "Why this zone is important",
      "estimated_businesses": 150,
      "area_description": "Downtown core, high density"
    }
  ],
  "avoid_areas": [
    {"area": "Area name", "reason": "Why to skip"}
  ],
  "total_zones": 18,
  "estimated_total_businesses": 2500,
  "estimated_searches_needed": 25,
  "coverage_area_km2": 850.5
}

Ensure zones:
- Cover the entire populated city area
- Don't overlap significantly (slight overlap is OK)
- Are sorted by priority (high first)
- Include 15-30 zones for major cities
- Have realistic business estimates"""
    
    def _build_user_prompt(
        self,
        city: str,
        state: str,
        country: str,
        category: str,
        center_lat: float,
        center_lon: float,
        population: Optional[int],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build user prompt with city and category details."""
        prompt = f"""Generate an optimal zone placement strategy for discovering businesses.

**Target City:**
- City: {city}, {state}, {country}
- Center Coordinates: {center_lat}, {center_lon}
- Population: {population:,} (approximate) if population else "Unknown"

**Business Category:** {category}

**Task:**
Analyze this city's geography and generate an intelligent zone placement strategy for finding {category} businesses.

Consider:
1. The actual shape and extent of {city} (not just a circle around the center)
2. Where {category} businesses typically locate in cities
3. Natural boundaries and unpopulated areas to avoid
4. Optimal zone spacing for this city's density
5. High-priority areas to search first

**Additional Context:**"""
        
        if context:
            if context.get("previous_results"):
                prompt += f"\n- Previous scraping found {context['previous_results']} businesses"
            if context.get("constraints"):
                prompt += f"\n- Constraints: {context['constraints']}"
        else:
            prompt += "\n- This is a new city with no previous scraping history"
        
        prompt += """

Generate a comprehensive strategy that will discover the maximum number of businesses with the minimum number of searches.

Return your strategy as a JSON object following the specified format."""
        
        return prompt
    
    def _build_refinement_system_prompt(self) -> str:
        """Build system prompt for strategy refinement."""
        return """You are refining a geographic search strategy based on actual performance data.

Your role is to analyze the results from executed search zones and suggest improvements:
- Identify areas of unexpected high/low business density
- Recommend new zones to fill coverage gaps
- Adjust existing zone priorities
- Suggest zone removals if areas are saturated

Be data-driven and specific in your recommendations.

Output Format:
{
  "analysis": "Summary of performance vs expectations",
  "key_findings": [
    "Finding 1: What the data reveals",
    "Finding 2: ...",
  ],
  "new_zones": [
    {
      "zone_id": "new_zone_1",
      "lat": 34.0522,
      "lon": -118.2437,
      "radius_km": 2.0,
      "priority": "high",
      "reason": "High density discovered in adjacent zone, likely spillover"
    }
  ],
  "adjust_zones": [
    {
      "zone_id": "existing_zone_id",
      "adjustments": {
        "priority": "low",
        "radius_km": 3.0,
        "reason": "Lower than expected density, expand search area"
      }
    }
  ],
  "remove_zones": ["zone_id1", "zone_id2"],
  "overall_strategy_assessment": "How well the strategy is performing"
}"""
    
    def _build_refinement_user_prompt(
        self,
        original_strategy: Dict[str, Any],
        performance_data: Dict[str, Any]
    ) -> str:
        """Build user prompt for strategy refinement."""
        city = original_strategy.get("city", "Unknown")
        category = original_strategy.get("category", "Unknown")
        
        prompt = f"""Refine the search strategy for {category} in {city} based on actual results.

**Original Strategy:**
- Total Zones: {original_strategy.get('total_zones', 0)}
- Estimated Businesses: {original_strategy.get('estimated_total_businesses', 0)}
- Zones Completed: {len(performance_data.get('zone_results', []))}

**Performance Data:**
"""
        
        zone_results = performance_data.get('zone_results', [])
        for result in zone_results:
            zone_id = result.get('zone_id')
            expected = result.get('expected', 'N/A')
            actual = result.get('actual', 0)
            variance = result.get('variance_pct', 'N/A')
            
            prompt += f"\n- Zone {zone_id}: Expected {expected}, Found {actual} (Variance: {variance}%)"
        
        prompt += f"""

**Overall Accuracy:** {performance_data.get('strategy_accuracy', 'N/A')}%

**Task:**
Analyze the performance data and recommend:
1. New zones to add (where might we be missing businesses?)
2. Adjustments to existing unscraped zones
3. Zones to potentially remove from the strategy

Be specific and data-driven in your recommendations."""
        
        return prompt
    
    def _parse_strategy_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's response into a strategy dictionary.
        
        Args:
            response_text: Raw response from Claude
        
        Returns:
            Parsed strategy dictionary
        """
        try:
            # Find JSON in response (might be wrapped in markdown)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[json_start:json_end]
            strategy = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["zones", "geographic_analysis", "strategy_reasoning"]
            for field in required_fields:
                if field not in strategy:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure zones have required fields
            for zone in strategy.get("zones", []):
                required_zone_fields = ["zone_id", "lat", "lon", "radius_km", "priority"]
                for field in required_zone_fields:
                    if field not in zone:
                        raise ValueError(f"Zone missing required field: {field}")
            
            # Calculate totals if not provided
            if "total_zones" not in strategy:
                strategy["total_zones"] = len(strategy["zones"])
            
            if "estimated_total_businesses" not in strategy:
                strategy["estimated_total_businesses"] = sum(
                    z.get("estimated_businesses", 0) for z in strategy["zones"]
                )
            
            return strategy
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")
            raise ValueError(f"Invalid JSON in strategy response: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to parse strategy response: {e}")
            raise
    
    def _parse_refinement_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's refinement response.
        
        Args:
            response_text: Raw response from Claude
        
        Returns:
            Parsed refinement dictionary
        """
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in refinement response")
            
            json_str = response_text[json_start:json_end]
            refinements = json.loads(json_str)
            
            # Set defaults for optional fields
            refinements.setdefault("new_zones", [])
            refinements.setdefault("adjust_zones", [])
            refinements.setdefault("remove_zones", [])
            
            return refinements
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse refinement JSON: {e}")
            raise ValueError(f"Invalid JSON in refinement response: {str(e)}")

