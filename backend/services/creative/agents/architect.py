"""
Architect Agent - generates HTML/CSS/JS code for websites.
Creates responsive, animated, semantic websites based on design brief.
ALWAYS generates full, professional single-page websites - NO FALLBACKS.
"""
from typing import Dict, Any, List, Optional
import logging

from services.creative.agents.base import BaseAgent
from services.creative.prompts.builder import PromptBuilder
from services.creative.image_service import ImageGenerationService
from services.creative.category_knowledge import CategoryKnowledgeService
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ArchitectAgent(BaseAgent):
    """
    Architect Agent: Generates complete website code.
    
    Input: Design brief + Creative DNA + business data
    Output: HTML, CSS, JS code + assets list
    """
    
    def __init__(self, prompt_builder: PromptBuilder, model: str = "claude-sonnet-4-5"):
        super().__init__(
            agent_name="architect",
            model=model,
            temperature=0.4,  # Lower temp for code generation
            max_tokens=8192  # Need more tokens for code
        )
        self.prompt_builder = prompt_builder
        
        # Initialize image generation service if API key is configured
        self.image_service = None
        if settings.GEMINI_API_KEY:
            try:
                self.image_service = ImageGenerationService()
                logger.info("Image generation service initialized")
            except Exception as e:
                logger.warning(f"Image generation service not available: {e}")
    
    async def generate_website(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any],
        design_brief: Dict[str, Any],
        subdomain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete, professional single-page website.
        Uses category knowledge to intelligently fill in missing data.
        NEVER returns a fallback - always generates a full website.
        Generate complete website code with AI-generated images.
        
        Args:
            business_data: Original business data
            creative_dna: Output from Concept agent
            design_brief: Output from Art Director agent
            subdomain: Site subdomain (for saving generated images)
                
        Returns:
            Dictionary with:
                - html: Complete HTML code
                - css: Complete CSS code (Tailwind + custom)
                - js: JavaScript code (GSAP animations)
                - assets_needed: List of assets (images, fonts)
                - generated_images: List of AI-generated image paths
                - meta: Meta tags and SEO data
        """
        logger.info(f"Generating website for: {business_data.get('name')}")
        
        # STEP 1: Enhance business data with category-specific intelligence
        enhanced_data = CategoryKnowledgeService.enhance_business_data(business_data)
        logger.info(f"Enhanced with {len(enhanced_data.get('services', []))} category-specific services")
        
        # STEP 2: Prepare content
        content = self._prepare_content(enhanced_data, creative_dna)
        
        # STEP 3: Prepare design specs
        design_specs = self._prepare_design_specs(design_brief)
        
        # STEP 4: Prepare services for template
        services_data = self._prepare_services_data(enhanced_data)
        
        # STEP 5: Build prompts with enhanced data
        system_prompt, user_prompt = await self.prompt_builder.build_prompts(
            agent_name="architect",
            data={
                "name": enhanced_data.get("name"),
                "category": enhanced_data.get("category"),
                "category_display": enhanced_data.get("category_display"),
                "location": f"{enhanced_data.get('city', '')}, {enhanced_data.get('state', '')}",
                "phone": enhanced_data.get("phone", ""),
                "email": enhanced_data.get("email", ""),
                "rating": enhanced_data.get("rating", 0),
                "review_count": enhanced_data.get("review_count", 0),
                "reviews": enhanced_data.get("reviews_data", []),
                "hours": enhanced_data.get("hours", ""),
                "content": content,
                "design_specs": design_specs,
                "services": services_data,
                "trust_factors": enhanced_data.get("trust_factors", []),
                "value_props": enhanced_data.get("value_propositions", []),
                "process_steps": enhanced_data.get("process_steps", []),
                "contact_strategy": enhanced_data.get("contact_strategy", {}),
                "photos": len(enhanced_data.get("photos_urls", []))
            }
        )
        
        # STEP 6: Generate code with AI
        result = await self.generate_json(system_prompt, user_prompt)
        
        # STEP 7: Generate AI images (always, unless photos available)
        generated_images = []
        if self.image_service and subdomain:
            generated_images = await self._generate_images(
                enhanced_data,
                creative_dna,
                design_brief,
                subdomain
            )
        
        # STEP 8: Validate and enhance website code
        website = self._validate_website(result, enhanced_data, design_brief)
        
        # STEP 9: Add generated images to result
        if generated_images:
            website["generated_images"] = generated_images
            logger.info(f"Generated {len(generated_images)} AI images")
        
        logger.info(
            f"Website generated: {len(website.get('html', ''))} chars HTML, "
            f"{len(website.get('css', ''))} chars CSS"
        )
        
        return website
    
    def _prepare_content(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any]
    ) -> Dict[str, str]:
        """Prepare content structure for website."""
        contact_strategy = business_data.get("contact_strategy", {})
        
        return {
            "headline": f"{business_data.get('name')}",
            "tagline": creative_dna.get("value_proposition", ""),
            "about": business_data.get("about", creative_dna.get("brand_story", "")),
            "differentiators": ", ".join(creative_dna.get("personality_traits", [])),
            "cta_primary": contact_strategy.get("cta_primary", "Get In Touch"),
            "cta_secondary": contact_strategy.get("cta_secondary", "Learn More"),
            "contact_info": f"{business_data.get('phone', '')} | {business_data.get('email', '')}"
        }
    
    def _prepare_services_data(self, business_data: Dict[str, Any]) -> str:
        """Format services data for the prompt."""
        services = business_data.get("services", [])
        if not services:
            return "No specific services provided."
        
        formatted = []
        for service in services:
            formatted.append(
                f"- {service.get('name')}: {service.get('description')} "
                f"(Icon: {service.get('icon', '⭐')})"
            )
        
        return "\n".join(formatted)
    
    def _prepare_design_specs(self, design_brief: Dict[str, Any]) -> str:
        """Format design specs as readable string for prompt."""
        typography = design_brief.get("typography", {})
        colors = design_brief.get("colors", {})
        
        specs = f"""
