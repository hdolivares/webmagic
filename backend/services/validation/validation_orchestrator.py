"""
Validation Orchestrator - Coordinates multi-stage website validation.

Pipeline stages:
1. URL Prescreener: Fast checks (file types, domains) - fail fast
2. Playwright: Browser automation - extract website content
3. LLM Validator: Intelligent cross-referencing - make final decision

This orchestrator manages the flow, handles errors, and produces
a final validation result with reasoning.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

import re

from services.validation.url_prescreener import URLPrescreener
from services.validation.playwright_service import PlaywrightValidationService
from services.validation.llm_validator import LLMWebsiteValidator
from services.system_settings_service import SystemSettingsService
from core.config import get_settings
from core.validation_enums import (
    ValidationRecommendation,
    InvalidURLReason,
    categorize_url_domain
)

_SOCIAL_MEDIA_HOSTS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com",
}


def _is_social_media_url(url: str) -> bool:
    """Return True if the URL is a social media profile page."""
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == d or host.endswith("." + d) for d in _SOCIAL_MEDIA_HOSTS)
    except Exception:
        return False


def _extract_website_url_from_content(content_preview: str) -> str | None:
    """
    Scan scraped page content for a real business website URL.

    Used when a social media page is scraped — the bio / About section often
    lists the official website (e.g. "abccpas.com" or "https://example.com").
    Returns the first URL that is NOT itself a social media domain.
    """
    if not content_preview:
        return None

    # Match both bare domains and full URLs mentioned in content
    url_pattern = re.compile(
        r'(?:https?://)?'                # optional scheme
        r'(?:www\.)?'                    # optional www
        r'([a-zA-Z0-9-]{2,63}'          # domain
        r'(?:\.[a-zA-Z]{2,}){1,3})'     # TLD(s)
        r'(?:/[^\s,;"\')]*)?',           # optional path
        re.IGNORECASE
    )

    for m in url_pattern.finditer(content_preview):
        raw = m.group(0).strip().rstrip(".,;\"')")
        # Normalize to full URL
        candidate = raw if raw.startswith("http") else f"https://{raw}"
        try:
            from urllib.parse import urlparse
            parsed = urlparse(candidate)
            host = parsed.netloc.lower().lstrip("www.")
            if not host or "." not in host:
                continue
            # Skip social media, aggregators
            if any(host == d or host.endswith("." + d) for d in _SOCIAL_MEDIA_HOSTS):
                continue
            # Must have a real TLD (at least 2 chars)
            tld = host.rsplit(".", 1)[-1]
            if len(tld) < 2:
                continue
            return candidate
        except Exception:
            continue

    return None

logger = logging.getLogger(__name__)


class ValidationOrchestrator:
    """
    Orchestrates the complete website validation pipeline.
    
    Three stages:
    1. Prescreen (cheap, fast) - Filter obvious invalids
    2. Playwright (expensive) - Extract content
    3. LLM (moderate cost) - Intelligent decision
    
    Design:
    - Each stage can fail independently
    - Results accumulated through pipeline
    - Clear reasoning at each stage
    - Fallback handling for errors
    """
    
    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        playwright_service: Optional[PlaywrightValidationService] = None,
        llm_validator: Optional[LLMWebsiteValidator] = None,
        model_override: Optional[str] = None
    ):
        """
        Initialize orchestrator with services.
        
        Args:
            db: Database session (optional, for loading model from system settings)
            playwright_service: Playwright service instance (creates if None)
            llm_validator: LLM validator instance (creates if None)
            model_override: Optional model to override system/config settings
        """
        self.prescreener = URLPrescreener()
        self.playwright_service = playwright_service
        self.llm_validator = llm_validator  # Will be initialized in validate method
        self.db = db
        self.model_override = model_override
        self._model = None  # Cache for loaded model
    
    async def _get_llm_model(self) -> str:
        """Get LLM model from system settings or config."""
        if self._model:
            return self._model
        
        # Priority 1: Explicit override
        if self.model_override:
            self._model = self.model_override
            logger.info(f"Using model override: {self._model}")
            return self._model
        
        # Priority 2: System settings (from database)
        if self.db:
            try:
                ai_config = await SystemSettingsService.get_ai_config(self.db)
                self._model = ai_config["validation"]["model"]
                logger.info(f"Using validation model from system settings: {self._model}")
                return self._model
            except Exception as e:
                logger.warning(f"Failed to load validation model from system settings: {e}")
        
        # Priority 3: Config/environment (fallback to Haiku, not invalid Sonnet-4)
        settings = get_settings()
        self._model = getattr(settings, 'LLM_MODEL', 'claude-3-haiku-20240307')
        logger.info(f"Using model from config fallback: {self._model}")
        return self._model
    
    async def validate_business_website(
        self,
        business: Dict[str, Any],
        url: str,
        timeout: int = 30000,
        capture_screenshot: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete validation pipeline for a business website.
        
        Args:
            business: Business data {name, phone, email, address, city, state, country}
            url: Website URL to validate
            timeout: Playwright timeout in ms
            capture_screenshot: Whether to capture screenshot
            
        Returns:
            {
                "is_valid": bool,
                "verdict": "valid" | "invalid" | "missing" | "error",
                "confidence": 0.0-1.0,
                "reasoning": str,
                "recommendation": str,
                "stages": {
                    "prescreen": {...},
                    "playwright": {...},
                    "llm": {...}
                },
                "metadata": {
                    "timestamp": ISO string,
                    "total_duration_ms": int,
                    "pipeline_version": str
                }
            }
        """
        start_time = datetime.now()
        result = {
            "is_valid": False,
            "verdict": "error",
            "confidence": 0.0,
            "reasoning": "",
            "recommendation": "mark_invalid_keep_url",
            "stages": {},
            "metadata": {
                "timestamp": start_time.isoformat(),
                "pipeline_version": "1.0.0"
            }
        }
        
        try:
            # STAGE 1: URL Prescreening
            logger.info(f"[Stage 1] Prescreening: {url}")
            prescreen_result = self.prescreener.prescreen_url(url)
            result["stages"]["prescreen"] = prescreen_result
            
            if not prescreen_result["should_validate"]:
                # Failed prescreen - don't proceed to Playwright
                result["verdict"] = "invalid"
                result["confidence"] = 0.95
                result["reasoning"] = prescreen_result["skip_reason"]
                result["recommendation"] = ValidationRecommendation.TRIGGER_SCRAPINGDOG.value
                
                # Categorize the invalid reason
                result["invalid_reason"] = categorize_url_domain(url) or InvalidURLReason.FILE.value
                
                logger.info(f"[Stage 1] Failed: {prescreen_result['skip_reason']}, reason: {result['invalid_reason']}")
                return self._finalize_result(result, start_time)
            
            logger.info(f"[Stage 1] Passed")
            
            # STAGE 2: Playwright Content Extraction
            logger.info(f"[Stage 2] Playwright extraction: {url}")
            
            # Create Playwright service if not provided (context manager)
            if self.playwright_service is None:
                async with PlaywrightValidationService() as pw_service:
                    playwright_result = await pw_service.validate_website(
                        url=url,
                        timeout=timeout,
                        capture_screenshot=capture_screenshot
                    )
            else:
                playwright_result = await self.playwright_service.validate_website(
                    url=url,
                    timeout=timeout,
                    capture_screenshot=capture_screenshot
                )
            
            result["stages"]["playwright"] = playwright_result
            
            # Check if Playwright extraction failed
            if not playwright_result.get("is_valid", False):
                result["verdict"] = "invalid"
                result["confidence"] = 0.8
                result["reasoning"] = f"Website failed to load: {playwright_result.get('error', 'Unknown error')}"
                result["recommendation"] = ValidationRecommendation.RETRY_VALIDATION.value
                
                # Determine technical failure reason
                error = playwright_result.get("error", "").lower()
                if "404" in error or "not found" in error:
                    result["invalid_reason"] = InvalidURLReason.NOT_FOUND.value
                elif "timeout" in error:
                    result["invalid_reason"] = InvalidURLReason.TIMEOUT.value
                elif "ssl" in error or "certificate" in error:
                    result["invalid_reason"] = InvalidURLReason.SSL_ERROR.value
                else:
                    result["invalid_reason"] = InvalidURLReason.SERVER_ERROR.value
                
                logger.warning(f"[Stage 2] Failed: {result['reasoning']}, reason: {result['invalid_reason']}")
                return self._finalize_result(result, start_time)
            
            logger.info(f"[Stage 2] Success - extracted content")
            
            # STAGE 3: LLM Intelligent Validation
            logger.info(f"[Stage 3] LLM validation")
            
            # Initialize LLM validator with correct model if not already done
            if self.llm_validator is None:
                model = await self._get_llm_model()
                self.llm_validator = LLMWebsiteValidator(model=model)
            
            # Prepare website data for LLM
            website_data = self._prepare_website_data_for_llm(url, playwright_result)
            
            # Call LLM validator
            llm_result = await self.llm_validator.validate_website_match(
                business=business,
                website_data=website_data
            )
            
            result["stages"]["llm"] = llm_result

            # ----------------------------------------------------------------
            # SOCIAL MEDIA RESCUE: If we validated a social media URL and the
            # LLM rejected it, check whether the scraped page content contains
            # the real business website URL (often listed in the bio/About).
            # ----------------------------------------------------------------
            llm_verdict = llm_result.get("verdict", "")
            if llm_verdict in ("missing", "invalid") and _is_social_media_url(url):
                content_preview = playwright_result.get("content_preview", "")
                rescued_url = _extract_website_url_from_content(content_preview)
                if rescued_url and rescued_url.lower() != url.lower():
                    logger.info(
                        f"🔄 Social-media rescue: found '{rescued_url}' in page content "
                        f"— re-validating instead of marking no-website"
                    )
                    # Re-run validation on the rescued URL recursively (one level deep)
                    rescued_result = await self.validate_business_website(
                        business=business,
                        url=rescued_url,
                        timeout=timeout,
                        capture_screenshot=capture_screenshot
                    )
                    if rescued_result.get("is_valid"):
                        logger.info(f"✅ Rescued website validated: {rescued_url}")
                        # Merge rescued result back, noting the rescue path
                        rescued_result["stages"]["social_media_rescue"] = {
                            "original_url": url,
                            "rescued_from": "social_media_content",
                            "rescued_url": rescued_url
                        }
                        rescued_result["rescued_from_social_media"] = True
                        return self._finalize_result(rescued_result, start_time)
                    else:
                        logger.info(
                            f"Rescued URL '{rescued_url}' also failed validation "
                            f"— proceeding with original social-media rejection"
                        )

            # LLM verdict is final
            result["verdict"] = llm_result["verdict"]
            result["confidence"] = llm_result["confidence"]
            result["reasoning"] = llm_result["reasoning"]
            
            # Map LLM recommendation to new system
            llm_recommendation = llm_result.get("recommendation", "")
            if llm_recommendation == "clear_url_and_mark_missing":
                result["recommendation"] = ValidationRecommendation.TRIGGER_SCRAPINGDOG.value
            elif llm_recommendation == "keep_url":
                result["recommendation"] = ValidationRecommendation.KEEP_URL.value
            elif llm_recommendation == "mark_invalid_keep_url":
                result["recommendation"] = ValidationRecommendation.RETRY_VALIDATION.value
            else:
                result["recommendation"] = llm_recommendation  # Use as-is if already new format
            
            # Extract invalid reason from LLM signals
            if result["verdict"] != "valid":
                match_signals = llm_result.get("match_signals", {})
                if match_signals.get("is_directory"):
                    result["invalid_reason"] = InvalidURLReason.DIRECTORY.value
                elif match_signals.get("is_aggregator"):
                    result["invalid_reason"] = InvalidURLReason.AGGREGATOR.value
                elif not match_signals.get("name_match"):
                    result["invalid_reason"] = InvalidURLReason.WRONG_BUSINESS.value
                elif not match_signals.get("phone_match") and not match_signals.get("address_match"):
                    result["invalid_reason"] = InvalidURLReason.NO_CONTACT.value
                else:
                    result["invalid_reason"] = categorize_url_domain(url)
            
            # Set is_valid based on verdict
            result["is_valid"] = (llm_result["verdict"] == "valid")
            
            logger.info(
                f"[Stage 3] Complete - Verdict: {result['verdict']} "
                f"(confidence={result['confidence']:.2f})"
            )
            
            return self._finalize_result(result, start_time)
            
        except Exception as e:
            logger.error(f"Validation pipeline error: {e}", exc_info=True)
            result["verdict"] = "error"
            result["confidence"] = 0.0
            result["reasoning"] = f"Pipeline error: {str(e)}"
            result["recommendation"] = "mark_invalid_keep_url"
            
            return self._finalize_result(result, start_time)
    
    def _prepare_website_data_for_llm(
        self,
        url: str,
        playwright_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract and format website data from Playwright result for LLM.
        
        Args:
            url: Original URL
            playwright_result: Result from Playwright validation
            
        Returns:
            Formatted dict for LLM prompt
        """
        # CRITICAL FIX: Playwright returns FLAT structure, not nested under "content"
        # The bug was: content_info = playwright_result.get("content", {}) <- "content" key doesn't exist!
        # This caused all phones/emails/content to be empty arrays, making LLM reject valid websites
        
        return {
            "url": url,
            "final_url": playwright_result.get("final_url", url),
            "title": playwright_result.get("title", ""),
            "meta_description": playwright_result.get("meta_description", ""),
            "phones": playwright_result.get("phones", []),
            "emails": playwright_result.get("emails", []),
            "has_address": playwright_result.get("has_address", False),
            "has_hours": playwright_result.get("has_hours", False),
            "content_preview": playwright_result.get("content_preview", "")[:500],
            "word_count": playwright_result.get("word_count", 0),
        }
    
    def _finalize_result(
        self,
        result: Dict[str, Any],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Add final metadata to result."""
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        result["metadata"]["total_duration_ms"] = duration_ms
        
        return result
    
    async def __aenter__(self):
        """Context manager entry - initialize Playwright if needed."""
        if self.playwright_service is None:
            self.playwright_service = PlaywrightValidationService()
            await self.playwright_service.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup Playwright if we created it."""
        if self.playwright_service is not None:
            await self.playwright_service.__aexit__(exc_type, exc_val, exc_tb)
            self.playwright_service = None
