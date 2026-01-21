"""
Art Director Agent - creates detailed design briefs.
Selects vibe, typography, colors, animations, and visual style.
"""
from typing import Dict, Any, List
import logging

from services.creative.agents.base import BaseAgent
from services.creative.prompts.builder import PromptBuilder

logger = logging.getLogger(__name__)


class ArtDirectorAgent(BaseAgent):
    """
    Art Director Agent: Creates comprehensive design brief.
    
    Input: Creative DNA + business data
    Output: Complete design specification (vibe, typography, colors, etc.)
    """
    
    def __init__(self, prompt_builder: PromptBuilder):
        super().__init__(
            agent_name="art_director",
            model="claude-3-5-sonnet-20240620",
            temperature=0.7,  # Balanced creativity and consistency
            max_tokens=4096
        )
        self.prompt_builder = prompt_builder
    
    async def create_brief(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create comprehensive design brief.
        
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
        """
        logger.info(f"Creating design brief for: {business_data.get('name')}")
        
        # Build prompts
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
                "has_photos": len(business_data.get("photos_urls", [])) > 0
            }
        )
        
        # Generate design brief
        try:
            result = await self.generate_json(system_prompt, user_prompt)
            
            # Validate and enhance
            brief = self._validate_brief(result, business_data, creative_dna)
            
            logger.info(
                f"Design brief created: {brief.get('vibe')} vibe, "
                f"{brief.get('typography', {}).get('display', 'N/A')} typeface"
            )
            
            return brief
            
        except Exception as e:
            logger.error(f"Design brief creation failed: {str(e)}")
            return self._create_fallback_brief(business_data, creative_dna)
    
    def _validate_brief(
        self,
        result: Dict[str, Any],
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and enhance design brief."""
        # Ensure all required sections exist
        brief = {
            "vibe": result.get("vibe", "Clean Modern"),
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
        
        # Validate typography (ensure no banned fonts)
        brief["typography"] = self._validate_typography(
            brief["typography"]
        )
        
        # Validate colors (ensure accessibility)
        brief["colors"] = self._validate_colors(
            brief["colors"]
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
    
    def _validate_typography(self, typography: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate typography choices and ban generic fonts.
        """
        # Banned fonts (generic, overused)
        BANNED_FONTS = [
            "roboto", "open sans", "lato", "montserrat", "poppins",
            "inter", "space grotesk", "arial", "helvetica", "times new roman"
        ]
        
        # Recommended alternatives
        DISPLAY_FONTS = [
            "Clash Display", "Cabinet Grotesk", "Syne", "Satoshi",
            "General Sans", "Manrope", "Plus Jakarta Sans"
        ]
        
        SERIF_FONTS = [
            "DM Serif Display", "Fraunces", "Playfair Display",
            "Crimson Pro", "Libre Baskerville"
        ]
        
        MONO_FONTS = [
            "JetBrains Mono", "Space Mono", "Fira Code",
            "IBM Plex Mono"
        ]
        
        # Check and replace if needed
        display = typography.get("display", "")
        if any(banned in display.lower() for banned in BANNED_FONTS):
            logger.warning(f"Banned font detected: {display}, replacing...")
            typography["display"] = DISPLAY_FONTS[0]
        
        # Ensure all required fields
        if not typography.get("display"):
            typography["display"] = DISPLAY_FONTS[0]
        
        if not typography.get("body"):
            typography["body"] = "system-ui, -apple-system, sans-serif"
        
        if not typography.get("accent"):
            typography["accent"] = MONO_FONTS[0]
        
        # Add font stacks
        typography["display_stack"] = f"\"{typography['display']}\", system-ui, sans-serif"
        typography["body_stack"] = typography["body"]
        typography["accent_stack"] = f"\"{typography['accent']}\", monospace"
        
        return typography
    
    def _validate_colors(self, colors: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate color palette and ensure accessibility.
        """
        # Ensure all required colors
        if not colors.get("primary"):
            colors["primary"] = "#2563eb"  # Default blue
        
        if not colors.get("secondary"):
            colors["secondary"] = "#7c3aed"  # Default purple
        
        if not colors.get("accent"):
            colors["accent"] = "#f59e0b"  # Default amber
        
        if not colors.get("background"):
            colors["background"] = "#ffffff"
        
        if not colors.get("surface"):
            colors["surface"] = "#f9fafb"
        
        if not colors.get("text"):
            colors["text"] = "#1f2937"
        
        if not colors.get("text_muted"):
            colors["text_muted"] = "#6b7280"
        
        # Add light/dark mode variants
        colors["background_dark"] = colors.get("background_dark", "#0f172a")
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
        creative_dna: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fallback design brief when AI fails."""
        return {
            "vibe": "Clean Modern",
            "typography": {
                "display": "Clash Display",
                "body": "system-ui, -apple-system, sans-serif",
                "accent": "JetBrains Mono",
                "display_stack": "\"Clash Display\", system-ui, sans-serif",
                "body_stack": "system-ui, -apple-system, sans-serif",
                "accent_stack": "\"JetBrains Mono\", monospace"
            },
            "colors": {
                "primary": "#2563eb",
                "secondary": "#7c3aed",
                "accent": "#f59e0b",
                "background": "#ffffff",
                "surface": "#f9fafb",
                "text": "#1f2937",
                "text_muted": "#6b7280",
                "background_dark": "#0f172a",
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
                "treatment": "natural",
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
                "vibe": "Clean Modern",
                "primary_font": "Clash Display",
                "primary_color": "#2563eb",
                "fallback": True
            }
        }