VIBE: {design_brief.get('vibe', 'Clean Modern')}

TYPOGRAPHY:
- Display: {typography.get('display', 'Clash Display')}
- Body: {typography.get('body', 'system-ui')}
- Accent: {typography.get('accent', 'JetBrains Mono')}

COLORS:
- Primary: {colors.get('primary', '#2563eb')}
- Secondary: {colors.get('secondary', '#7c3aed')}
- Accent: {colors.get('accent', '#f59e0b')}
- Background: {colors.get('background', '#ffffff')}
- Text: {colors.get('text', '#1f2937')}

LAYOUT: {design_brief.get('layout', {}).get('type', 'single-page')}
HERO: {design_brief.get('hero', {}).get('layout', 'split-screen')}
INTERACTIONS: {', '.join(design_brief.get('interactions', []))}
SPACING: {design_brief.get('spacing', 'comfortable')}
"""
        return specs.strip()
    
    def _validate_website(
        self,
        result: Dict[str, Any],
        business_data: Dict[str, Any],
        design_brief: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and enhance website code."""
        # Extract code
        html = result.get("html", "")
        css = result.get("css", "")
        js = result.get("js", "")
        
        # Clean code (remove markdown if present)
        html = self._clean_code(html)
        css = self._clean_code(css)
        js = self._clean_code(js)
        
        # Validate HTML structure
        if not html or "<html" not in html.lower():
            logger.error("AI generated invalid HTML structure")
            raise ValueError(
                "Website generation failed: Invalid HTML structure generated. "
                "This should not happen with properly configured prompts."
            )
        
        # Add "Claim This Site" bar if not present
        if "claim this site" not in html.lower():
            html = self._add_claim_bar(html)
        
        # Ensure CSS variables are included
        if "--color-primary" not in css:
            css = self._add_css_variables(css, design_brief) + "\n\n" + css
        
        # Build assets list
        assets_needed = self._extract_assets(html, business_data)
        
        # Generate meta tags
        meta = self._generate_meta_tags(business_data)
        
        return {
            "html": html,
            "css": css,
            "js": js,
            "assets_needed": assets_needed,
            "meta": meta,
            "_metadata": {
                "business_name": business_data.get("name"),
                "vibe": design_brief.get("vibe"),
                "html_length": len(html),
                "css_length": len(css),
                "js_length": len(js)
            }
        }
    
    def _clean_code(self, code: str) -> str:
        """Remove markdown code blocks and clean code."""
        if not code:
            return ""
        
        # Remove markdown code blocks
        if "```html" in code:
            code = code.split("```html")[1].split("```")[0]
        elif "```css" in code:
            code = code.split("```css")[1].split("```")[0]
        elif "```javascript" in code or "```js" in code:
            parts = code.split("```")
            if len(parts) >= 3:
                code = parts[1]
                if code.startswith("javascript") or code.startswith("js"):
                    code = code.split("\n", 1)[1]
        elif "```" in code:
            parts = code.split("```")
            if len(parts) >= 3:
                code = parts[1]
        
        return code.strip()
    
    def _add_claim_bar(self, html: str) -> str:
        """Add 'Claim This Site' bar to HTML."""
        claim_bar = """
<!-- Claim This Site Bar -->
<div id="claim-bar" class="fixed bottom-0 left-0 right-0 bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-4 z-50">
    <div class="container mx-auto flex items-center justify-between">
        <p class="text-sm font-medium">
            Is this your business? Claim this site for <strong>FREE</strong>!
        </p>
        <button onclick="claimSite()" class="bg-white text-blue-600 px-4 py-2 rounded-lg font-semibold hover:bg-gray-100 transition-colors">
            Claim Now
        </button>
    </div>
</div>

<script>
function claimSite() {
    alert('Thank you for your interest! Please contact us to claim this site.');
    // TODO: Add actual claim functionality
}
</script>
"""
        
        # Insert before closing body tag
        if "</body>" in html:
            html = html.replace("</body>", claim_bar + "\n</body>")
        else:
            html += claim_bar
        
        return html
    
    def _add_css_variables(self, css: str, design_brief: Dict[str, Any]) -> str:
        """Add CSS variables to CSS."""
        variables = design_brief.get("css_variables", {})
        if not variables:
            # Generate from brief
            from services.creative.agents.director import ArtDirectorAgent
            director = ArtDirectorAgent(None)
            variables = director._generate_css_variables(design_brief)
        
        css_vars = ":root {\n"
        for var_name, value in variables.items():
            css_vars += f"  {var_name}: {value};\n"
        css_vars += "}\n"
        
        return css_vars
    
    def _extract_assets(
        self,
        html: str,
        business_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Extract needed assets from HTML."""
        assets = []
        
        # Add business photos
        photos = business_data.get("photos_urls", [])
        for i, photo_url in enumerate(photos[:5]):  # Max 5 photos
            assets.append({
                "type": "image",
                "name": f"photo-{i+1}.jpg",
                "source": photo_url,
                "usage": "hero or gallery"
            })
        
        # Add logo if available
        if business_data.get("logo_url"):
            assets.append({
                "type": "image",
                "name": "logo.png",
                "source": business_data.get("logo_url"),
                "usage": "header logo"
            })
        
        return assets
    
    def _generate_meta_tags(self, business_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate SEO meta tags."""
        name = business_data.get("name", "Business")
        category = business_data.get("category", "business")
        city = business_data.get("city", "")
        state = business_data.get("state", "")
        
        return {
            "title": f"{name} - {category} in {city}, {state}",
            "description": f"Professional {category} services by {name} in {city}, {state}. Highly rated with excellent customer reviews.",
            "keywords": f"{category}, {city}, {state}, {name}",
            "og:title": f"{name} - {category}",
            "og:description": f"Professional {category} services in {city}, {state}",
            "og:type": "business.business"
        }
    
    async def _generate_images(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any],
        design_brief: Dict[str, Any],
        subdomain: str
    ) -> List[Dict[str, str]]:
        """
        Generate AI images for the website.
        
        Args:
            business_data: Business information
            creative_dna: Brand personality and values
            design_brief: Design specifications
            subdomain: Site subdomain for saving images
            
        Returns:
            List of generated image metadata
        """
        generated_images = []
        
        try:
            # Extract color palette
            colors = design_brief.get("colors", {})
            color_palette = {
                "primary": colors.get("primary", "#2563eb"),
                "secondary": colors.get("secondary", "#7c3aed"),
                "accent": colors.get("accent", "#f59e0b")
            }
            
            # Get brand archetype (default to "Regular Guy" if not found)
            brand_archetype = creative_dna.get("brand_archetype", "Regular Guy")
            
            # 1. Generate hero image
            logger.info(f"Generating hero image for {business_data.get('name')}...")
            hero_bytes = await self.image_service.generate_hero_image(
                business_name=business_data.get("name", "Business"),
                category=business_data.get("category", "business"),
                brand_archetype=brand_archetype,
                color_palette=color_palette,
                aspect_ratio="16:9"
            )
            
            if hero_bytes:
                hero_path = await self.image_service.save_image_to_disk(
                    image_bytes=hero_bytes,
                    filename="hero.png",
                    subdomain=subdomain
                )
                generated_images.append({
                    "type": "hero",
                    "path": hero_path,
                    "filename": "hero.png",
                    "size_bytes": len(hero_bytes)
                })
                logger.info(f"✅ Hero image generated: {len(hero_bytes):,} bytes")
            
            # 2. Generate section background (optional, only if we have time)
            # This is lighter and faster
            logger.info("Generating section background...")
            bg_bytes = await self.image_service.generate_section_background(
                section_type="about",
                mood=design_brief.get("vibe", "modern").lower(),
                color_palette=color_palette,
                aspect_ratio="16:9"
            )
            
            if bg_bytes:
                bg_path = await self.image_service.save_image_to_disk(
                    image_bytes=bg_bytes,
                    filename="section-bg.png",
                    subdomain=subdomain
                )
                generated_images.append({
                    "type": "background",
                    "path": bg_path,
                    "filename": "section-bg.png",
                    "size_bytes": len(bg_bytes)
                })
                logger.info(f"✅ Background generated: {len(bg_bytes):,} bytes")
            
        except Exception as e:
            logger.error(f"Error generating images: {e}")
            # Continue without images rather than failing
        
        return generated_images
