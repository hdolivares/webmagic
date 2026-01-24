"""
SMS Content Generator - AI-Powered SMS Messages.

Uses Claude Sonnet to generate personalized, concise SMS messages
optimized for business outreach.

Author: WebMagic Team
Date: January 21, 2026
"""
from typing import Dict, Any, Optional
import logging
from anthropic import AsyncAnthropic

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SMSGenerator:
    """
    Generate personalized SMS messages using Claude AI.
    
    Features:
    - Length optimization (160 chars = 1 segment)
    - Tone customization (professional, friendly, urgent)
    - Business-specific personalization
    - URL shortening recommendations
    - Compliance footer inclusion
    """
    
    # SMS length limits
    SINGLE_SEGMENT_LIMIT = 160
    RECOMMENDED_LIMIT = 140  # Leave room for compliance footer
    
    # Message variants
    VARIANTS = {
        "professional": "formal and professional business tone",
        "friendly": "warm, approachable, and conversational",
        "urgent": "direct and action-oriented for emergency services"
    }
    
    def __init__(self):
        """Initialize SMS generator with Claude AI."""
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "Anthropic API key not configured. "
                "Set ANTHROPIC_API_KEY in .env"
            )
        
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20241022"
        logger.info("SMS generator initialized")
    
    async def generate_sms(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str] = None,
        variant: str = "professional",
        max_length: int = RECOMMENDED_LIMIT
    ) -> str:
        """
        Generate SMS content for business outreach.
        
        Args:
            business_data: Business info (name, category, city, rating, etc.)
            site_url: Optional generated site URL
            variant: Message tone (professional, friendly, urgent)
            max_length: Maximum SMS length (default: 140 chars)
        
        Returns:
            SMS body text optimized for single segment
        
        Example:
            >>> business_data = {
            ...     "name": "ABC Plumbing",
            ...     "category": "plumber",
            ...     "city": "Chicago",
            ...     "state": "IL",
            ...     "rating": 4.8
            ... }
            >>> sms = await generator.generate_sms(business_data)
            >>> print(sms)
            "ABC Plumbing - We built you a website! Preview: [URL]. Reply STOP to opt out."
        """
        # Get variant description
        tone = self.VARIANTS.get(variant, self.VARIANTS["professional"])
        
        # Build AI prompt
        prompt = self._build_prompt(
            business_data=business_data,
            site_url=site_url,
            tone=tone,
            max_length=max_length
        )
        
        # Generate SMS via Claude
        try:
            # Use streaming to avoid timeout limits on large max_tokens
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=64000,  # Max for Claude Sonnet 4.5
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                sms_body = (await stream.get_final_text()).strip()
            
            # Remove quotes if Claude added them
            sms_body = sms_body.strip('"').strip("'")
            
            # Add compliance footer if not present
            sms_body = self._ensure_compliance_footer(sms_body)
            
            # Validate length
            if len(sms_body) > self.SINGLE_SEGMENT_LIMIT:
                logger.warning(
                    f"SMS exceeds single segment ({len(sms_body)} chars), "
                    f"will cost 2x: {sms_body[:50]}..."
                )
            
            logger.info(f"Generated SMS ({len(sms_body)} chars): {sms_body[:50]}...")
            return sms_body
        
        except Exception as e:
            logger.error(f"SMS generation failed: {e}")
            # Fallback to template
            return self._get_fallback_template(business_data, site_url)
    
    def _build_prompt(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str],
        tone: str,
        max_length: int
    ) -> str:
        """
        Build AI prompt for SMS generation.
        
        Args:
            business_data: Business information
            site_url: Website URL
            tone: Desired message tone
            max_length: Maximum length
        
        Returns:
            Prompt string for Claude
        """
        business_name = business_data.get("name", "the business")
        category = business_data.get("category", "business")
        city = business_data.get("city", "")
        state = business_data.get("state", "")
        rating = business_data.get("rating", 0)
        
        location = f"{city}, {state}" if city and state else city or state or "your area"
        rating_str = f"{rating}⭐" if rating > 0 else ""
        
        prompt = f"""Generate a concise SMS message for business outreach.

Business: {business_name}
Category: {category}
Location: {location}
Rating: {rating_str}
Website: {site_url or "[creating...]"}

REQUIREMENTS:
1. Maximum {max_length} characters (STRICT LIMIT)
2. Tone: {tone}
3. Mention we built them a professional website they can preview
4. Include call-to-action (view site or reply)
5. Include "Reply STOP to opt out" (compliance required)
6. Be direct and valuable
7. Do NOT say "free website" - the preview is free, claim is $495
7. No emojis unless tone is "friendly"
8. Use proper grammar and punctuation

AVOID:
- Spam language ("limited time", "act now", "free money")
- All caps or excessive punctuation
- Misleading claims
- Personal information requests

Return ONLY the SMS message text, no quotes or explanations."""

        return prompt
    
    def _ensure_compliance_footer(self, sms_body: str) -> str:
        """
        Ensure SMS includes opt-out compliance text.
        
        Args:
            sms_body: Generated SMS text
        
        Returns:
            SMS with compliance footer if not present
        """
        # Check if compliance text is already present
        compliance_keywords = ["stop", "opt out", "unsubscribe", "opt-out"]
        
        if any(keyword in sms_body.lower() for keyword in compliance_keywords):
            return sms_body
        
        # Add compliance footer
        footer = " Reply STOP to opt out."
        
        # If adding footer exceeds limit, truncate message
        if len(sms_body) + len(footer) > self.SINGLE_SEGMENT_LIMIT:
            available_length = self.SINGLE_SEGMENT_LIMIT - len(footer)
            sms_body = sms_body[:available_length].rsplit(' ', 1)[0]  # Truncate at word boundary
        
        return sms_body + footer
    
    def _get_fallback_template(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str]
    ) -> str:
        """
        Get fallback SMS template if AI generation fails.
        
        Args:
            business_data: Business information
            site_url: Website URL
        
        Returns:
            Template-based SMS message
        """
        business_name = business_data.get("name", "Your business")
        category = business_data.get("category", "business")
        
        # Shorten URL if too long
        url_display = self._shorten_url_display(site_url) if site_url else "[creating...]"
        
        # Build template
        template = (
            f"{business_name} - We built you a {category} website! "
            f"Preview: {url_display}. Reply STOP to opt out."
        )
        
        # Ensure it fits in single segment
        if len(template) > self.SINGLE_SEGMENT_LIMIT:
            # Truncate business name if needed
            max_name_length = 30
            if len(business_name) > max_name_length:
                business_name = business_name[:max_name_length] + "..."
            
            template = (
                f"{business_name} - Free website: {url_display}. "
                f"Reply STOP to opt out."
            )
        
        return template
    
    def _shorten_url_display(self, url: str) -> str:
        """
        Shorten URL for display in SMS.
        
        Args:
            url: Full URL
        
        Returns:
            Shortened URL for display
        """
        # Remove protocol
        url_display = url.replace("https://", "").replace("http://", "")
        
        # Remove trailing slash
        url_display = url_display.rstrip("/")
        
        # If still too long, truncate
        if len(url_display) > 40:
            url_display = url_display[:37] + "..."
        
        return url_display
    
    async def generate_batch(
        self,
        businesses: list[Dict[str, Any]],
        site_urls: Optional[list[str]] = None,
        variant: str = "professional"
    ) -> list[str]:
        """
        Generate SMS messages for multiple businesses.
        
        Args:
            businesses: List of business data dicts
            site_urls: Optional list of site URLs (must match businesses length)
            variant: Message tone
        
        Returns:
            List of generated SMS messages
        """
        if site_urls and len(site_urls) != len(businesses):
            raise ValueError("site_urls length must match businesses length")
        
        results = []
        
        for i, business_data in enumerate(businesses):
            site_url = site_urls[i] if site_urls else None
            
            try:
                sms = await self.generate_sms(
                    business_data=business_data,
                    site_url=site_url,
                    variant=variant
                )
                results.append(sms)
            except Exception as e:
                logger.error(f"Batch generation failed for {business_data.get('name')}: {e}")
                # Use fallback
                results.append(self._get_fallback_template(business_data, site_url))
        
        return results
    
    @staticmethod
    def estimate_segments(sms_body: str) -> int:
        """
        Estimate number of SMS segments.
        
        Args:
            sms_body: SMS message text
        
        Returns:
            Estimated segment count
        """
        length = len(sms_body)
        
        # Single segment
        if length <= 160:
            return 1
        
        # Multi-segment (each segment is 153 chars due to concatenation header)
        return (length + 152) // 153
    
    @staticmethod
    def estimate_cost(sms_body: str, cost_per_segment: float = 0.0079) -> float:
        """
        Estimate SMS cost.
        
        Args:
            sms_body: SMS message text
            cost_per_segment: Cost per segment (default: Twilio US rate)
        
        Returns:
            Estimated cost in USD
        """
        segments = SMSGenerator.estimate_segments(sms_body)
        return segments * cost_per_segment

