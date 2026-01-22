"""
Geographic Grid System for Maximum Business Coverage.

Subdivides cities into smaller geographic zones to ensure comprehensive
business discovery, as Google Maps results are location-biased.

Strategy:
- Cities 100K-250K: 2x2 grid (4 zones)
- Cities 250K-500K: 3x3 grid (9 zones)
- Cities 500K-1M: 4x4 grid (16 zones)
- Cities 1M+: 5x5 grid (25 zones)
"""
import math
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Earth's radius in kilometers
EARTH_RADIUS_KM = 6371.0


class GeoGrid:
    """
    Represents a geographic grid zone for systematic business searches.
    """
    
    def __init__(
        self,
        zone_id: str,
        center_lat: float,
        center_lon: float,
        city: str,
        state: str,
        radius_km: float = 3.0
    ):
        self.zone_id = zone_id
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.city = city
        self.state = state
        self.radius_km = radius_km
    
    @property
    def search_query_suffix(self) -> str:
        """Generate search query suffix for this zone."""
        return f"near {self.center_lat},{self.center_lon}"
    
    @property
    def zone_name(self) -> str:
        """Human-readable zone name."""
        return f"{self.city}, {self.state} - Zone {self.zone_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "zone_id": self.zone_id,
            "center_lat": self.center_lat,
            "center_lon": self.center_lon,
            "city": self.city,
            "state": self.state,
            "radius_km": self.radius_km
        }


def calculate_grid_size(population: int) -> Tuple[int, int]:
    """
    Calculate optimal grid size based on city population.
    
    Returns:
        Tuple of (rows, cols) for grid subdivision
    """
    if population >= 1_000_000:
        return (5, 5)  # 25 zones for mega-cities
    elif population >= 500_000:
        return (4, 4)  # 16 zones for large cities
    elif population >= 250_000:
        return (3, 3)  # 9 zones for medium cities
    elif population >= 100_000:
        return (2, 2)  # 4 zones for smaller cities
    else:
        return (2, 2)  # 4 zones minimum


def calculate_search_radius(population: int) -> float:
    """
    Calculate search radius in kilometers based on city size.
    
    Returns:
        Radius in kilometers
    """
    if population >= 1_000_000:
        return 4.0  # 4km radius for mega-cities
    elif population >= 500_000:
        return 3.5  # 3.5km radius
    elif population >= 250_000:
        return 3.0  # 3km radius
    else:
        return 2.5  # 2.5km radius for smaller cities


def estimate_city_bounds(
    center_lat: float,
    center_lon: float,
    population: int
) -> Tuple[float, float]:
    """
    Estimate city bounds (width and height in degrees) based on population.
    
    This is a rough estimation. For production, use actual city boundary data.
    
    Returns:
        Tuple of (lat_span, lon_span) in degrees
    """
    # Estimate area in square kilometers (rough approximation)
    # Average city density: ~2000 people per sq km
    estimated_area_km2 = population / 2000
    
    # Calculate radius of circular approximation
    radius_km = math.sqrt(estimated_area_km2 / math.pi)
    
    # Convert to degrees (rough approximation)
    # 1 degree latitude ≈ 111 km
    # 1 degree longitude varies by latitude
    lat_span = (radius_km * 2) / 111.0
    
    # Longitude degree width at given latitude
    lon_degree_km = 111.0 * math.cos(math.radians(center_lat))
    lon_span = (radius_km * 2) / lon_degree_km if lon_degree_km > 0 else lat_span
    
    # Add 20% buffer to ensure coverage
    lat_span *= 1.2
    lon_span *= 1.2
    
    return (lat_span, lon_span)


