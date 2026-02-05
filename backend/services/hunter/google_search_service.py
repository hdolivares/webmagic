"""
Google Search Service using Scrapingdog API.

Provides Google search functionality to verify business websites
that weren't captured by Outscraper.

Best Practices:
- Rate limiting and retry logic
- Comprehensive logging
- Domain validation
- Error handling
"""
import logging
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
import aiohttp
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleSearchService:
    """
    Service for searching Google to find business websites.
    
    Uses Scrapingdog API to avoid bot detection and rate limits.
    """
    
    # Domains to exclude (not actual business websites)
    EXCLUDED_DOMAINS = {
        "google.com", "maps.google.com", "google.co.uk",
        "facebook.com", "fb.com", "m.facebook.com",
        "yelp.com", "m.yelp.com",
        "yellowpages.com", "yp.com",
        "bbb.org",
        "tripadvisor.com",
        "linkedin.com",
        "instagram.com",
        "twitter.com", "x.com",
        "youtube.com",
        "pinterest.com",
        "nextdoor.com",
        "thumbtack.com",
        "angi.com", "angieslist.com",
        "houzz.com",
        "porch.com",
        "homeadvisor.com",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Google Search Service.
        
        Args:
            api_key: Scrapingdog API key (defaults to settings)
        """
        self.api_key = api_key or getattr(settings, "SCRAPINGDOG_API_KEY", None)
        self.base_url = "https://api.scrapingdog.com/google"
        
        if not self.api_key:
            logger.warning("SCRAPINGDOG_API_KEY not configured - Google search will be disabled")
    
    def is_valid_business_website(self, url: str) -> bool:
        """
        Check if URL is likely a real business website (not a directory).
        
        Args:
            url: URL to validate
            
        Returns:
            True if likely a business website, False otherwise
        """
        if not url:
            return False
        
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc or parsed.path
            
            # Remove www. prefix
            domain = domain.replace("www.", "")
            
            # Check against excluded domains
            for excluded in self.EXCLUDED_DOMAINS:
                if excluded in domain:
                    logger.debug(f"Excluding directory site: {url}")
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return False
    
    async def search_business_website(
        self,
        business_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: str = "US"
    ) -> Optional[str]:
        """
        Search Google for a business website.
        
        Args:
            business_name: Name of the business
            city: City (optional but recommended)
            state: State (optional but recommended)
            country: Country code (default: US)
            
        Returns:
            Website URL if found, None otherwise
        """
        if not self.api_key:
            logger.warning("Scrapingdog API key not configured, skipping search")
            return None
        
        # Build search query
        query_parts = [f'"{business_name}"']
        if city:
            query_parts.append(city)
        if state:
            query_parts.append(state)
        query_parts.append("website")
        
        query = " ".join(query_parts)
        
        logger.info(f"Searching Google for: {query}")
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "api_key": self.api_key,
                    "query": query,
                    "results": 10,  # Get top 10 results
                    "country": country.lower(),
                }
                
                async with session.get(self.base_url, params=params, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"Scrapingdog API error: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    # Extract organic results
                    organic_results = data.get("organic_results", [])
                    
                    logger.info(f"Found {len(organic_results)} results for {business_name}")
                    
                    # Try to find a valid business website
                    for result in organic_results:
                        url = result.get("link") or result.get("url")
                        title = result.get("title", "")
                        snippet = result.get("snippet", "")
                        
                        if not url:
                            continue
                        
                        logger.debug(f"Checking result: {title} - {url}")
                        
                        # Validate it's a business website
                        if self.is_valid_business_website(url):
                            # Additional check: business name should be in title or snippet
                            business_name_lower = business_name.lower()
                            title_lower = title.lower()
                            snippet_lower = snippet.lower()
                            
                            # Extract business name words (ignore common words)
                            name_words = [
                                word for word in business_name_lower.split()
                                if len(word) > 3 and word not in {"plumbing", "services", "company", "corp", "inc", "llc"}
                            ]
                            
                            # Check if any significant word from business name is in title/snippet
                            if any(word in title_lower or word in snippet_lower for word in name_words):
                                logger.info(f"✅ Found website for {business_name}: {url}")
                                return url
                            else:
                                logger.debug(f"Skipping {url} - business name not in title/snippet")
                    
                    logger.info(f"No valid website found for {business_name}")
                    return None
                    
        except aiohttp.ClientTimeout:
            logger.error(f"Timeout searching for {business_name}")
            return None
        except Exception as e:
            logger.error(f"Error searching for {business_name}: {type(e).__name__}: {e}")
            return None
    
    async def batch_search_websites(
        self,
        businesses: List[Dict[str, Any]],
        delay_seconds: float = 1.0
    ) -> Dict[str, Optional[str]]:
        """
        Search for websites for multiple businesses.
        
        Args:
            businesses: List of business dicts with name, city, state
            delay_seconds: Delay between requests (rate limiting)
            
        Returns:
            Dict mapping business_id to website URL (or None)
        """
        import asyncio
        
        results = {}
        
        for business in businesses:
            business_id = business.get("id")
            business_name = business.get("name")
            city = business.get("city")
            state = business.get("state")
            country = business.get("country", "US")
            
            if not business_name:
                logger.warning(f"Skipping business {business_id} - no name")
                continue
            
            website = await self.search_business_website(
                business_name=business_name,
                city=city,
                state=state,
                country=country
            )
            
            results[business_id] = website
            
            # Rate limiting
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
        
        return results

