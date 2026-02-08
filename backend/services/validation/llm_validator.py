"""
LLM-Powered Website Validator.

Uses Claude to intelligently verify if a website truly belongs to a business.
Handles complex cases that regex/hardcoding cannot:
- Member directories (chambers, associations)
- Aggregator sites (MapQuest, Yelp, etc.)
- Mismatched contact information
- Generic templates vs real business sites

Design:
- Single source of truth for validation decisions
- Structured output for consistency
- Reasoning capture for debugging/improvement
- Cross-references business data with website content
"""
import logging
import json
import re
from typing import Dict, Any, Optional
from anthropic import AsyncAnthropic
from core.config import get_settings

logger = logging.getLogger(__name__)


class LLMWebsiteValidator:
    """
    Uses Claude to validate if a website belongs to a business.
    
    This is the intelligence layer that makes the final validation decision
    by analyzing website content against business information.
    """
    
    # Master prompt template
    VALIDATION_PROMPT = """You are an expert website validation specialist. Your job is to determine if a website truly belongs to a specific business.

BUSINESS INFORMATION:
- Name: {business_name}
- Phone: {business_phone}
- Email: {business_email}
- Address: {business_address}
- City: {business_city}, State: {business_state}
- Country: {business_country}

WEBSITE INFORMATION:
- URL: {website_url}
- Final URL (after redirects): {final_url}
- Title: {website_title}
- Meta Description: {website_description}
- Phones found: {website_phones}
- Emails found: {website_emails}
- Has address: {has_address}
- Has business hours: {has_hours}
- Content preview (first 500 chars): {content_preview}
- Word count: {word_count}

INVALID WEBSITE TYPES (mark as "missing" - business needs a real website):

1. MEMBER DIRECTORIES & LISTINGS:
   - Chamber of Commerce member pages (e.g., cantonchamber.org/members/business)
   - Better Business Bureau profiles
   - Trade association member directories
   - Industry group listings
   - Local business association pages
   
2. AGGREGATOR & REVIEW SITES:
   - Yelp, Yellow Pages, White Pages
   - Google Maps/Business profiles
   - MapQuest business listings
   - Angi, HomeAdvisor, Thumbtack
   - TripAdvisor, Foursquare
   - Nextdoor business pages
   
3. SOCIAL MEDIA PROFILES:
   - Facebook pages
   - LinkedIn company pages
   - Instagram profiles
   - Twitter/X accounts
   
4. PLACEHOLDER/UNRELATED:
   - "Under construction" pages
   - "Coming soon" pages
   - Domain parking pages
   - Completely unrelated businesses
   - Generic landing pages
   
5. ALREADY DETECTED BY PRESCREENER:
   - PDFs, documents, files
   - File storage links
   - Shortened URLs

CROSS-REFERENCE RULES:
✅ STRONG MATCH SIGNALS:
- Phone number matches exactly or partially (same area code + first 6 digits)
- Business name appears prominently in title or main content
- Address street name or zip code matches
- Multiple contact methods match (phone + email, phone + address)

⚠️ WEAK SIGNALS:
- Business name in URL domain
- Generic services match ("plumbing", "heating")
- Same city/state (not enough alone)

❌ MISMATCH SIGNALS:
- Phone numbers are completely different
- Business name doesn't appear anywhere
- Wrong city/state mentioned prominently
- Website clearly belongs to different business

VALIDATION DECISION:
Respond ONLY with valid JSON in this exact format:
{{
  "verdict": "valid" | "invalid" | "missing",
  "confidence": 0.0-1.0,
  "reasoning": "Concise explanation of your decision (2-3 sentences)",
  "recommendation": "keep_url" | "clear_url_and_mark_missing" | "mark_invalid_keep_url",
  "match_signals": {{
    "phone_match": true/false,
    "address_match": true/false,
    "name_match": true/false,
    "is_directory": true/false,
    "is_aggregator": true/false
  }}
}}

VERDICT DEFINITIONS:
- "valid": This IS the business's actual website (even if low quality)
- "invalid": This IS their website but broken/placeholder (keep URL for records)
- "missing": NOT their website (directory/aggregator/unrelated) - clear URL

EXAMPLES:

Example 1 - Member Directory:
Business: DX Plumbing, Canton, OH
URL: business.cantonchamber.org/member/dx-plumbing
Result: {{"verdict": "missing", "confidence": 0.95, "reasoning": "This is a Canton Chamber of Commerce member directory listing, not the business's actual website. The business needs its own domain.", "recommendation": "clear_url_and_mark_missing", "match_signals": {{"phone_match": false, "address_match": false, "name_match": true, "is_directory": true, "is_aggregator": false}}}}

Example 2 - MapQuest Aggregator:
Business: Brian's Plumbing, Kansas
URL: mapquest.com/us/kansas/brians-plumbing-456601382
Result: {{"verdict": "missing", "confidence": 1.0, "reasoning": "MapQuest business listing page, not the company's website. This is an aggregator directory.", "recommendation": "clear_url_and_mark_missing", "match_signals": {{"phone_match": false, "address_match": false, "name_match": true, "is_directory": false, "is_aggregator": true}}}}

Example 3 - Valid Website with Phone Match:
Business: Ray Miller Plumbing, Phone: (555) 123-4567
URL: raymillerplumbinginc.com, Phones found: ["555-123-4567"]
Result: {{"verdict": "valid", "confidence": 0.98, "reasoning": "Business name matches title, phone number matches exactly. This is clearly their official website.", "recommendation": "keep_url", "match_signals": {{"phone_match": true, "address_match": false, "name_match": true, "is_directory": false, "is_aggregator": false}}}}

Example 4 - Unrelated Business:
Business: Smith Plumbing, Austin TX
URL: johnsplumbing.com with different phone/address
Result: {{"verdict": "missing", "confidence": 0.90, "reasoning": "Website is for 'Johnson Plumbing' with different contact info. This is not Smith Plumbing's website.", "recommendation": "clear_url_and_mark_missing", "match_signals": {{"phone_match": false, "address_match": false, "name_match": false, "is_directory": false, "is_aggregator": false}}}}

Now analyze the provided business and website information above and return your validation decision."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM validator.
        
        Args:
            api_key: Anthropic API key (defaults to settings)
        """
        settings = get_settings()
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-3-sonnet-20240229"  # Claude 3 Sonnet (fallback if 3.5 not available)
    
    async def validate_website_match(
        self,
        business: Dict[str, Any],
        website_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to validate if website belongs to business.
        
        Args:
            business: {name, phone, email, address, city, state, country}
            website_data: {url, final_url, title, phones, emails, content_preview, ...}
            
        Returns:
            {
                "verdict": "valid" | "invalid" | "missing",
                "confidence": 0.0-1.0,
                "reasoning": str,
                "recommendation": str,
                "match_signals": dict,
                "llm_model": str,
                "llm_tokens": int
            }
        """
        try:
            # Format prompt with business and website data
            prompt = self._format_prompt(business, website_data)
            
            logger.info(f"LLM validation for: {business.get('name')} - {website_data.get('url')}")
            
            # Call Claude
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0,  # Deterministic for validation
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract response
            response_text = response.content[0].text
            
            # Parse JSON response
            result = self._parse_llm_response(response_text)
            
            # Add metadata
            result["llm_model"] = self.model
            result["llm_tokens"] = response.usage.input_tokens + response.usage.output_tokens
            result["llm_raw_response"] = response_text
            
            logger.info(
                f"LLM verdict: {result['verdict']} "
                f"(confidence={result['confidence']:.2f}) - "
                f"{result['reasoning'][:100]}"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}")
            return self._fallback_result(
                "error",
                f"LLM response parsing error: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"LLM validation failed: {e}", exc_info=True)
            return self._fallback_result(
                "error",
                f"LLM validation error: {str(e)}"
            )
    
    def _format_prompt(
        self,
        business: Dict[str, Any],
        website_data: Dict[str, Any]
    ) -> str:
        """Format the validation prompt with business and website data."""
        return self.VALIDATION_PROMPT.format(
            # Business data
            business_name=business.get("name", "Unknown"),
            business_phone=business.get("phone", "Not provided"),
            business_email=business.get("email", "Not provided"),
            business_address=business.get("address", "Not provided"),
            business_city=business.get("city", "Unknown"),
            business_state=business.get("state", "Unknown"),
            business_country=business.get("country", "US"),
            
            # Website data
            website_url=website_data.get("url", "Unknown"),
            final_url=website_data.get("final_url", website_data.get("url", "Unknown")),
            website_title=website_data.get("title", "No title"),
            website_description=website_data.get("meta_description", "No description"),
            website_phones=", ".join(website_data.get("phones", [])) or "None found",
            website_emails=", ".join(website_data.get("emails", [])) or "None found",
            has_address=website_data.get("has_address", False),
            has_hours=website_data.get("has_hours", False),
            content_preview=website_data.get("content_preview", "")[:500],
            word_count=website_data.get("word_count", 0),
        )
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LLM response and validate structure.
        
        Handles cases where LLM includes explanation before/after JSON.
        """
        # Try to find JSON in response
        # LLM might wrap in markdown code blocks or add explanation
        response_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])  # Remove first and last line
            response_text = response_text.strip()
        
        # Try to extract JSON if there's extra text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate required fields
        required_fields = ["verdict", "confidence", "reasoning", "recommendation"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate verdict values
        if result["verdict"] not in ["valid", "invalid", "missing"]:
            raise ValueError(f"Invalid verdict: {result['verdict']}")
        
        # Validate confidence range
        if not 0 <= result["confidence"] <= 1:
            result["confidence"] = max(0, min(1, result["confidence"]))
        
        return result
    
    def _fallback_result(self, verdict: str, reason: str) -> Dict[str, Any]:
        """Return a fallback result when LLM validation fails."""
        return {
            "verdict": verdict,
            "confidence": 0.5,
            "reasoning": reason,
            "recommendation": "mark_invalid_keep_url",
            "match_signals": {
                "phone_match": False,
                "address_match": False,
                "name_match": False,
                "is_directory": False,
                "is_aggregator": False
            },
            "llm_model": "fallback",
            "llm_tokens": 0,
            "llm_raw_response": None
        }
