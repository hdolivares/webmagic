"""
Enhances a user's hero image idea with the site's brand context using Claude.

Used when regenerating only the hero image with custom guidance: the user describes
their vision, and this module merges it with colors, vibe, and industry to produce
a cohesive image prompt.
"""
import logging
from typing import Any, Dict, Optional

from anthropic import AsyncAnthropic

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def enhance_hero_prompt_with_branding(
    hero_guidance: str,
    business_name: str,
    category: str,
    design_brief: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Merge the user's hero image idea with the site's branding into a single
    detailed image prompt.

    Args:
        hero_guidance: The user's description of what they want (e.g. "cozy
            interior with warm lighting and plants").
        business_name: Name of the business.
        category: Business category (e.g. "plumber", "massage therapist").
        design_brief: Site design context: colors (primary, secondary), vibe,
            industry_persona. Can be None or empty.

    Returns:
        A 2-4 sentence image prompt suitable for passing to the image generator.
    """
    brief = design_brief or {}
    colors = brief.get("colors") or {}
    primary = colors.get("primary", "")
    secondary = colors.get("secondary", "")
    vibe = brief.get("vibe", "") or brief.get("visual_identity", "")
    industry_persona = brief.get("industry_persona", "") or brief.get("value_proposition", "")

    brand_parts = []
    if primary or secondary:
        brand_parts.append(f"Brand colors: {primary or '—'}, {secondary or '—'}.")
    if vibe:
        brand_parts.append(f"Visual style/vibe: {vibe}.")
    if industry_persona:
        brand_parts.append(f"Industry positioning: {industry_persona}.")
    brand_context = " ".join(brand_parts) if brand_parts else "No specific brand constraints."

    prompt = f"""You are an image prompt specialist for a website builder. Your job is to produce a single, detailed image generation prompt for a hero banner.

The user's idea for the hero image:
"{hero_guidance.strip()}"

The website is for a business called "{business_name}" (category: {category or "general"}).
Brand context:
{brand_context}

Merge the user's vision with the brand's visual identity and industry. Produce a 2-4 sentence image prompt that:
1. Incorporates the user's core idea
2. Aligns with the brand colors, vibe, and industry
3. Describes a professional, high-quality hero image suitable for a business website (photorealistic, no text, no logos)

Output ONLY the image prompt text. No quotes, no JSON, no preamble."""

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    enhanced = response.content[0].text.strip()
    # Remove surrounding quotes if Claude added them
    if (enhanced.startswith('"') and enhanced.endswith('"')) or (
        enhanced.startswith("'") and enhanced.endswith("'")
    ):
        enhanced = enhanced[1:-1]

    logger.info(f"[HeroPromptEnhancer] Enhanced prompt for '{business_name}': {len(enhanced)} chars")
    return enhanced
