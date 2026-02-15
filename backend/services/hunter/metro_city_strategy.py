"""
Metro Area City-Based Strategy Generator.

Since Outscraper ignores coordinate-based searches, we use a city-based approach
where each "zone" represents a city within a metro area.
"""
from typing import Dict, List, Any


# Metro area definitions with their constituent cities
METRO_AREAS = {
    "Los Angeles": {
        "state": "CA",
        "cities": [
            # Core LA
            {"city": "Los Angeles", "priority": "high", "population": 3900000},
            
            # San Fernando Valley
            {"city": "Van Nuys", "priority": "high", "population": 136000},
            {"city": "North Hollywood", "priority": "high", "population": 87000},
            {"city": "Sherman Oaks", "priority": "high", "population": 52000},
            {"city": "Encino", "priority": "medium", "population": 44000},
            {"city": "Reseda", "priority": "medium", "population": 79000},
            {"city": "Canoga Park", "priority": "medium", "population": 58000},
            {"city": "Woodland Hills", "priority": "medium", "population": 60000},
            
            # Westside
            {"city": "Santa Monica", "priority": "high", "population": 93000},
            {"city": "Venice", "priority": "high", "population": 41000},
            {"city": "Culver City", "priority": "high", "population": 39000},
            {"city": "West Hollywood", "priority": "medium", "population": 35000},
            {"city": "Beverly Hills", "priority": "medium", "population": 34000},
            
            # South Bay
            {"city": "Long Beach", "priority": "high", "population": 467000},
            {"city": "Torrance", "priority": "high", "population": 147000},
            {"city": "Carson", "priority": "high", "population": 92000},
            {"city": "Redondo Beach", "priority": "medium", "population": 67000},
            {"city": "Manhattan Beach", "priority": "medium", "population": 35000},
            {"city": "Hermosa Beach", "priority": "low", "population": 20000},
            
            # San Gabriel Valley
            {"city": "Pasadena", "priority": "high", "population": 142000},
            {"city": "Glendale", "priority": "high", "population": 197000},
            {"city": "Burbank", "priority": "high", "population": 104000},
            {"city": "Alhambra", "priority": "medium", "population": 84000},
            {"city": "El Monte", "priority": "medium", "population": 115000},
            {"city": "Arcadia", "priority": "medium", "population": 57000},
            
            # Southeast LA
            {"city": "Downey", "priority": "high", "population": 113000},
            {"city": "Norwalk", "priority": "medium", "population": 106000},
            {"city": "Whittier", "priority": "medium", "population": 86000},
            {"city": "Pico Rivera", "priority": "medium", "population": 63000},
            
            # Gateway Cities
            {"city": "Inglewood", "priority": "high", "population": 110000},
            {"city": "Hawthorne", "priority": "medium", "population": 87000},
            {"city": "Gardena", "priority": "medium", "population": 60000},
            {"city": "Compton", "priority": "medium", "population": 97000},
        ]
    },
    
    "New York": {
        "state": "NY",
        "cities": [
            {"city": "New York", "priority": "high", "population": 8400000},
            {"city": "Brooklyn", "priority": "high", "population": 2600000},
            {"city": "Queens", "priority": "high", "population": 2300000},
            {"city": "Manhattan", "priority": "high", "population": 1600000},
            {"city": "Bronx", "priority": "high", "population": 1400000},
            {"city": "Staten Island", "priority": "medium", "population": 480000},
            {"city": "Yonkers", "priority": "medium", "population": 200000},
            {"city": "New Rochelle", "priority": "low", "population": 79000},
        ]
    },
    
    "Chicago": {
        "state": "IL",
        "cities": [
            {"city": "Chicago", "priority": "high", "population": 2700000},
            {"city": "Aurora", "priority": "high", "population": 200000},
            {"city": "Naperville", "priority": "high", "population": 148000},
            {"city": "Joliet", "priority": "medium", "population": 148000},
            {"city": "Evanston", "priority": "medium", "population": 75000},
            {"city": "Cicero", "priority": "medium", "population": 81000},
        ]
    },
    
    "Houston": {
        "state": "TX",
        "cities": [
            {"city": "Houston", "priority": "high", "population": 2300000},
            {"city": "Pasadena", "priority": "high", "population": 152000},
            {"city": "Pearland", "priority": "high", "population": 122000},
            {"city": "Sugar Land", "priority": "medium", "population": 118000},
            {"city": "The Woodlands", "priority": "medium", "population": 114000},
            {"city": "League City", "priority": "medium", "population": 106000},
        ]
    },
    
    "Phoenix": {
        "state": "AZ",
        "cities": [
            {"city": "Phoenix", "priority": "high", "population": 1600000},
            {"city": "Mesa", "priority": "high", "population": 508000},
            {"city": "Chandler", "priority": "high", "population": 275000},
            {"city": "Scottsdale", "priority": "high", "population": 258000},
            {"city": "Glendale", "priority": "high", "population": 252000},
            {"city": "Tempe", "priority": "medium", "population": 195000},
        ]
    },
}


