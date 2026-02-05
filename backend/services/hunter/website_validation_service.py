"""
Website URL Validation Service.

Validates business website URLs, detects issues (PDFs, broken links, timeouts),
and discovers alternative URLs from Google web results.
"""
import asyncio
import aiohttp
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncSession

from models.business import Business
from models.website_validation import WebsiteValidation

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of website validation."""
    status: str  # valid, invalid, missing, needs_generation
    url: Optional[str]
    url_type: Optional[str]  # html, pdf, image, redirect, invalid
    accessibility: str  # accessible, inaccessible, timeout, not_checked
    http_status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    issues: List[str] = None
    web_results_urls: List[str] = None
    recommended_url: Optional[str] = None
    recommendation: str = "generate"  # keep, replace, generate
    
    def __post_init__(self):
        """Initialize list fields if None."""
        if self.issues is None:
            self.issues = []
        if self.web_results_urls is None:
            self.web_results_urls = []


class WebsiteValidationService:
    """
    Validates business website URLs.
    
    Key Features:
    - HTTP HEAD requests to check accessibility (< 5 sec per business)
    - Content-Type detection (HTML vs PDF vs image)
    - Google web results cross-reference (future enhancement)
    - Invalid URL pattern detection
    - Comprehensive error handling and timeout management
    
    Usage:
        async with WebsiteValidationService(db) as validator:
            result = await validator.validate_business_website(business_data)
            if result.recommendation == "generate":
                # Queue for generation
    """
    
    # Invalid URL patterns (regex)
    INVALID_PATTERNS = [
        r'\.pdf$',
        r'\.jpg$',
        r'\.jpeg$',
        r'\.png$',
        r'\.gif$',
        r'\.webp$',
        r'\.zip$',
        r'\.rar$',
        r'\.tar$',
        r'^file://',
        r'^ftp://',
    ]
    
    # Suspicious domain patterns (not necessarily invalid, but low quality)
    SUSPICIOUS_DOMAINS = [
        'facebook.com',
        'instagram.com',
        'linkedin.com',
        'twitter.com',
        'google.com',
        'maps.google.com',
        'yelp.com',
        'yellowpages.com',
    ]
    
    def __init__(self, db: AsyncSession, timeout: int = 5):
        """
        Initialize validation service.
        
        Args:
            db: Database session for storing validation results
            timeout: Timeout in seconds for URL accessibility checks (default: 5)
        """
        self.db = db
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry - create HTTP session."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                'User-Agent': 'WebMagic/1.0 (Website Validator; +https://webmagic.com)'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP session."""
        if self.session:
            await self.session.close()
    
    async def validate_business_website(
        self,
        business_data: Dict[str, Any],
        check_web_results: bool = False,  # Future enhancement
        store_result: bool = True
    ) -> ValidationResult:
        """
        Main validation entry point.
        
        Args:
            business_data: Business data dict with website_url, gmb_place_id, id
            check_web_results: Whether to check Google web results (not yet implemented)
            store_result: Whether to store validation result in database
            
        Returns:
            ValidationResult with all findings
        """
        url = business_data.get('website_url')
        place_id = business_data.get('gmb_place_id')
        business_id = business_data.get('id')
        
        issues = []
        web_results_urls = []
        
        logger.info(f"Validating website for business: {business_data.get('name')} (ID: {business_id})")
        
        # STEP 1: Check if URL exists
        if not url or not isinstance(url, str) or url.strip() == '':
            logger.info(f"No website URL for business: {business_data.get('name')}")
            
            # TODO: Future enhancement - check web results for hidden URL
            # if check_web_results and place_id:
            #     web_results_urls = await self.fetch_google_web_results(place_id)
            #     if web_results_urls:
            #         issues.append("url_missing_but_found_in_web_results")
            #         result = ValidationResult(...)
            
            result = ValidationResult(
                status='missing',
                url=None,
                url_type=None,
                accessibility='not_checked',
                issues=['no_url_provided'],
                recommendation='generate'
            )
            
            if store_result and business_id:
                await self._store_validation_result(business_id, result)
            
            return result
        
        # STEP 2: Validate URL format
        url = url.strip()
        url_type = self._detect_url_type(url)
        
        if url_type in ['pdf', 'image', 'archive']:
            issues.append(f"url_is_{url_type}")
            logger.warning(f"Invalid URL type '{url_type}' for {url}")
            
            result = ValidationResult(
                status='invalid',
                url=url,
                url_type=url_type,
                accessibility='not_checked',
                issues=issues,
                recommendation='generate'
            )
            
            if store_result and business_id:
                await self._store_validation_result(business_id, result)
            
            return result
        
        # STEP 3: Check if URL is suspicious (social media, etc.)
        if self._is_suspicious_domain(url):
            issues.append('suspicious_domain')
            logger.info(f"Suspicious domain detected: {url}")
        
        # STEP 4: Check accessibility
        accessibility_result = await self.check_url_accessibility(url)
        
        if accessibility_result['accessible']:
            # URL is valid and accessible
            logger.info(f"✅ Valid website: {url} ({accessibility_result['status_code']})")
            
            result = ValidationResult(
                status='valid',
                url=url,
                url_type=accessibility_result.get('content_type', 'html'),
                accessibility='accessible',
                http_status_code=accessibility_result['status_code'],
                response_time_ms=accessibility_result['response_time_ms'],
                issues=issues,
                recommended_url=url,
                recommendation='keep' if not issues else 'replace'  # Replace if suspicious
            )
        else:
            # URL is inaccessible
            issues.append(accessibility_result.get('error', 'inaccessible'))
            logger.warning(f"❌ Inaccessible website: {url} - {issues}")
            
            # TODO: Future enhancement - check web results for alternative
            # if check_web_results and place_id:
            #     web_results_urls = await self.fetch_google_web_results(place_id)
            
            result = ValidationResult(
                status='invalid',
                url=url,
                url_type=url_type,
                accessibility=accessibility_result['accessibility'],
                http_status_code=accessibility_result.get('status_code'),
                response_time_ms=accessibility_result.get('response_time_ms'),
                issues=issues,
                web_results_urls=web_results_urls,
                recommended_url=web_results_urls[0] if web_results_urls else None,
                recommendation='replace' if web_results_urls else 'generate'
            )
        
        # STEP 5: Store validation result
        if store_result and business_id:
            await self._store_validation_result(business_id, result)
        
        return result
    
    async def check_url_accessibility(self, url: str) -> Dict[str, Any]:
        """
        Check if URL is accessible via HTTP HEAD request.
        
        Args:
            url: URL to check
            
        Returns:
            Dict with accessible, status_code, response_time_ms, error, accessibility
        """
        start_time = datetime.utcnow()
        
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            # Try HEAD request first (faster, doesn't download content)
            async with self.session.head(url, allow_redirects=True, ssl=False) as response:
                response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Check status code
                if 200 <= response.status < 400:
                    content_type = response.headers.get('Content-Type', '')
                    
                    return {
                        'accessible': True,
                        'status_code': response.status,
                        'response_time_ms': response_time_ms,
                        'content_type': self._parse_content_type(content_type),
                        'accessibility': 'accessible'
                    }
                else:
                    return {
                        'accessible': False,
                        'status_code': response.status,
                        'response_time_ms': response_time_ms,
                        'error': f'http_status_{response.status}',
                        'accessibility': 'inaccessible'
                    }
        
        except asyncio.TimeoutError:
            logger.debug(f"Timeout checking URL: {url}")
            return {
                'accessible': False,
                'error': 'timeout',
                'accessibility': 'timeout'
            }
        
        except aiohttp.ClientError as e:
            logger.debug(f"Client error checking URL {url}: {type(e).__name__}")
            return {
                'accessible': False,
                'error': f'client_error_{type(e).__name__}',
                'accessibility': 'inaccessible'
            }
        
        except Exception as e:
            logger.error(f"Unexpected error checking URL {url}: {str(e)}")
            return {
                'accessible': False,
                'error': 'unknown_error',
                'accessibility': 'inaccessible'
            }
    
    def _detect_url_type(self, url: str) -> str:
        """
        Detect URL type from extension or pattern.
        
        Args:
            url: URL to analyze
            
        Returns:
            'html', 'pdf', 'image', 'archive', 'invalid'
        """
        url_lower = url.lower()
        
        # Check for file extensions
        if url_lower.endswith('.pdf'):
            return 'pdf'
        elif url_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
            return 'image'
        elif url_lower.endswith(('.zip', '.rar', '.tar', '.gz', '.7z')):
            return 'archive'
        
        # Check for invalid protocols
        parsed = urlparse(url)
        if parsed.scheme and parsed.scheme not in ['http', 'https', '']:
            return 'invalid'
        
        return 'html'
    
    def _is_suspicious_domain(self, url: str) -> bool:
        """
        Check if domain is suspicious (social media, directories, etc.).
        
        Args:
            url: URL to check
            
        Returns:
            True if domain is in suspicious list
        """
        try:
            parsed = urlparse(url if url.startswith('http') else 'https://' + url)
            domain = parsed.netloc.lower()
            
            for suspicious in self.SUSPICIOUS_DOMAINS:
                if suspicious in domain:
                    return True
        except Exception:
            pass
        
        return False
    
    def _parse_content_type(self, content_type: str) -> str:
        """
        Parse Content-Type header to simple type.
        
        Args:
            content_type: Content-Type header value
            
        Returns:
            'html', 'pdf', 'image', 'other'
        """
        content_type_lower = content_type.lower()
        
        if 'text/html' in content_type_lower:
            return 'html'
        elif 'application/pdf' in content_type_lower:
            return 'pdf'
        elif 'image/' in content_type_lower:
            return 'image'
        else:
            return 'other'
    
    async def _store_validation_result(
        self,
        business_id: str,
        result: ValidationResult
    ) -> WebsiteValidation:
        """
        Store validation result in database for audit trail.
        
        NOTE: Does NOT commit - caller must commit the transaction.
        This allows validation to be part of a larger transaction.
        
        Args:
            business_id: Business UUID
            result: ValidationResult to store
            
        Returns:
            Created WebsiteValidation record
        """
        try:
            validation = WebsiteValidation(
                business_id=business_id,
                url_tested=result.url,
                status=result.status,
                url_type=result.url_type,
                accessibility=result.accessibility,
                http_status_code=result.http_status_code,
                response_time_ms=result.response_time_ms,
                issues=result.issues,
                web_results_urls=result.web_results_urls,
                recommended_url=result.recommended_url,
                recommendation=result.recommendation,
                validation_method='http_head',
                validator_version='1.0'
            )
            
            self.db.add(validation)
            await self.db.flush()  # Flush to get ID, but don't commit
            
            logger.debug(f"Stored validation result for business {business_id}: {result.status}")
            
            return validation
        
        except Exception as e:
            logger.error(f"Failed to store validation result: {str(e)}")
            raise
    
    async def fetch_google_web_results(self, place_id: str) -> List[str]:
        """
        Fetch web results URLs for a business from Google.
        
        NOTE: This is a future enhancement. Outscraper doesn't directly provide
        web results in the google_maps_search API. Implementation options:
        1. Check if Outscraper provides this in raw_data
        2. Use Google Custom Search API
        3. Direct scraping (risky, last resort)
        
        Args:
            place_id: Google Place ID
            
        Returns:
            List of discovered URLs
        """
        # TODO: Implement web results fetching
        logger.warning("Web results fetching not yet implemented")
        return []
    
    async def validate_multiple(
        self,
        businesses: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> List[ValidationResult]:
        """
        Validate multiple business websites concurrently.
        
        Args:
            businesses: List of business data dicts
            max_concurrent: Maximum concurrent validations
            
        Returns:
            List of ValidationResults
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_with_semaphore(business_data):
            async with semaphore:
                return await self.validate_business_website(business_data)
        
        tasks = [validate_with_semaphore(b) for b in businesses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, ValidationResult)]
        
        logger.info(f"Validated {len(valid_results)}/{len(businesses)} businesses")
        
        return valid_results

