"""
Geocoding Service

Converts city names to geographic coordinates and retrieves population data.
Uses Nominatim (OpenStreetMap) as a free, open-source geocoding service.
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CityData:
    """City geographic and demographic data"""
    city: str
    state: str
    country: str
    latitude: float
    longitude: float
    population: Optional[int] = None
    display_name: str = ""
    bounding_box: Optional[Dict[str, float]] = None
    
    def get_radius_km(self) -> float:
        """Calculate approximate radius based on population"""
        if not self.population:
            return 10.0  # Default 10km radius
        
        # Rough estimate: larger cities need larger radius
        if self.population > 5_000_000:
            return 25.0
        elif self.population > 1_000_000:
            return 20.0
        elif self.population > 500_000:
            return 15.0
        elif self.population > 100_000:
            return 10.0
        else:
            return 8.0


class GeocodingService:
    """Service for geocoding cities and retrieving geographic data"""
    
    def __init__(self):
        self.nominatim_base_url = "https://nominatim.openstreetmap.org"
        # User agent required by Nominatim
        self.headers = {
            "User-Agent": "WebMagic/1.0 (Business Discovery Platform)"
        }
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session
    
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def geocode_city(
        self,
        city: str,
        state: str,
        country: str = "United States"
    ) -> Optional[CityData]:
        """
        Geocode a city to get coordinates and population data.
        
        Args:
            city: City name (e.g., "Los Angeles")
            state: State code or name (e.g., "CA" or "California")
            country: Country name (default: "United States")
        
        Returns:
            CityData object with coordinates and population, or None if not found
        """
        try:
            session = await self._get_session()
            
            # Build search query
            query = f"{city}, {state}, {country}"
            
            # Nominatim search endpoint
            url = f"{self.nominatim_base_url}/search"
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
                "extratags": 1  # Get additional tags including population
            }
            
            logger.info(f"Geocoding city: {query}")
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Geocoding failed with status {response.status}")
                    return None
                
                results = await response.json()
                
                if not results:
                    logger.warning(f"No geocoding results for: {query}")
                    return None
                
                result = results[0]
                
                # Extract data
                lat = float(result.get("lat", 0))
                lon = float(result.get("lon", 0))
                display_name = result.get("display_name", "")
                
                # Extract population from extratags or use estimate
                population = None
                if "extratags" in result and "population" in result["extratags"]:
                    try:
                        population = int(result["extratags"]["population"])
                    except (ValueError, TypeError):
                        pass
                
                # If no population, try to estimate based on place type
                if not population:
                    population = self._estimate_population(result)
                
                # Extract bounding box
                bounding_box = None
                if "boundingbox" in result:
                    bbox = result["boundingbox"]
                    bounding_box = {
                        "south": float(bbox[0]),
                        "north": float(bbox[1]),
                        "west": float(bbox[2]),
                        "east": float(bbox[3])
                    }
                
                city_data = CityData(
                    city=city,
                    state=state,
                    country=country,
                    latitude=lat,
                    longitude=lon,
                    population=population,
                    display_name=display_name,
                    bounding_box=bounding_box
                )
                
                logger.info(
                    f"Geocoded {city}, {state}: "
                    f"lat={lat:.4f}, lon={lon:.4f}, pop={population}"
                )
                
                return city_data
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during geocoding: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error geocoding city: {str(e)}", exc_info=True)
            return None
    
    def _estimate_population(self, geocoding_result: Dict[str, Any]) -> int:
        """
        Estimate population based on place type when exact data unavailable.
        
        This is a rough heuristic based on typical US city classifications.
        """
        place_type = geocoding_result.get("type", "").lower()
        place_class = geocoding_result.get("class", "").lower()
        
        # Heuristic estimates
        if place_type == "city":
            return 100_000  # Average medium city
        elif place_type == "town":
            return 25_000
        elif place_type == "village":
            return 5_000
        elif place_type == "hamlet":
            return 1_000
        elif place_class == "place" and place_type == "suburb":
            return 50_000
        
        # Default estimate for unknown
        return 50_000
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, str]]:
        """
        Reverse geocode coordinates to get address information.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
        
        Returns:
            Dictionary with address components, or None if not found
        """
        try:
            session = await self._get_session()
            
            url = f"{self.nominatim_base_url}/reverse"
            params = {
                "lat": latitude,
                "lon": longitude,
                "format": "json",
                "addressdetails": 1
            }
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                
                result = await response.json()
                
                if "address" in result:
                    return result["address"]
                
                return None
                
        except Exception as e:
            logger.error(f"Error reverse geocoding: {str(e)}")
            return None
    
    async def get_city_boundaries(
        self,
        city: str,
        state: str,
        country: str = "United States"
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed boundary information for a city.
        
        Returns bounding box and polygon data if available.
        """
        city_data = await self.geocode_city(city, state, country)
        
        if not city_data or not city_data.bounding_box:
            return None
        
        return {
            "center": {
                "lat": city_data.latitude,
                "lon": city_data.longitude
            },
            "bounding_box": city_data.bounding_box,
            "estimated_radius_km": city_data.get_radius_km()
        }


# Singleton instance
_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    """Get the global geocoding service instance"""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service


async def geocode_city(city: str, state: str, country: str = "United States") -> Optional[CityData]:
    """
    Convenience function to geocode a city.
    
    Usage:
        city_data = await geocode_city("Los Angeles", "CA")
        if city_data:
            print(f"Coordinates: {city_data.latitude}, {city_data.longitude}")
            print(f"Population: {city_data.population}")
    """
    service = get_geocoding_service()
    return await service.geocode_city(city, state, country)


# Example usage and testing
if __name__ == "__main__":
    async def test_geocoding():
        """Test the geocoding service"""
        service = GeocodingService()
        
        # Test cities
        test_cities = [
            ("Los Angeles", "CA"),
            ("New York", "NY"),
            ("Chicago", "IL"),
            ("Houston", "TX"),
            ("Phoenix", "AZ"),
        ]
        
        print("Testing Geocoding Service\n" + "="*50)
        
        for city, state in test_cities:
            data = await service.geocode_city(city, state)
            
            if data:
                print(f"\n{city}, {state}:")
                print(f"  Coordinates: {data.latitude:.4f}, {data.longitude:.4f}")
                print(f"  Population: {data.population:,}" if data.population else "  Population: Unknown")
                print(f"  Recommended radius: {data.get_radius_km()} km")
                print(f"  Display: {data.display_name}")
            else:
                print(f"\n{city}, {state}: FAILED")
        
        await service.close()
    
    # Run test
    asyncio.run(test_geocoding())

