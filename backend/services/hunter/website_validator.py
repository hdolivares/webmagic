"""
Website Validation Service.

Verifies if a business actually has a working, legitimate website.
Many Google Maps listings have invalid, dead, or fake website URLs.

This service:
1. Checks if URL is accessible (HTTP 200)
2. Validates it's not a Google Maps redirect
3. Checks if it's a real website (not just a social media profile)
4. Verifies basic content exists
"""
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import re

logger = logging.getLogger(__name__)

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 10

# Non-website domains (social media, directories, etc.)
NON_WEBSITE_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "yelp.com",
    "google.com",
    "maps.google.com",
    "goo.gl",
    "bit.ly",
    "tinyurl.com",
    "yellowpages.com",
    "superpages.com",
    "mapquest.com",
}

# Google Maps redirect patterns
GOOGLE_REDIRECT_PATTERNS = [
    r"google\.com/url",
    r"maps\.google\.com",
    r"goo\.gl",
    r"g\.page",
]


class WebsiteValidationResult:
    """Result of website validation."""
    
    def __init__(
        self,
        url: str,
        is_valid: bool,
        is_accessible: bool = False,
        is_real_website: bool = False,
        has_content: bool = False,
        status_code: Optional[int] = None,
        final_url: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        self.url = url
        self.is_valid = is_valid
        self.is_accessible = is_accessible
        self.is_real_website = is_real_website
        self.has_content = has_content
        self.status_code = status_code
        self.final_url = final_url
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "is_valid": self.is_valid,
            "is_accessible": self.is_accessible,
            "is_real_website": self.is_real_website,
            "has_content": self.has_content,
            "status_code": self.status_code,
            "final_url": self.final_url,
            "error_message": self.error_message
        }
    
    def __repr__(self):
        status = "VALID" if self.is_valid else "INVALID"
        return f"<WebsiteValidation {status}: {self.url}>"


