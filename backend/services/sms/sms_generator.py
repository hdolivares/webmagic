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
        "friendly": "warm and conversational — feels like a real person texting, not a company (RECOMMENDED)",
        "professional": "polite and professional but still personal — suitable for formal service businesses",
        "urgent": "direct and confident — ideal for emergency/on-demand services like plumbers, locksmiths, HVAC"
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
    
    # Template variables available for custom messages (Settings > Messaging)
    TEMPLATE_VARIABLES = ("business_name", "category", "site_url", "city", "state", "rating", "review_count")

    async def generate_sms(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str] = None,
        variant: str = "friendly",
        max_length: int = RECOMMENDED_LIMIT,
        custom_template: Optional[str] = None,
    ) -> str:
        """
        Generate SMS content for business outreach.
        
        Args:
            business_data: Business info (name, category, city, rating, etc.)
            site_url: Optional generated site URL
            variant: Message tone (professional, friendly, urgent)
            max_length: Maximum SMS length (default: 140 chars)
            custom_template: If set, use this template with variable substitution instead of AI.
                             Variables: {{business_name}}, {{category}}, {{site_url}}, {{city}}, {{state}}
        
        Returns:
            SMS body text optimized for single segment
        """
        if custom_template and custom_template.strip():
            body = self._substitute_template(custom_template.strip(), business_data, site_url)
            body = self._ensure_compliance_footer(body)
            return body

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
        """Build AI prompt for SMS generation using research-backed psychology."""
        business_name = business_data.get("name", "the business")
        category = business_data.get("category", "business")
        city = business_data.get("city", "")
        state = business_data.get("state", "")
        rating = business_data.get("rating", 0)
        review_count = business_data.get("review_count", 0)

        location = f"{city}, {state}" if city and state else city or state or ""
        location_hint = f" in {location}" if location else ""

        # Build review signal — the single most powerful personalization hook
        if rating and rating >= 4.0 and review_count and review_count >= 5:
            review_signal = f"They have a {rating}⭐ rating from {review_count} Google reviews."
        elif rating and rating >= 4.0:
            review_signal = f"They have a {rating}⭐ Google rating."
        else:
            review_signal = "They have an active Google Business profile."

        prompt = f"""You are writing a cold outreach SMS from a single person (not a company) to the owner of a small business. We found their Google Business listing, confirmed they have no website, and built them a free preview site.

BUSINESS DETAILS:
- Name: {business_name}{location_hint}
- Category: {category}
- {review_signal}
- Preview website: {site_url or "[URL]"}

TONE: {tone}

RESEARCH-BACKED RULES (from analysis of 25B+ SMS messages and 100k+ sales conversations):
1. STRICT maximum {max_length} characters — must fit in ONE SMS segment
2. Lead with a SPECIFIC compliment about their reviews — this is the #1 engagement trigger because it proves you actually looked them up
3. Immediately name the gap: they have great reviews but NO website
4. Deliver the value: you already built it, here's the link
5. End with ONE soft question — messages with questions get 28% reply rates vs 24% without
6. "I built" / "I made" beats "we created" — sounds human, not corporate
7. Use "your" and "you" throughout — second-person language outperforms first-person
8. NO spam triggers: free, limited time, act now, click here, congratulations, winner
9. NO exclamation marks after the opening greeting
10. Opt-out must be woven into the closing sentence naturally — do NOT add "Reply STOP to opt out" as a separate robotic sentence. Instead fold it into the soft question: e.g. "Want to personalize it? Just reply NO if not for you." or "Interested? Reply NO if not your thing." The opt-out must feel like a natural conversational out, not a legal disclaimer bolted on.

PSYCHOLOGICAL STRUCTURE (follow this order):
[Greeting with business name] → [Compliment their reviews — show you looked them up] → [Name the gap: no website] → [Value: built one for them + URL] → [Soft question + natural opt-out woven in]

EXAMPLE OUTPUT (friendly variant, ~155 chars):
"Hi {business_name}! Saw your {rating}⭐ Google reviews — nice work. No website yet so I built one: {site_url or '[URL]'}. Want to personalize it? Just reply NO if not for you."

AVOID:
- "We created a preview website" (sounds like a blast)
- "Take a look and let us know" (weak, generic)
- "Check it out!" (pushy)
- Starting with "I" (start with "Hi [BusinessName]")
- Any mention of payment, pricing, or urgency

Return ONLY the SMS message text — no quotes, no labels, no explanation."""

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
        compliance_keywords = ["stop", "opt out", "unsubscribe", "opt-out", "reply no", "just no", "not for you", "not interested"]
        
        if any(keyword in sms_body.lower() for keyword in compliance_keywords):
            return sms_body
        
        # Add compliance footer — natural phrasing that doesn't break conversational tone
        footer = " Just reply NO if not for you."
        
        # If adding footer exceeds limit, truncate message
        if len(sms_body) + len(footer) > self.SINGLE_SEGMENT_LIMIT:
            available_length = self.SINGLE_SEGMENT_LIMIT - len(footer)
            sms_body = sms_body[:available_length].rsplit(' ', 1)[0]  # Truncate at word boundary
        
        return sms_body + footer
    
    def _substitute_template(
        self,
        template: str,
        business_data: Dict[str, Any],
        site_url: Optional[str],
    ) -> str:
        """
        Replace {{variable}} placeholders in a template.
        Available: {{business_name}}, {{category}}, {{site_url}}, {{city}}, {{state}},
                   {{rating}}, {{review_count}}
        """
        business_name = (business_data.get("name") or "Your business").strip()
        category = (business_data.get("category") or "business").strip()
        city = (business_data.get("city") or "").strip()
        state = (business_data.get("state") or "").strip()
        url = (site_url or "").strip() or "[creating...]"
        rating = business_data.get("rating", 0)
        review_count = business_data.get("review_count", 0)

        # Format rating as "4.8⭐" or omit star if no rating
        rating_str = f"{rating}⭐" if rating and float(rating) > 0 else "great"
        review_count_str = str(int(review_count)) if review_count else ""

        return (
            template.replace("{{business_name}}", business_name)
            .replace("{{category}}", category)
            .replace("{{site_url}}", url)
            .replace("{{city}}", city)
            .replace("{{state}}", state)
            .replace("{{rating}}", rating_str)
            .replace("{{review_count}}", review_count_str)
        )

    def _get_fallback_template(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str]
    ) -> str:
        """
        Fallback SMS template used when AI generation fails.

        Structure: Compliment reviews → name the gap → deliver value → soft question → opt-out.
        This is the research-backed formula for cold outreach (Attentive / Closeable data):
        - Leading with a review compliment proves you looked them up (+personalization)
        - Naming the gap (no website) creates a cognitive hook without being pushy
        - Soft question at the end boosts reply rates from 24% to 28%
        """
        business_name = business_data.get("name") or "Your business"
        rating = business_data.get("rating", 0)
        review_count = business_data.get("review_count", 0)
        url_display = site_url or "[link]"

        # Build the review compliment — most powerful personalization hook
        if rating and rating >= 4.0 and review_count and review_count >= 5:
            review_hook = f"Saw your {rating}⭐ Google reviews"
        elif rating and rating >= 4.0:
            review_hook = f"Saw your {rating}⭐ Google rating"
        else:
            review_hook = "Saw your Google Business listing"

        # Full version (~155 chars with a short URL)
        template = (
            f"Hi {business_name}! {review_hook} — nice work. "
            f"No website yet, so I built one: {url_display}. "
            f"Want to personalize it? Just reply NO if not for you."
        )

        if len(template) <= self.SINGLE_SEGMENT_LIMIT:
            return template

        # Short version — drop some words
        template = (
            f"Hi {business_name}! {review_hook} — built you a site: "
            f"{url_display}. Want it customized? Reply NO if not."
        )

        if len(template) <= self.SINGLE_SEGMENT_LIMIT:
            return template

        # Minimal version — truncate business name if needed
        max_name = 20
        short_name = business_name[:max_name].rsplit(" ", 1)[0] if len(business_name) > max_name else business_name
        template = (
            f"Hi {short_name}! {review_hook} — I built you a site: "
            f"{url_display}. Reply NO if not interested."
        )

        return template[:self.SINGLE_SEGMENT_LIMIT]
    
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

