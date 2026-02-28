"""
Art Director Agent - creates detailed design briefs.
Selects vibe, typography, colors, animations, and visual style.

Enhanced with industry-specific color psychology recommendations based on
neuromarketing research (users form 90% of opinion based on color within 50ms).
"""
from typing import Any, Dict, List, Optional
import logging

from services.creative.agents.base import BaseAgent
from services.creative.prompts.builder import PromptBuilder
from services.creative.industry_style_service import IndustryStyleService
from services.creative.color_variation_service import ColorVariationService

logger = logging.getLogger(__name__)


class ArtDirectorAgent(BaseAgent):
    """
    Art Director Agent: Creates comprehensive design brief.
    
    Input: Creative DNA + business data
    Output: Complete design specification (vibe, typography, colors, etc.)
    """
    
    def __init__(self, prompt_builder: PromptBuilder, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_name="art_director",
            model=model,
            temperature=0.7,  # Balanced creativity and consistency
            max_tokens=64000  # Max for Claude Sonnet 4.5
        )
        self.prompt_builder = prompt_builder
    
    async def create_brief(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create comprehensive design brief.
        
        Enhanced with industry-specific color psychology recommendations.
        Research shows users form 90% of their opinion based on color within 50ms.
        
        Args:
            business_data: Original business data
            creative_dna: Output from Concept agent
                
        Returns:
            Dictionary with complete design specifications:
                - vibe: Design vibe/aesthetic
                - typography: Font selections
                - colors: Color palette
                - layout: Layout approach
                - hero: Hero section design
                - interactions: Animation/interaction patterns
                - imagery: Image treatment style
                - components: Component styling approach
                - industry_persona: The matched industry persona (if any)
        """
        logger.info(f"Creating design brief for: {business_data.get('name')}")
        
        # Get industry-specific style recommendations based on color psychology
        category = business_data.get("category", "")
        style_overrides = IndustryStyleService.get_style_overrides(category)
        gradient_practices = IndustryStyleService.get_gradient_best_practices()
        
        if style_overrides.get("has_industry_guidance"):
            logger.info(
                f"Applied industry style guidance: {style_overrides.get('persona_name')} persona "
                f"for category '{category}'"
            )
        
        # Build prompts with industry guidance
        system_prompt, user_prompt = await self.prompt_builder.build_prompts(
            agent_name="art_director",
            data={
                "name": business_data.get("name"),
                "category": business_data.get("category"),
                "personality": ", ".join(creative_dna.get("personality_traits", [])),
                "tone": creative_dna.get("tone_of_voice", ""),
                "emotion": creative_dna.get("emotional_core", ""),
                "story": creative_dna.get("brand_story", ""),
                "differentiation": creative_dna.get("differentiation_angle", ""),
                "themes": ", ".join(creative_dna.get("content_pillars", [])),
                "has_photos": len(business_data.get("photos_urls", [])) > 0,
                # NEW: Industry-specific guidance
                "industry_style_guidance": style_overrides.get("industry_guidance_text", ""),
                "gradient_best_practices": gradient_practices
            }
        )
        
        # If branding signals are present (images and/or text notes), run a
        # dedicated vision pass first and inject the derived palette into the
        # main prompt as client-specified constraints the Director must honour.
        branding_context: Optional[Dict[str, Any]] = business_data.get("branding_context")
        branding_constraints: str = ""
        if branding_context:
            try:
                interpreted = await self._interpret_branding_signals(branding_context)
                if interpreted:
                    branding_constraints = self._format_branding_constraints(interpreted)
                    user_prompt += f"\n\n{branding_constraints}"
                    logger.info(
                        "[art_director] Branding signals interpreted and injected into brief prompt"
                    )
            except Exception as branding_err:
                logger.warning(
                    "[art_director] Branding signal interpretation failed (non-fatal): %s",
                    branding_err,
                )

        # Generate design brief
        try:
            result = await self.generate_json(system_prompt, user_prompt)

            # Validate and enhance (pass style overrides for fallback colors)
            brief = self._validate_brief(result, business_data, creative_dna, style_overrides)
            
            # Add industry persona metadata
            if style_overrides.get("has_industry_guidance"):
                brief["industry_persona"] = {
                    "name": style_overrides.get("persona_name"),
                    "key": style_overrides.get("persona_key"),
                    "emotional_target": style_overrides.get("emotional_target"),
                    "cta_style": style_overrides.get("cta_style"),
                    "cta_text": style_overrides.get("cta_text")
                }
            
            # NEW: Apply color variations to prevent all businesses looking identical
            business_id = business_data.get("id", "")
            if business_id and brief.get("colors"):
                original_primary = brief["colors"].get("primary", "N/A")
                brief["colors"] = ColorVariationService.generate_variations(
                    brief["colors"],
                    business_id,
                    variation_intensity=0.15  # 15% variation
                )
                logger.info(
                    f"Applied color variation: {original_primary} → {brief['colors'].get('primary')}"
                )
            
            logger.info(
                f"Design brief created: {brief.get('vibe')} vibe, "
                f"{brief.get('typography', {}).get('display', 'N/A')} typeface"
            )
            
            return brief
            
        except Exception as e:
            logger.error(f"Design brief creation failed: {str(e)}")
            return self._create_fallback_brief(business_data, creative_dna, style_overrides)
    
    def _validate_brief(
        self,
        result: Dict[str, Any],
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any],
        style_overrides: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate and enhance design brief.
        Uses industry-specific style overrides if available.
        """
        style_overrides = style_overrides or {}
        
        # Ensure all required sections exist
        brief = {
            "vibe": result.get("vibe", style_overrides.get("vibe_recommendation", "Clean Modern")),
            "typography": result.get("typography", {}),
            "colors": result.get("colors", {}),
            "layout": result.get("layout", {}),
            "hero": result.get("hero", {}),
            "interactions": result.get("interactions", []),
            "imagery": result.get("imagery", {}),
            "components": result.get("components", {}),
            "loader": result.get("loader", {}),
            "spacing": result.get("spacing", "comfortable"),
            "border_style": result.get("border_style", "subtle"),
            "shadows": result.get("shadows", "soft")
        }
        
        # Validate typography (ensure no banned fonts, use industry fonts as fallback)
        recommended_typography = style_overrides.get("recommended_typography", {})
        brief["typography"] = self._validate_typography(
            brief["typography"],
            recommended_typography
        )
        
        # Validate colors (ensure accessibility, use industry colors as fallback)
        recommended_colors = style_overrides.get("recommended_colors", {})
        brief["colors"] = self._validate_colors(
            brief["colors"],
            recommended_colors
        )
        
        # Add CSS variables structure
        brief["css_variables"] = self._generate_css_variables(brief)
        
        # Add metadata
        brief["_metadata"] = {
            "business_name": business_data.get("name"),
            "vibe": brief["vibe"],
            "primary_font": brief["typography"].get("display"),
            "primary_color": brief["colors"].get("primary")
        }
        
        return brief
    
    def _validate_typography(
        self, 
        typography: Dict[str, Any],
        recommended: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate typography choices and ban generic fonts.
        Uses industry-recommended fonts as fallbacks if provided.
        """
        recommended = recommended or {}
        
        # Banned fonts (generic, overused)
        BANNED_FONTS = [
            "roboto", "open sans", "lato", "poppins",
            "space grotesk", "arial", "helvetica", "times new roman"
        ]
        # Note: montserrat and inter are allowed for specific industry personas
        
        # Recommended alternatives (general fallbacks)
        DISPLAY_FONTS = [
            "Clash Display", "Cabinet Grotesk", "Syne", "Satoshi",
            "General Sans", "Manrope", "Plus Jakarta Sans"
        ]
        
        MONO_FONTS = [
            "JetBrains Mono", "Space Mono", "Fira Code",
            "IBM Plex Mono"
        ]
        
        # Check and replace if needed
        display = typography.get("display", "")
        if any(banned in display.lower() for banned in BANNED_FONTS):
            logger.warning(f"Banned font detected: {display}, replacing...")
            # Use industry recommendation if available, otherwise general fallback
            typography["display"] = recommended.get("display", DISPLAY_FONTS[0])
        
        # Ensure all required fields - prefer industry recommendations
        if not typography.get("display"):
            typography["display"] = recommended.get("display", DISPLAY_FONTS[0])
        
        if not typography.get("body"):
            typography["body"] = recommended.get("body", "system-ui, -apple-system, sans-serif")
        
        if not typography.get("accent"):
            typography["accent"] = recommended.get("accent", MONO_FONTS[0])
        
        # Add font stacks
        typography["display_stack"] = f"\"{typography['display']}\", system-ui, sans-serif"
        typography["body_stack"] = typography["body"]
        typography["accent_stack"] = f"\"{typography['accent']}\", monospace"
        
        return typography
    
    def _validate_colors(
        self, 
        colors: Dict[str, Any],
        recommended: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate color palette and ensure accessibility.
        Uses industry-recommended colors as fallbacks if provided.
        
        Color psychology research shows users form 90% of their opinion
        based on color within 50ms - industry-appropriate colors matter!
        """
        recommended = recommended or {}
        
        # Ensure all required colors - prefer industry recommendations
        if not colors.get("primary"):
            colors["primary"] = recommended.get("primary", "#2563eb")
        
        if not colors.get("secondary"):
            colors["secondary"] = recommended.get("secondary", "#7c3aed")
        
        if not colors.get("accent"):
            colors["accent"] = recommended.get("accent", "#f59e0b")
        
        if not colors.get("background"):
            # Use off-white instead of pure white to prevent gradient banding
            colors["background"] = recommended.get("background", "#FAFAFA")
        
        if not colors.get("surface"):
            colors["surface"] = recommended.get("surface", "#FFFFFF")
        
        if not colors.get("text"):
            colors["text"] = recommended.get("text", "#1f2937")
        
        if not colors.get("text_muted"):
            colors["text_muted"] = recommended.get("text_muted", "#6b7280")
        
        # Gradient colors for smooth transitions (anti-banding)
        if not colors.get("gradient_start"):
            colors["gradient_start"] = recommended.get("gradient_start", colors["primary"])
        
        if not colors.get("gradient_end"):
            colors["gradient_end"] = recommended.get("gradient_end", colors["secondary"])
        
        # Add light/dark mode variants (use off-blacks to prevent banding)
        colors["background_dark"] = colors.get("background_dark", "#0a0a0f")  # Off-black
        colors["surface_dark"] = colors.get("surface_dark", "#1e293b")
        colors["text_dark"] = colors.get("text_dark", "#f1f5f9")
        colors["text_muted_dark"] = colors.get("text_muted_dark", "#94a3b8")
        
        return colors
    
    def _generate_css_variables(self, brief: Dict[str, Any]) -> Dict[str, str]:
        """Generate CSS variable definitions from brief."""
        colors = brief.get("colors", {})
        typography = brief.get("typography", {})
        
        return {
            # Colors
            "--color-primary": colors.get("primary", "#2563eb"),
            "--color-secondary": colors.get("secondary", "#7c3aed"),
            "--color-accent": colors.get("accent", "#f59e0b"),
            "--color-bg": colors.get("background", "#ffffff"),
            "--color-surface": colors.get("surface", "#f9fafb"),
            "--color-text": colors.get("text", "#1f2937"),
            "--color-text-muted": colors.get("text_muted", "#6b7280"),
            
            # Typography
            "--font-display": typography.get("display_stack", "system-ui, sans-serif"),
            "--font-body": typography.get("body_stack", "system-ui, sans-serif"),
            "--font-accent": typography.get("accent_stack", "monospace"),
            
            # Spacing (based on spacing preference)
            "--spacing-unit": "0.25rem",
            "--spacing-xs": "0.5rem",
            "--spacing-sm": "0.75rem",
            "--spacing-md": "1rem",
            "--spacing-lg": "1.5rem",
            "--spacing-xl": "2rem",
            "--spacing-2xl": "3rem",
            
            # Borders
            "--border-radius": "0.375rem" if brief.get("border_style") != "sharp" else "0",
            "--border-width": "1px",
            
            # Shadows
            "--shadow-sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
            "--shadow-md": "0 4px 6px -1px rgb(0 0 0 / 0.1)",
            "--shadow-lg": "0 10px 15px -3px rgb(0 0 0 / 0.1)",
        }
    
    def _create_fallback_brief(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any],
        style_overrides: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create fallback design brief when AI fails.
        Uses industry-specific colors and fonts if available.
        """
        style_overrides = style_overrides or {}
        recommended_colors = style_overrides.get("recommended_colors", {})
        recommended_typography = style_overrides.get("recommended_typography", {})
        
        # Use industry-specific values or defaults
        vibe = style_overrides.get("vibe_recommendation", "Clean Modern")
        display_font = recommended_typography.get("display", "Clash Display")
        body_font = recommended_typography.get("body", "system-ui, -apple-system, sans-serif")
        accent_font = recommended_typography.get("accent", "JetBrains Mono")
        
        primary_color = recommended_colors.get("primary", "#2563eb")
        secondary_color = recommended_colors.get("secondary", "#7c3aed")
        accent_color = recommended_colors.get("accent", "#f59e0b")
        background_color = recommended_colors.get("background", "#FAFAFA")  # Off-white
        
        # Build industry persona info if available
        industry_persona = None
        if style_overrides.get("has_industry_guidance"):
            industry_persona = {
                "name": style_overrides.get("persona_name"),
                "key": style_overrides.get("persona_key"),
                "emotional_target": style_overrides.get("emotional_target"),
                "cta_style": style_overrides.get("cta_style"),
                "cta_text": style_overrides.get("cta_text")
            }
        
        brief = {
            "vibe": vibe,
            "typography": {
                "display": display_font,
                "body": body_font,
                "accent": accent_font,
                "display_stack": f"\"{display_font}\", system-ui, sans-serif",
                "body_stack": body_font,
                "accent_stack": f"\"{accent_font}\", monospace"
            },
            "colors": {
                "primary": primary_color,
                "secondary": secondary_color,
                "accent": accent_color,
                "background": background_color,
                "surface": "#FFFFFF",
                "text": recommended_colors.get("text", "#1f2937"),
                "text_muted": recommended_colors.get("text_muted", "#6b7280"),
                "gradient_start": recommended_colors.get("gradient_start", primary_color),
                "gradient_end": recommended_colors.get("gradient_end", secondary_color),
                "background_dark": "#0a0a0f",  # Off-black for anti-banding
                "surface_dark": "#1e293b",
                "text_dark": "#f1f5f9",
                "text_muted_dark": "#94a3b8"
            },
            "layout": {
                "type": "single-page",
                "sections": ["hero", "about", "services", "testimonials", "contact"],
                "max_width": "1280px",
                "padding": "comfortable"
            },
            "hero": {
                "layout": "split-screen",
                "headline_style": "bold-large",
                "cta_style": "primary-button",
                "background": "gradient"
            },
            "interactions": [
                "smooth-scroll",
                "fade-in-on-scroll",
                "hover-lift"
            ],
            "imagery": {
                "treatment": style_overrides.get("imagery_style", "natural"),
                "border_radius": "medium",
                "hover_effect": "zoom"
            },
            "components": {
                "buttons": "rounded-full",
                "cards": "elevated",
                "inputs": "outlined"
            },
            "loader": {
                "type": "simple",
                "style": "spinner"
            },
            "spacing": "comfortable",
            "border_style": "rounded",
            "shadows": "soft",
            "css_variables": {},
            "_metadata": {
                "business_name": business_data.get("name"),
                "vibe": vibe,
                "primary_font": display_font,
                "primary_color": primary_color,
                "fallback": True,
                "used_industry_styling": style_overrides.get("has_industry_guidance", False)
            }
        }
        
        # Add industry persona if matched
        if industry_persona:
            brief["industry_persona"] = industry_persona

        return brief

    # ------------------------------------------------------------------
    # Branding signal interpretation (manual mode only)
    # ------------------------------------------------------------------

    _BRANDING_SYSTEM_PROMPT = """\
You are a senior brand designer with deep expertise in color theory and visual identity.
Your task is to derive a complete, harmonious color system and typography direction from
client-provided branding signals (images and/or text descriptions).

Rules:
1. Analyze every image for dominant, supporting, and accent colors — extract exact hex values.
2. Read text notes as client intent. Vague phrases like "luxury feel" or "earthy tones" are valid
   signals — translate them into a concrete palette using your design judgment.
3. Cross-reference images and text when both are present — text refines what you see.
4. Build a COMPLETE color system (all slots below must be filled — no nulls).
5. Apply color theory to fill gaps: complementary, analogous, or triadic relationships.
6. Suggest a typography direction consistent with the visual signals.

Respond with valid JSON only. No markdown, no explanation.
"""

    async def _interpret_branding_signals(
        self, branding_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Run a dedicated Claude call to derive a complete color system and
        typography direction from client-provided branding images and/or notes.

        Returns a dict with ``colors`` and ``typography`` sub-dicts, or None if
        there are no signals to interpret.
        """
        images: List[str] = branding_context.get("images", []) or []
        notes: str = (branding_context.get("notes") or "").strip()

        if not images and not notes:
            return None

        # Build multimodal content blocks
        content_blocks: List[Dict[str, Any]] = []

        for data_uri in images[:5]:  # cap at 5 images
            try:
                # data_uri format: "data:<media_type>;base64,<data>"
                header, b64_data = data_uri.split(",", 1)
                media_type = header.split(":")[1].split(";")[0]
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64_data,
                    },
                })
            except Exception as parse_err:
                logger.warning("[art_director] Could not parse branding image: %s", parse_err)

        instruction = f"""\
{"Client branding images are attached above." if content_blocks else "No images provided."}
{"Client style notes: " + notes if notes else "No text notes provided."}

Derive a complete brand color system and typography direction.
Return JSON with exactly this structure:
{{
  "colors": {{
    "primary": "#hex",
    "secondary": "#hex",
    "accent": "#hex",
    "background": "#hex",
    "surface": "#hex",
    "text": "#hex",
    "text_muted": "#hex",
    "gradient_start": "#hex",
    "gradient_end": "#hex",
    "background_dark": "#hex",
    "surface_dark": "#hex",
    "text_dark": "#hex",
    "text_muted_dark": "#hex"
  }},
  "typography": {{
    "direction": "Short description of type style, e.g. 'Modern sans-serif with editorial serif accents'",
    "display": "Suggested Google Fonts heading font name",
    "body": "Suggested Google Fonts body font name"
  }},
  "vibe": "One-word or short design vibe, e.g. 'Luxury Minimal' or 'Warm Playful'"
}}
"""
        content_blocks.append({"type": "text", "text": instruction})

        return await self.generate_json(
            self._BRANDING_SYSTEM_PROMPT,
            content_blocks,
        )

    def _format_branding_constraints(self, interpreted: Dict[str, Any]) -> str:
        """Format the interpreted branding signals as injected prompt constraints."""
        colors = interpreted.get("colors", {})
        typography = interpreted.get("typography", {})
        vibe = interpreted.get("vibe", "")

        color_lines = "\n".join(
            f"  - {slot}: {hex_val}"
            for slot, hex_val in colors.items()
            if hex_val
        )
        return f"""\
---
CLIENT BRANDING CONSTRAINTS (must be honored — these are confirmed client specifications):
Vibe: {vibe}
Typography direction: {typography.get("direction", "")}
Suggested heading font: {typography.get("display", "")}
Suggested body font: {typography.get("body", "")}
Color system:
{color_lines}

Use these values as the foundation. You may refine shades for accessibility or harmony,
but the overall palette, vibe, and typography direction must match the client's intent.
---"""
