"""
Core Playwright validation service.
Orchestrates browser automation, content extraction, and screenshot capture.
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError
import logging

from .stealth_config import create_stealth_browser, human_like_navigation, wait_for_stable_page
from .content_analyzer import ContentAnalyzer

logger = logging.getLogger(__name__)


class PlaywrightValidationService:
    """
    Playwright-based website validation service.
    
    Features:
    - Anti-bot detection avoidance
    - Human-like navigation behavior
    - Content extraction and analysis
    - Screenshot capture
    - Error handling and retry logic
    
    Usage:
        async with PlaywrightValidationService() as validator:
            result = await validator.validate_website("https://example.com")
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        self.content_analyzer = ContentAnalyzer()
    
    async def __aenter__(self):
        """Context manager entry - initialize browser."""
        try:
            self.playwright = await async_playwright().start()
            self.browser, self.context = await create_stealth_browser(self.playwright)
            logger.info("Playwright validation service initialized")
            return self
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            await self._cleanup()
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        await self._cleanup()
    
    async def _cleanup(self):
        """Cleanup browser resources."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Playwright validation service cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    async def validate_website(
        self,
        url: str,
        timeout: int = 30000,
        capture_screenshot: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a website and extract information.
        
        Args:
            url: Website URL to validate
            timeout: Maximum time to wait for page load (ms)
            capture_screenshot: Whether to capture screenshot
            
        Returns:
            Dictionary containing validation results:
            {
                "is_valid": bool,
                "url": str,
                "status_code": int,
                "title": str,
                "meta_description": str,
                "phones": List[str],
                "emails": List[str],
                "has_contact_info": bool,
                "has_phone": bool,
                "has_email": bool,
                "has_address": bool,
                "has_hours": bool,
                "word_count": int,
                "content_length": int,
                "content_preview": str,
                "has_images": bool,
                "has_forms": bool,
                "social_links": List[str],
                "is_placeholder": bool,
                "quality_score": int,
                "screenshot_base64": str or None,
                "load_time_ms": int,
                "error": str or None,
                "validation_timestamp": str,
            }
        """
        page = None
        start_time = datetime.utcnow()
        
        try:
            # Normalize URL
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            
            logger.info(f"Validating website: {url}")
            
            # Create new page
            page = await self.context.new_page()
            
            # Set timeout
            page.set_default_timeout(timeout)
            
            # Navigate with human-like behavior
            try:
                await human_like_navigation(page, url)
            except PlaywrightError as e:
                if 'timeout' in str(e).lower():
                    logger.warning(f"Navigation timeout for {url}, attempting with load state")
                    await human_like_navigation(page, url, wait_until='load')
                else:
                    raise
            
            # Wait for page to be stable
            await wait_for_stable_page(page, timeout=5000)
            
            # Get final URL (after redirects)
            final_url = page.url
            
            # Extract page information using content analyzer
            content_info = await self.content_analyzer.analyze_page(page)
            
            # Capture screenshot if requested
            screenshot_base64 = None
            if capture_screenshot:
                screenshot_base64 = await self._capture_screenshot(page)
            
            # Calculate load time
            load_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Build result
            result = {
                "is_valid": True,
                "url": url,
                "final_url": final_url,
                "status_code": 200,  # Playwright doesn't easily expose status code
                "load_time_ms": load_time_ms,
                "screenshot_base64": screenshot_base64,
                "error": None,
                "validation_timestamp": datetime.utcnow().isoformat(),
                **content_info  # Merge content analyzer results
            }
            
            logger.info(
                f"Validation successful for {url}: "
                f"quality_score={content_info.get('quality_score', 0)}, "
                f"has_contact={content_info.get('has_contact_info', False)}"
            )
            
            return result
            
        except PlaywrightError as e:
            error_msg = str(e)
            logger.error(f"Playwright error validating {url}: {error_msg}")
            
            return {
                "is_valid": False,
                "url": url,
                "final_url": None,
                "status_code": 0,
                "error": f"Browser error: {error_msg}",
                "error_type": "playwright_error",
                "load_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "validation_timestamp": datetime.utcnow().isoformat(),
                **self._empty_content_result()
            }
            
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout validating {url}")
            
            return {
                "is_valid": False,
                "url": url,
                "final_url": None,
                "status_code": 0,
                "error": f"Timeout: Page took too long to load",
                "error_type": "timeout",
                "load_time_ms": timeout,
                "validation_timestamp": datetime.utcnow().isoformat(),
                **self._empty_content_result()
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error validating {url}: {error_msg}", exc_info=True)
            
            return {
                "is_valid": False,
                "url": url,
                "final_url": None,
                "status_code": 0,
                "error": f"Unexpected error: {error_msg}",
                "error_type": "unknown",
                "load_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "validation_timestamp": datetime.utcnow().isoformat(),
                **self._empty_content_result()
            }
            
        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")
    
    async def _capture_screenshot(self, page: Page) -> Optional[str]:
        """
        Capture page screenshot and return as base64.
        
        Args:
            page: Playwright page object
            
        Returns:
            Base64 encoded screenshot or None if capture fails
        """
        try:
            import base64
            
            # Capture full page screenshot
            screenshot_bytes = await page.screenshot(
                full_page=True,
                type='png'
            )
            
            # Convert to base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            logger.debug(f"Screenshot captured: {len(screenshot_bytes)} bytes")
            
            return screenshot_base64
            
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    def _empty_content_result(self) -> Dict[str, Any]:
        """Return empty content result for failed validations."""
        return {
            "title": None,
            "meta_description": None,
            "phones": [],
            "emails": [],
            "has_phone": False,
            "has_email": False,
            "has_address": False,
            "has_hours": False,
            "has_contact_info": False,
            "word_count": 0,
            "content_length": 0,
            "content_preview": None,
            "has_images": False,
            "has_forms": False,
            "social_links": [],
            "is_placeholder": True,
            "quality_score": 0,
            "screenshot_base64": None,
        }
    
    async def validate_multiple_websites(
        self,
        urls: list[str],
        max_concurrent: int = 3
    ) -> Dict[str, Dict[str, Any]]:
        """
        Validate multiple websites concurrently.
        
        Args:
            urls: List of URLs to validate
            max_concurrent: Maximum number of concurrent validations
            
        Returns:
            Dictionary mapping URL to validation result
        """
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_with_semaphore(url: str):
            async with semaphore:
                return url, await self.validate_website(url)
        
        # Run validations concurrently
        tasks = [validate_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dictionary
        result_dict = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Validation task failed: {result}")
                continue
            url, validation_result = result
            result_dict[url] = validation_result
        
        return result_dict