class WebsiteValidator:
    """
    Validates if businesses have legitimate, working websites.
    """
    
    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for validation."""
        url = url.strip()
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        return url
    
    def _is_google_redirect(self, url: str) -> bool:
        """Check if URL is a Google Maps redirect."""
        for pattern in GOOGLE_REDIRECT_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def _is_social_media_or_directory(self, url: str) -> bool:
        """Check if URL is just a social media profile or directory listing."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')
            
            # Check exact match
            if domain in NON_WEBSITE_DOMAINS:
                return True
            
            # Check if it's a subdomain of non-website domains
            for non_website in NON_WEBSITE_DOMAINS:
                if domain.endswith(f".{non_website}"):
                    return True
            
            return False
        except Exception:
            return False
    
    def _has_meaningful_content(self, html: str) -> bool:
        """
        Check if HTML has meaningful content (basic heuristic).
        
        A real business website should have:
        - More than 500 characters of content
        - Common HTML elements (body, div, etc.)
        - Not just a redirect page
        """
        if not html or len(html) < 500:
            return False
        
        html_lower = html.lower()
        
        # Check for basic HTML structure
        if '<body' not in html_lower:
            return False
        
        # Check it's not just an error or redirect page
        error_indicators = [
            'page not found',
            '404',
            'site is under construction',
            'coming soon',
            'domain for sale',
            'parked domain',
            'this domain may be for sale'
        ]
        
        for indicator in error_indicators:
            if indicator in html_lower:
                return False
        
        return True
    
    async def validate_url(self, url: Optional[str]) -> WebsiteValidationResult:
        """
        Validate a single URL.
        
        Args:
            url: Website URL to validate
        
        Returns:
            WebsiteValidationResult with validation details
        """
        # Handle empty/null URLs
        if not url:
            return WebsiteValidationResult(
                url="",
                is_valid=False,
                error_message="No URL provided"
            )
        
        try:
            # Normalize URL
            normalized_url = self._normalize_url(url)
            
            # Check if it's a Google redirect
            if self._is_google_redirect(normalized_url):
                return WebsiteValidationResult(
                    url=normalized_url,
                    is_valid=False,
                    error_message="Google Maps redirect URL"
                )
            
            # Check if it's social media or directory
            if self._is_social_media_or_directory(normalized_url):
                return WebsiteValidationResult(
                    url=normalized_url,
                    is_valid=False,
                    is_real_website=False,
                    error_message="Social media or directory listing, not a real website"
                )
            
            # Try to fetch the URL
            if not self.session:
                raise RuntimeError("WebsiteValidator must be used as async context manager")
            
            async with self.session.get(
                normalized_url,
                allow_redirects=True,
                ssl=False  # Don't verify SSL to avoid certificate errors
            ) as response:
                status_code = response.status
                final_url = str(response.url)
                
                # Check if accessible (2xx status code)
                is_accessible = 200 <= status_code < 300
                
                if not is_accessible:
                    return WebsiteValidationResult(
                        url=normalized_url,
                        is_valid=False,
                        is_accessible=False,
                        status_code=status_code,
                        final_url=final_url,
                        error_message=f"HTTP {status_code}"
                    )
                
                # Get content
                html = await response.text()
                
                # Check if final URL is social media (after redirects)
                if self._is_social_media_or_directory(final_url):
                    return WebsiteValidationResult(
                        url=normalized_url,
                        is_valid=False,
                        is_accessible=True,
                        is_real_website=False,
                        status_code=status_code,
                        final_url=final_url,
                        error_message="Redirects to social media or directory"
                    )
                
                # Check for meaningful content
                has_content = self._has_meaningful_content(html)
                
                # Everything checks out - this is a valid website
                if has_content:
                    return WebsiteValidationResult(
                        url=normalized_url,
                        is_valid=True,
                        is_accessible=True,
                        is_real_website=True,
                        has_content=True,
                        status_code=status_code,
                        final_url=final_url
                    )
                else:
                    return WebsiteValidationResult(
                        url=normalized_url,
                        is_valid=False,
                        is_accessible=True,
                        is_real_website=True,
                        has_content=False,
                        status_code=status_code,
                        final_url=final_url,
                        error_message="Insufficient content (possible placeholder/parked domain)"
                    )
        
        except asyncio.TimeoutError:
            return WebsiteValidationResult(
                url=url,
                is_valid=False,
                error_message=f"Timeout after {self.timeout}s"
            )
        except aiohttp.ClientError as e:
            return WebsiteValidationResult(
                url=url,
                is_valid=False,
                error_message=f"Connection error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error validating {url}: {str(e)}")
            return WebsiteValidationResult(
                url=url,
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )
    
    async def validate_batch(
        self,
        urls: List[str],
        max_concurrent: int = 10
    ) -> List[WebsiteValidationResult]:
        """
        Validate multiple URLs concurrently.
        
        Args:
            urls: List of URLs to validate
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of WebsiteValidationResult objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_with_semaphore(url: str) -> WebsiteValidationResult:
            async with semaphore:
                return await self.validate_url(url)
        
        tasks = [validate_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    WebsiteValidationResult(
                        url=urls[i],
                        is_valid=False,
                        error_message=f"Exception: {str(result)}"
                    )
                )
            else:
                final_results.append(result)
        
        return final_results


def has_valid_website(website_url: Optional[str]) -> bool:
    """
    Quick synchronous check if a URL looks like it might be valid.
    
    This is a fast pre-filter before async validation.
    Checks:
    - URL is not empty
    - URL is not a social media profile
    - URL is not a Google redirect
    
    Args:
        website_url: URL to check
    
    Returns:
        True if URL looks potentially valid, False otherwise
    """
    if not website_url:
        return False
    
    url_lower = website_url.lower()
    
    # Check for Google redirects
    for pattern in GOOGLE_REDIRECT_PATTERNS:
        if re.search(pattern, url_lower):
            return False
    
    # Check for social media
    for domain in NON_WEBSITE_DOMAINS:
        if domain in url_lower:
            return False
    
    return True


# Standalone function for use in filters
def quick_website_check(business_data: Dict[str, Any]) -> bool:
    """
    Quick check if business appears to have a valid website.
    
    Args:
        business_data: Business dictionary with 'website_url' field
    
    Returns:
        True if business appears to NOT have a valid website, False otherwise
    """
    website_url = business_data.get("website_url") or business_data.get("website")
    return not has_valid_website(website_url)


# Example usage
async def main():
    """Test the website validator."""
    test_urls = [
        "https://example.com",
        "facebook.com/somebusiness",
        "https://google.com/url?q=something",
        "http://nonexistentwebsite123456.com",
        "https://www.businesswebsite.com",
        "",
        None,
    ]
    
    async with WebsiteValidator(timeout=5) as validator:
        results = await validator.validate_batch(test_urls)
        
        print("\n" + "="*60)
        print("Website Validation Results:")
        print("="*60)
        
        for result in results:
            print(f"\nURL: {result.url}")
            print(f"  Valid: {result.is_valid}")
            print(f"  Accessible: {result.is_accessible}")
            print(f"  Real Website: {result.is_real_website}")
            print(f"  Has Content: {result.has_content}")
            print(f"  Status: {result.status_code}")
            if result.error_message:
                print(f"  Error: {result.error_message}")


if __name__ == "__main__":
    asyncio.run(main())

