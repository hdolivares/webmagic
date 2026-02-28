"""
Business Interpreter Agent - Stage 0 of the manual generation pipeline.

Transforms a raw free-form business description into a rich structured profile
that the downstream agents (Analyst, Art Director, Architect) can work with,
at the same quality level as if hundreds of customer reviews were available.

Hard facts (name, phone, email, address, city, state) are treated as verbatim
ground truth — the LLM never overrides or embelishes them.
"""
from typing import Any, Dict, Optional
import logging

from services.creative.agents.base import BaseAgent

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior brand strategist and business analyst. Your task is to transform
a free-form business description into a rich, structured business profile.

Rules you must follow:
1. HARD FACTS — any field explicitly marked as a hard fact is confirmed ground truth.
   Use these values EXACTLY as given in all generated content. Never paraphrase,
   shorten, or embellish them.
2. UNDERSTAND & EXPAND — read every detail in the description, then infer and enrich:
   brand personality, target audience, unique value, content themes, tone of voice,
   tagline ideas, differentiators. Think as a strategist, not a transcriptionist.
3. FILL GAPS INTELLIGENTLY — if the description doesn't mention a category, infer it
   from context. If no tone is mentioned, choose one that fits the business type.
4. STAY GROUNDED — base every inference on evidence in the description. Don't invent
   facts that contradict what was written.

Respond with a single valid JSON object. No markdown, no explanation, JSON only.
"""


def _build_user_prompt(description: str, hard_facts: Dict[str, Any]) -> str:
    facts_lines = "\n".join(
        f"  {key}: {value}"
        for key, value in hard_facts.items()
        if value
    )
    facts_section = (
        f"HARD FACTS (use verbatim — never change these):\n{facts_lines}\n\n"
        if facts_lines
        else ""
    )

    return f"""\
{facts_section}FREE-FORM DESCRIPTION:
{description}

Based on the above, produce a JSON profile with exactly these fields:
{{
  "name": "Business name (use hard fact if provided, else infer from description)",
  "category": "Primary business category (e.g. 'Pet Supplies & Home Décor')",
  "subcategory": "More specific sub-category",
  "tagline": "A compelling one-liner that captures the brand essence",
  "about": "2-3 sentence narrative about the business — engaging, third-person",
  "services": ["List", "of", "main", "products/services", "or", "offerings"],
  "owner_name": "Owner or founder name if mentioned, else null",
  "target_audience": "Who the ideal customer is — be specific",
  "brand_personality": ["adjective1", "adjective2", "adjective3", "adjective4"],
  "key_differentiators": ["What makes this business unique vs competitors"],
  "content_themes": ["Main topics/themes the website should feature"],
  "tone_of_voice": "Short description of the right communication style",
  "unique_value": "One sentence capturing the single biggest reason to choose this business"
}}
"""


class BusinessInterpreterAgent(BaseAgent):
    """
    Stage-0 agent for the manual generation pipeline.

    Converts a user's free-form business description into a structured
    `interpreted_profile` dict that replaces review-derived insights for
    the downstream agents.
    """

    def __init__(self, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_name="interpreter",
            model=model,
            temperature=0.5,
            max_tokens=4096,
        )

    async def interpret(
        self,
        description: str,
        hard_facts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Interpret a free-form description into a structured business profile.

        Args:
            description: Raw user-written description of the business.
            hard_facts: Optional dict with explicitly confirmed fields
                        (name, phone, email, address, city, state). These
                        are used verbatim and never overridden by inference.

        Returns:
            Structured `interpreted_profile` dict ready for `business_data`.
        """
        hard_facts = {k: v for k, v in (hard_facts or {}).items() if v}
        logger.info(
            "[interpreter] Interpreting description (%d chars) with %d hard facts",
            len(description),
            len(hard_facts),
        )

        user_prompt = _build_user_prompt(description, hard_facts)

        try:
            profile = await self.generate_json(_SYSTEM_PROMPT, user_prompt)
            profile = self._apply_hard_facts(profile, hard_facts)
            logger.info(
                "[interpreter] Profile created: '%s' / %s",
                profile.get("name"),
                profile.get("category"),
            )
            return profile
        except Exception as exc:
            logger.error("[interpreter] Interpretation failed: %s", exc)
            return self._fallback_profile(description, hard_facts)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply_hard_facts(
        self, profile: Dict[str, Any], hard_facts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Overwrite inferred fields with any explicitly provided hard facts."""
        field_map = {
            "name": "name",
            "phone": "phone",
            "email": "email",
            "address": "address",
            "city": "city",
            "state": "state",
        }
        for fact_key, profile_key in field_map.items():
            if hard_facts.get(fact_key):
                profile[profile_key] = hard_facts[fact_key]
        return profile

    def _fallback_profile(
        self, description: str, hard_facts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Minimal profile when the LLM call fails."""
        name = hard_facts.get("name") or description.split()[:3]
        if isinstance(name, list):
            name = " ".join(name)
        profile: Dict[str, Any] = {
            "name": name,
            "category": "Business",
            "subcategory": "",
            "tagline": f"Welcome to {name}",
            "about": description[:400],
            "services": [],
            "owner_name": None,
            "target_audience": "General public",
            "brand_personality": ["professional", "reliable", "friendly"],
            "key_differentiators": ["Dedicated service"],
            "content_themes": ["services", "about us", "contact"],
            "tone_of_voice": "Professional and approachable",
            "unique_value": f"Quality service from {name}",
        }
        profile = self._apply_hard_facts(profile, hard_facts)
        return profile