def generate_city_based_strategy(
    metro_area: str,
    state: str,
    category: str,
    center_lat: float,
    center_lon: float
) -> Dict[str, Any]:
    """
    Generate a city-based scraping strategy for a metro area.
    
    Args:
        metro_area: Metro area name (e.g., "Los Angeles")
        state: State code (e.g., "CA")
        category: Business category (e.g., "plumbers")
        center_lat: Metro center latitude (for reference)
        center_lon: Metro center longitude (for reference)
    
    Returns:
        Strategy dictionary with zones (cities)
    """
    # Get metro area definition
    metro_def = METRO_AREAS.get(metro_area)
    
    if not metro_def:
        # Fallback: single city strategy
        # Generate short zone_id (max 20 chars) - INCLUDE CATEGORY for uniqueness
        city_abbr = metro_area.lower().replace(' ', '')[:8]
        category_abbr = category.lower().replace(' ', '')[:8]
        zone_id = f"{city_abbr}_{category_abbr}"[:20]
        
        return {
            "geographic_analysis": f"Single city strategy for {metro_area}, {state}",
            "business_distribution_analysis": f"{category} are distributed throughout {metro_area}",
            "strategy_reasoning": "Using city-based search since coordinate-based search is unreliable",
            "zones": [
                {
                    "zone_id": zone_id,
                    "city": metro_area,
                    "target_city": metro_area,
                    "lat": center_lat,
                    "lon": center_lon,
                    "radius_km": 10.0,
                    "priority": "high",
                    "reason": f"Main city search for {metro_area}",
                    "estimated_businesses": 200,
                    "area_description": f"{metro_area} city limits"
                }
            ],
            "total_zones": 1,
            "estimated_total_businesses": 200,
            "estimated_searches_needed": 4,
            "coverage_area_km2": 314.0
        }
    
    # Build zones from cities
    zones = []
    total_estimated = 0
    
    for idx, city_def in enumerate(metro_def["cities"]):
        city_name = city_def["city"]
        priority = city_def["priority"]
        population = city_def.get("population", 50000)
        
        # Estimate businesses based on population and category
        # Rough estimate: 1 plumber per 1000 people, 1 restaurant per 500 people, etc.
        category_multipliers = {
            "plumber": 1.0,
            "restaurant": 2.0,
            "lawyer": 0.5,
            "dentist": 0.8,
            "contractor": 1.2,
        }
        multiplier = category_multipliers.get(category.lower().rstrip('s'), 1.0)
        estimated = int((population / 1000) * multiplier)
        total_estimated += estimated
        
        # Generate short zone_id (max 20 chars for DB constraint)
        # Format: metro_abbreviation + city_abbreviation + category (e.g., "la_losang_pet")
        # INCLUDE CATEGORY to prevent collisions when scraping different categories in same city
        metro_abbr = ''.join([w[0] for w in metro_area.split()]).lower()  # "LA" -> "la"
        city_abbr = city_name.lower().replace(' ', '')[:8]  # Remove spaces, max 8 chars
        category_abbr = category.lower().replace(' ', '')[:6]  # Max 6 chars for category
        zone_id = f"{metro_abbr}_{city_abbr}_{category_abbr}"[:20]  # Ensure max 20 chars
        
        zone = {
            "zone_id": zone_id,
            "city": city_name,
            "target_city": city_name,
            "lat": center_lat,  # Placeholder (not used)
            "lon": center_lon,  # Placeholder (not used)
            "radius_km": 5.0,   # Placeholder (not used)
            "priority": priority,
            "reason": f"{city_name} - population {population:,}",
            "estimated_businesses": estimated,
            "area_description": f"{city_name}, {state}"
        }
        zones.append(zone)
    
    return {
        "geographic_analysis": f"{metro_area} metro area with {len(zones)} cities",
        "business_distribution_analysis": f"{category} distributed across metro area cities",
        "strategy_reasoning": (
            "City-based strategy to work around Outscraper's broken coordinate search. "
            f"Targeting {len(zones)} cities in {metro_area} metro area for comprehensive coverage."
        ),
        "zones": zones,
        "total_zones": len(zones),
        "estimated_total_businesses": total_estimated,
        "estimated_searches_needed": len(zones) * 2,  # ~2 searches per city
        "coverage_area_km2": len(zones) * 78.5  # Rough estimate
    }

