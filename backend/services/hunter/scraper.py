"""
Outscraper API client for Google My Business scraping.
"""
import asyncio
from typing import List, Dict, Any, Optional
from outscraper import ApiClient
from core.config import get_settings
from core.exceptions import ExternalAPIException
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class OutscraperClient:
    """
    Wrapper for Outscraper API with error handling and rate limiting.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Outscraper client.
        
        Args:
            api_key: Outscraper API key (defaults to settings)
        """
        self.api_key = api_key or settings.OUTSCRAPER_API_KEY
        self.client = ApiClient(api_key=self.api_key)
        self.rate_limit_delay = 1.0  # seconds between requests
        self._active_searches = set()  # Track in-progress searches to prevent duplicates
        
    async def search_businesses(
        self,
        query: str,
        city: str,
        state: str,
        country: str = "US",
        limit: int = 50,
        language: str = "en",
        zone_lat: Optional[float] = None,
        zone_lon: Optional[float] = None,
        zone_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for businesses on Google Maps.
        
        Args:
            query: Search query (e.g., "Plumbers", "Pizza Restaurant")
            city: City name
            state: State code (e.g., "TX", "CA")
            country: Country code (default: "US")
            limit: Maximum number of results
            language: Language code (default: "en")
            zone_lat: Optional zone center latitude for geo-specific search
            zone_lon: Optional zone center longitude for geo-specific search
            zone_id: Optional zone identifier for logging
            
        Returns:
            Dictionary with:
                - businesses: List of business dictionaries
                - total_found: Number of businesses found
                - has_more: Whether more results may be available
                - search_query: Query that was executed
            
        Raises:
            ExternalAPIException: If the API request fails
        """
        try:
            # Build search query
            # If zone coordinates provided, use geo-specific search
            if zone_lat is not None and zone_lon is not None:
                search_query = f"{query} near {zone_lat},{zone_lon}"
                zone_str = f" [Zone {zone_id}]" if zone_id else ""
                logger.info(f"Geo-search: {search_query}{zone_str} (limit: {limit})")
            else:
                # Traditional city-based search
                location = f"{city}, {state}, {country}"
                search_query = f"{query} in {location}"
                logger.info(f"City-search: {search_query} (limit: {limit})")
            
            # ANTI-DUPLICATE: Check if this exact search is already running
            search_key = f"{query}|{city}|{state}|{zone_lat}|{zone_lon}|{limit}"
            if search_key in self._active_searches:
                logger.warning(f"⚠️  DUPLICATE CALL BLOCKED: {search_query}")
                logger.warning("This search is already in progress - preventing duplicate Outscraper charge!")
                raise ExternalAPIException(
                    "Duplicate search detected - this exact query is already running. "
                    "Please wait for the first search to complete."
                )
            
            # Mark search as active
            self._active_searches.add(search_key)
            logger.info(f"🔒 Search locked: {search_key}")
            
            # Run synchronous API call in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._search_sync,
                search_query,
                limit,
                language
            )
            
            # Normalize results
            normalized = self._normalize_results(results)
            
            # Determine if more results likely available
            # If we got exactly the limit, there may be more
            has_more = len(normalized) >= limit
            
            logger.info(
                f"Found {len(normalized)} businesses "
                f"(has_more: {has_more})"
            )
            
            result = {
                "businesses": normalized,
                "total_found": len(normalized),
                "has_more": has_more,
                "search_query": search_query,
                "zone_id": zone_id
            }
            
            # Release lock
            self._active_searches.discard(search_key)
            logger.info(f"🔓 Search unlocked: {search_key}")
            
            return result
            
        except Exception as e:
            # Release lock on error
            if 'search_key' in locals():
                self._active_searches.discard(search_key)
                logger.info(f"🔓 Search unlocked (error): {search_key}")
            
            logger.error(f"Outscraper API error: {str(e)}")
            raise ExternalAPIException(f"Failed to scrape businesses: {str(e)}")
    
    def _search_sync(
        self,
        query: str,
        limit: int,
        language: str
    ) -> List[Dict[str, Any]]:
        """
        Synchronous search call to Outscraper.
        This runs in a thread pool to avoid blocking.
        """
        try:
            results = self.client.google_maps_search(
                query=[query],
                limit=limit,
                language=language,
                region=None,
                drop_duplicates=True
            )
            
            # DEBUG: Log what Outscraper returns
            logger.info(f"Outscraper returned type: {type(results)}, length: {len(results) if results else 0}")
            
            # Check if Outscraper returned an error code (usually 0 when out of credits)
            if isinstance(results, int):
                if results == 0:
                    raise ValueError("Outscraper returned 0 - likely out of API credits or invalid API key")
                else:
                    raise ValueError(f"Outscraper returned error code: {results}")
            
            if results and len(results) > 0:
                logger.info(f"First element type: {type(results[0])}, length: {len(results[0]) if isinstance(results[0], (list, dict)) else 'N/A'}")
                logger.info(f"Total results from Outscraper: {len(results)}")
                
                # Outscraper returns a flat list of dicts (not a list of lists)
                return results  # Return the whole list
            
            logger.warning("Outscraper returned empty results")
            return []
            
        except Exception as e:
            logger.error(f"Error in Outscraper API call: {type(e).__name__}: {str(e)}")
            raise
    
    def _normalize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize Outscraper results to our standard format.
        
        Outscraper fields → Our fields:
        - name → name
        - full_address → address
        - city → city
        - state → state
        - postal_code → zip_code
        - country_code → country
        - latitude → latitude
        - longitude → longitude
        - phone → phone
        - site → website_url
        - type → category
        - rating → rating
        - reviews → review_count
        - reviews_data → reviews_data (for AI analysis)
        - place_id → gmb_place_id
        - google_id → gmb_id
        - photos_data_id → photos_urls
        """
        # DEBUG: Log what we're actually getting
        logger.info(f"Normalizing {len(results)} results. Type: {type(results)}")
        if results and len(results) > 0:
            logger.info(f"First result type: {type(results[0])}, Sample: {str(results[0])[:200]}")
            # DEBUG: Check if 'site' field exists in first result
            first_result = results[0]
            if isinstance(first_result, dict):
                logger.info(f"First result keys: {list(first_result.keys())}")
                logger.info(f"First result 'site' field: {first_result.get('site', 'KEY NOT FOUND')}")
        
        normalized = []
        
        for business in results:
            try:
                # Type check - skip if not a dict
                if not isinstance(business, dict):
                    logger.warning(f"Skipping non-dict business: {type(business)} = {str(business)[:100]}")
                    continue
                
                # Extract review data for AI analysis
                reviews_data = business.get("reviews_data", [])
                review_texts = [
                    {
                        "text": review.get("review_text", ""),
                        "rating": review.get("review_rating"),
                        "date": review.get("review_datetime_utc")
                    }
                    for review in reviews_data[:10]  # Top 10 reviews
                    if review.get("review_text")
                ]
                
                # Extract photo URLs
                photos = business.get("photos_data_id", [])
                photo_urls = [photo for photo in photos[:10] if photo]  # Top 10 photos
                
                # DEBUG: Log website field for each business
                site_value = business.get("site")
                if site_value:
                    logger.info(f"Business '{business.get('name')}' has site: {site_value}")
                
                normalized_business = {
                    # Identity
                    "gmb_id": business.get("google_id"),
                    "gmb_place_id": business.get("place_id"),
                    "name": business.get("name", "").strip(),
                    
                    # Contact
                    "phone": business.get("phone"),
                    "website_url": business.get("site"),
                    "email": None,  # Not provided by Outscraper
                    
                    # Location
                    "address": business.get("full_address"),
                    "city": business.get("city"),
                    "state": business.get("state"),
                    "zip_code": business.get("postal_code"),
                    "country": business.get("country_code", "US"),
                    "latitude": business.get("latitude"),
                    "longitude": business.get("longitude"),
                    
                    # Business Info
                    "category": business.get("type"),
                    "subcategory": business.get("subtypes", [None])[0] if business.get("subtypes") else None,
                    "rating": business.get("rating"),
                    "review_count": business.get("reviews", 0),
                    
                    # Media
                    "photos_urls": photo_urls,
                    "logo_url": photos[0] if photos else None,
                    
                    # Raw data for AI processing
                    "reviews_data": review_texts,
                    
                    # Metadata
                    "raw_data": business  # Store original for debugging
                }
                
                # Only add if has name (required field)
                if normalized_business["name"]:
                    normalized.append(normalized_business)
                    
            except Exception as e:
                logger.warning(f"Failed to normalize business: {str(e)}")
                continue
        
        return normalized
    
    async def get_business_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed business information by Google Place ID.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Business dictionary or None if not found
        """
        try:
            logger.info(f"Fetching business by place_id: {place_id}")
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self._get_by_place_id_sync,
                place_id
            )
            
            if results:
                normalized = self._normalize_results(results)
                return normalized[0] if normalized else None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch business: {str(e)}")
            return None
    
    def _get_by_place_id_sync(self, place_id: str) -> List[Dict[str, Any]]:
        """Synchronous place_id lookup."""
        results = self.client.google_maps_search(
            query=[f"place_id:{place_id}"],
            limit=1
        )
        
        if results and len(results) > 0:
            return results[0]
        return []