def create_city_grid(
    city: str,
    state: str,
    center_lat: float,
    center_lon: float,
    population: int
) -> List[GeoGrid]:
    """
    Create a grid of geographic zones for comprehensive city coverage.
    
    Args:
        city: City name
        state: State code
        center_lat: City center latitude
        center_lon: City center longitude
        population: City population
    
    Returns:
        List of GeoGrid zones covering the city
    """
    # Calculate grid dimensions
    rows, cols = calculate_grid_size(population)
    search_radius = calculate_search_radius(population)
    
    # Estimate city bounds
    lat_span, lon_span = estimate_city_bounds(center_lat, center_lon, population)
    
    # Calculate grid cell size
    cell_lat_size = lat_span / rows
    cell_lon_size = lon_span / cols
    
    # Calculate starting point (top-left corner)
    start_lat = center_lat + (lat_span / 2) - (cell_lat_size / 2)
    start_lon = center_lon - (lon_span / 2) + (cell_lon_size / 2)
    
    # Generate grid zones
    zones = []
    zone_index = 1
    
    for row in range(rows):
        for col in range(cols):
            # Calculate zone center
            zone_lat = start_lat - (row * cell_lat_size)
            zone_lon = start_lon + (col * cell_lon_size)
            
            # Create zone identifier (e.g., "2x3" means row 2, column 3)
            zone_id = f"{row+1}x{col+1}"
            
            zone = GeoGrid(
                zone_id=zone_id,
                center_lat=round(zone_lat, 6),
                center_lon=round(zone_lon, 6),
                city=city,
                state=state,
                radius_km=search_radius
            )
            
            zones.append(zone)
            zone_index += 1
    
    logger.info(
        f"Created {len(zones)} zones for {city}, {state} "
        f"(population: {population:,}, grid: {rows}x{cols})"
    )
    
    return zones


def get_zone_search_query(
    industry: str,
    zone: GeoGrid,
    country: str = "US"
) -> str:
    """
    Generate optimized search query for a specific zone.
    
    Args:
        industry: Business category (e.g., "plumbers")
        zone: Geographic zone
        country: Country code
    
    Returns:
        Search query string for Outscraper
    """
    # Format: "plumbers near 34.0522,-118.2437"
    # This tells Google Maps to search near this specific coordinate
    return f"{industry} near {zone.center_lat},{zone.center_lon}"


def should_subdivide_city(population: int) -> bool:
    """
    Determine if a city should be subdivided into zones.
    
    Args:
        population: City population
    
    Returns:
        True if city should be subdivided, False otherwise
    """
    # Subdivide all cities with 100K+ population
    return population >= 100_000


def get_grid_summary(zones: List[GeoGrid]) -> Dict[str, Any]:
    """
    Generate summary statistics for a grid.
    
    Args:
        zones: List of GeoGrid zones
    
    Returns:
        Dictionary with grid statistics
    """
    if not zones:
        return {
            "total_zones": 0,
            "grid_size": "N/A",
            "coverage_area": "N/A"
        }
    
    # Determine grid dimensions
    zone_ids = [z.zone_id for z in zones]
    rows = max(int(zid.split('x')[0]) for zid in zone_ids)
    cols = max(int(zid.split('x')[1]) for zid in zone_ids)
    
    # Calculate total coverage area (approximate)
    # Each zone covers roughly π * radius²
    zone_area_km2 = math.pi * (zones[0].radius_km ** 2)
    total_area_km2 = zone_area_km2 * len(zones)
    
    return {
        "total_zones": len(zones),
        "grid_size": f"{rows}x{cols}",
        "zone_radius_km": zones[0].radius_km,
        "approx_coverage_km2": round(total_area_km2, 1),
        "city": zones[0].city,
        "state": zones[0].state
    }


# Example usage and testing
if __name__ == "__main__":
    # Test with different city sizes
    
    # Small city (100K)
    zones_small = create_city_grid(
        city="Burbank",
        state="CA",
        center_lat=34.1808,
        center_lon=-118.3090,
        population=107_000
    )
    print(f"\nSmall City: {get_grid_summary(zones_small)}")
    
    # Medium city (500K)
    zones_medium = create_city_grid(
        city="Tucson",
        state="AZ",
        center_lat=32.2226,
        center_lon=-110.9747,
        population=548_000
    )
    print(f"\nMedium City: {get_grid_summary(zones_medium)}")
    
    # Large city (1M+)
    zones_large = create_city_grid(
        city="Los Angeles",
        state="CA",
        center_lat=34.0522,
        center_lon=-118.2437,
        population=3_900_000
    )
    print(f"\nLarge City: {get_grid_summary(zones_large)}")
    
    # Show sample zone search queries
    print("\nSample Search Queries:")
    for i, zone in enumerate(zones_large[:3], 1):
        query = get_zone_search_query("plumbers", zone)
        print(f"  Zone {zone.zone_id}: {query}")

