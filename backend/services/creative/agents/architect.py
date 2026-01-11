"""
Architect Agent - generates HTML/CSS/JS code for websites.
Creates responsive, animated, semantic websites based on design brief.
"""
from typing import Dict, Any, List
import logging

from services.creative.agents.base import BaseAgent
from services.creative.prompts.builder import PromptBuilder

logger = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    """
    Architect Agent: Generates complete website code.
    
    Input: Design brief + Creative DNA + business data
    Output: HTML, CSS, JS code + assets list
    """
    
    def __init__(self, prompt_builder: PromptBuilder):
        super().__init__(
            agent_name="architect",
            model="claude-3-5-sonnet-20241022",
            temperature=0.4,  # Lower temp for code generation
            max_tokens=8192  # Need more tokens for code
        )
        self.prompt_builder = prompt_builder
    
    async def generate_website(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any],
        design_brief: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate complete website code.
        
        Args:
            business_data: Original business data
            creative_dna: Output from Concept agent
            design_brief: Output from Art Director agent
                
        Returns:
            Dictionary with:
                - html: Complete HTML code
                - css: Complete CSS code (Tailwind + custom)
                - js: JavaScript code (GSAP animations)
                - assets_needed: List of assets (images, fonts)
                - meta: Meta tags and SEO data
        """
        logger.info(f"Generating website for: {business_data.get('name')}")
        
        # Prepare content
        content = self._prepare_content(business_data, creative_dna)
        
        # Prepare design specs
        design_specs = self._prepare_design_specs(design_brief)
        
        # Build prompts
        system_prompt, user_prompt = await self.prompt_builder.build_prompts(
            agent_name="architect",
            data={
                "name": business_data.get("name"),
                "category": business_data.get("category"),
                "location": f"{business_data.get('city', '')}, {business_data.get('state', '')}",
                "phone": business_data.get("phone", ""),
                "email": business_data.get("email", ""),
                "rating": business_data.get("rating", 0),
                "review_count": business_data.get("review_count", 0),
                "content": content,
                "design_specs": design_specs,
                "photos": len(business_data.get("photos_urls", []))
            }
        )
        
        # Generate code
        try:
            result = await self.generate_json(system_prompt, user_prompt)
            
            # Validate and enhance
            website = self._validate_website(result, business_data, design_brief)
            
            logger.info(
                f"Website generated: {len(website.get('html', ''))} chars HTML, "
                f"{len(website.get('css', ''))} chars CSS"
            )
            
            return website
            
        except Exception as e:
            logger.error(f"Website generation failed: {str(e)}")
            return self._create_fallback_website(
                business_data,
                creative_dna,
                design_brief
            )
    
    def _prepare_content(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any]
    ) -> Dict[str, str]:
        """Prepare content structure for website."""
        return {
            "headline": f"{business_data.get('name')} - {business_data.get('category')}",
            "tagline": creative_dna.get("value_proposition", ""),
            "about": creative_dna.get("brand_story", ""),
            "differentiators": ", ".join(creative_dna.get("personality_traits", [])),
            "cta_text": "Get In Touch",
            "contact_info": f"{business_data.get('phone', '')} | {business_data.get('email', '')}"
        }
    
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
            logger.warning("Invalid HTML, using fallback")
            return self._create_fallback_website(
                business_data, {}, design_brief
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
    
    def _create_fallback_website(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any],
        design_brief: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fallback website when AI fails."""
        name = business_data.get("name", "Business")
        category = business_data.get("category", "Business")
        city = business_data.get("city", "")
        state = business_data.get("state", "")
        phone = business_data.get("phone", "")
        email = business_data.get("email", "")
        rating = business_data.get("rating", 0)
        
        # Simple but beautiful fallback HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - {category}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Inter', sans-serif; }}</style>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen flex items-center justify-center p-8">
        <div class="max-w-2xl w-full bg-white rounded-2xl shadow-xl p-12">
            <h1 class="text-5xl font-bold text-gray-900 mb-4">{name}</h1>
            <p class="text-2xl text-gray-600 mb-8">{category} • {city}, {state}</p>
            
            {f'<div class="flex items-center mb-8"><span class="text-3xl font-bold text-yellow-500">{rating}★</span><span class="ml-2 text-gray-600">Rated by customers</span></div>' if rating else ''}
            
            <div class="space-y-4 mb-8">
                {f'<p class="text-lg"><strong>Phone:</strong> {phone}</p>' if phone else ''}
                {f'<p class="text-lg"><strong>Email:</strong> {email}</p>' if email else ''}
            </div>
            
            <button class="w-full bg-blue-600 text-white py-4 px-8 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors">
                Get In Touch
            </button>
        </div>
    </div>
</body>
</html>"""
        
        css = """:root {
  --color-primary: #2563eb;
  --color-secondary: #7c3aed;
  --color-bg: #ffffff;
  --color-text: #1f2937;
}"""
        
        js = "// Fallback website - no custom JS needed"
        
        return {
            "html": html,
            "css": css,
            "js": js,
            "assets_needed": [],
            "meta": self._generate_meta_tags(business_data),
            "_metadata": {
                "business_name": name,
                "vibe": "Simple Fallback",
                "fallback": True
            }
        }
