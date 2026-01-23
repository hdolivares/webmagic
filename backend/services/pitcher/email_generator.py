"""
Email template generator using AI.
Creates personalized cold emails for website pitches.
"""
from typing import Dict, Any, Optional
import logging
from anthropic import AsyncAnthropic

from core.config import get_settings
from core.exceptions import GenerationException

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailGenerator:
    """
    Generates personalized cold emails using AI.
    Creates subject lines, email bodies, and preview text.
    """
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20241022"
    
    async def generate_email(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str] = None,
        review_highlight: Optional[str] = None,
        variant: str = "default"
    ) -> Dict[str, str]:
        """
        Generate personalized cold email.
        
        Args:
            business_data: Business information
            site_url: URL to generated website
            review_highlight: Highlighted customer review
            variant: Email variant (default, direct, story, value)
            
        Returns:
            Dictionary with subject_line, email_body, preview_text
        """
        logger.info(f"Generating email for: {business_data.get('name')}")
        
        # Build system prompt
        system_prompt = self._build_system_prompt(variant)
        
        # Build user prompt
        user_prompt = self._build_user_prompt(
            business_data,
            site_url,
            review_highlight
        )
        
        try:
            # Generate email
            # Use streaming to avoid timeout limits on large max_tokens
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=64000,  # Max for Claude Sonnet 4.5
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            ) as stream:
                content = await stream.get_final_text()
            
            # Parse response
            email = self._parse_email_response(content)
            
            logger.info(f"Email generated: {email['subject_line']}")
            return email
            
        except Exception as e:
            logger.error(f"Email generation failed: {str(e)}")
            # Return fallback email
            return self._create_fallback_email(business_data, site_url)
    
    def _build_system_prompt(self, variant: str) -> str:
        """Build system prompt based on variant."""
        base_prompt = """You are an expert copywriter specializing in cold email outreach.

Your job is to write a personalized, compelling cold email to a business owner about their FREE website.

Key principles:
- Keep it SHORT (under 150 words)
- Lead with VALUE, not features
- Use their actual customer reviews when available
- Create curiosity about the website
- NO pushy sales language
- Make it feel personal and authentic
- Include a clear, low-pressure CTA

"""
        
        variant_additions = {
            "default": "Focus on helping them get found online by more customers.",
            "direct": "Be very direct and to-the-point. Busy owner friendly.",
            "story": "Lead with a customer story or review highlight.",
            "value": "Emphasize the immediate business value and ROI."
        }
        
        return base_prompt + variant_additions.get(variant, variant_additions["default"])
    
    def _build_user_prompt(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str],
        review_highlight: Optional[str]
    ) -> str:
        """Build user prompt with business context."""
        name = business_data.get("name", "the business")
        category = business_data.get("category", "business")
        city = business_data.get("city", "")
        state = business_data.get("state", "")
        rating = business_data.get("rating", 0)
        review_count = business_data.get("review_count", 0)
        
        prompt = f"""Generate a cold email for:

Business: {name}
Category: {category}
Location: {city}, {state}
Rating: {rating}★ ({review_count} reviews)
"""
        
        if review_highlight:
            prompt += f"\nCustomer Quote: \"{review_highlight}\"\n"
        
        if site_url:
            prompt += f"\nWebsite Preview: {site_url}\n"
        
        prompt += """
Output format (JSON):
{
  "subject_line": "Subject line (40-60 chars, no emojis)",
  "preview_text": "Preview text shown in inbox (80-120 chars)",
  "email_body": "Email body in plain text with \\n\\n for paragraphs"
}

Include:
1. Personalized opening (mention their rating/reviews)
2. The hook (why this matters to them)
3. Website preview link
4. Soft CTA (invite to view/claim site)

Keep it under 150 words total."""
        
        return prompt
    
    def _parse_email_response(self, content: str) -> Dict[str, str]:
        """Parse AI response into email components."""
        import json
        
        # Clean markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        try:
            data = json.loads(content)
            return {
                "subject_line": data.get("subject_line", "Your Website is Ready"),
                "email_body": data.get("email_body", ""),
                "preview_text": data.get("preview_text", "We created something for you...")
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse email JSON: {str(e)}")
            raise GenerationException(f"Invalid email format: {str(e)}")
    
    def _create_fallback_email(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str]
    ) -> Dict[str, str]:
        """Create fallback email when AI fails."""
        name = business_data.get("name", "there")
        category = business_data.get("category", "business")
        rating = business_data.get("rating", 0)
        
        subject = f"We built a website for {name}"
        preview = "Free website preview - no obligation"
        
        body = f"""Hi {name},

I noticed you're doing great work in {category}"""
        
        if rating >= 4.0:
            body += f" ({rating}★ rating!)"
        
        body += """.

I created a professional website for your business - completely free.

"""
        
        if site_url:
            body += f"Preview it here: {site_url}\n\n"
        
        body += """If you like it, you can claim it. If not, no worries at all.

Either way, hope it helps!

Best regards"""
        
        return {
            "subject_line": subject,
            "email_body": body,
            "preview_text": preview
        }
    
    async def generate_variants(
        self,
        business_data: Dict[str, Any],
        site_url: Optional[str] = None,
        review_highlight: Optional[str] = None,
        count: int = 3
    ) -> list[Dict[str, str]]:
        """
        Generate multiple email variants for A/B testing.
        
        Args:
            business_data: Business information
            site_url: Website URL
            review_highlight: Review quote
            count: Number of variants (max 4)
            
        Returns:
            List of email dictionaries
        """
        variants = ["default", "direct", "story", "value"][:count]
        emails = []
        
        for variant in variants:
            try:
                email = await self.generate_email(
                    business_data,
                    site_url,
                    review_highlight,
                    variant=variant
                )
                email["variant"] = variant
                emails.append(email)
            except Exception as e:
                logger.warning(f"Failed to generate {variant} variant: {str(e)}")
                continue
        
        return emails
