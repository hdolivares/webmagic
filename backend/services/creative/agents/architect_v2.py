"""
Architect Agent - Generates website HTML/CSS/JS code
Uses delimited output format instead of JSON for reliability
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .base import BaseAgent
from ..prompts.builder import PromptBuilder
from services.creative.category_knowledge import CategoryKnowledgeService
from core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class ArchitectAgentV2(BaseAgent):
    """
    Architect agent that generates complete website code.
    Uses LLM-friendly delimited output instead of JSON.
    """
    
    def __init__(self, prompt_builder: PromptBuilder, model: str = "claude-sonnet-4-5"):
        """Initialize architect agent."""
        super().__init__(
            agent_name="architect",
            model=model,
            temperature=0.7,
            max_tokens=8192  # More tokens for code generation
        )
        self.prompt_builder = prompt_builder
    
    async def generate_website(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any],
        design_brief: Dict[str, Any],
        subdomain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete website code using delimited output format.
        
        Returns:
            {
                "html": str,
                "css": str,
                "js": str,
                "metadata": dict
            }
        """
        logger.info(f"Generating website for: {business_data.get('name')}")
        
        # STEP 1: Enhance business data with category intelligence
        enhanced_data = CategoryKnowledgeService.enhance_business_data(business_data)
        
        # STEP 2: Prepare content
        content = self._prepare_content(enhanced_data, creative_dna)
        
        # STEP 3: Prepare services data
        services_data = self._prepare_services_data(enhanced_data)
        
        # STEP 4: Build prompts
        system_prompt, user_prompt = await self.prompt_builder.build_prompts(
            agent_name="architect",
            data={
                "name": enhanced_data.get("name"),
                "category": enhanced_data.get("category"),
                "location": enhanced_data.get("location", {}),
                "phone": enhanced_data.get("phone"),
                "email": enhanced_data.get("email"),
                "rating": enhanced_data.get("rating"),
                "review_count": enhanced_data.get("review_count"),
                "reviews": enhanced_data.get("reviews_data", []),
                "hours": enhanced_data.get("hours", ""),
                "content": content,
                "design_specs": design_brief,
                "services": services_data,
                "trust_factors": enhanced_data.get("trust_factors", []),
                "value_props": enhanced_data.get("value_propositions", []),
                "process_steps": enhanced_data.get("process_steps", []),
                "contact_strategy": enhanced_data.get("contact_strategy", {}),
                "photos": len(enhanced_data.get("photos_urls", []))
            }
        )
        
        # STEP 5: Modify prompt to request delimited output
        user_prompt += """

**OUTPUT FORMAT (CRITICAL)**:
Do NOT use JSON. Instead, return your code in clearly delimited sections like this:

=== HTML ===
<!DOCTYPE html>
<html>
...your HTML code here...
</html>

=== CSS ===
/* Your CSS code here */
body {
  ...
}

=== JS ===
// Your JavaScript code here
document.addEventListener('DOMContentLoaded', () => {
  ...
});

=== METADATA ===
{
  "sections": ["hero", "about", "services", "testimonials", "contact"],
  "features": ["responsive", "seo-optimized", "fast-loading"],
  "technologies": ["HTML5", "CSS3", "Vanilla JS"]
}

This format is much more reliable than JSON-wrapped code. Use exactly these delimiters.
"""
        
        # STEP 6: Generate code using text (not JSON)
        raw_output = await self.generate(system_prompt, user_prompt, max_tokens=8192)
        
        # STEP 7: Parse delimited output using LLM-friendly parsing
        website = self._parse_delimited_output(raw_output, enhanced_data)
        
        # STEP 8: Validate
        if not website.get('html'):
            raise ValidationException("No HTML generated")
        
        logger.info(
            f"Website generated: {len(website.get('html', ''))} chars HTML, "
            f"{len(website.get('css', ''))} chars CSS, "
            f"{len(website.get('js', ''))} chars JS"
        )
        
        return website
    
    def _parse_delimited_output(
        self,
        raw_output: str,
        business_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse LLM output using clear delimiters.
        Much more reliable than JSON parsing for code.
        """
        logger.info("[architect] Parsing delimited output")
        
        result = {
            "html": "",
            "css": "",
            "js": "",
            "metadata": {}
        }
        
        try:
            # Extract HTML
            if "=== HTML ===" in raw_output:
                html_start = raw_output.find("=== HTML ===") + len("=== HTML ===")
                html_end = raw_output.find("=== CSS ===")
                if html_end == -1:
                    html_end = raw_output.find("=== METADATA ===")
                if html_end == -1:
                    html_end = len(raw_output)
                
                result["html"] = raw_output[html_start:html_end].strip()
                logger.info(f"[architect] Extracted HTML: {len(result['html'])} chars")
            
            # Extract CSS
            if "=== CSS ===" in raw_output:
                css_start = raw_output.find("=== CSS ===") + len("=== CSS ===")
                css_end = raw_output.find("=== JS ===")
                if css_end == -1:
                    css_end = raw_output.find("=== METADATA ===")
                if css_end == -1:
                    css_end = len(raw_output)
                
                result["css"] = raw_output[css_start:css_end].strip()
                logger.info(f"[architect] Extracted CSS: {len(result['css'])} chars")
            
            # Extract JS
            if "=== JS ===" in raw_output:
                js_start = raw_output.find("=== JS ===") + len("=== JS ===")
                js_end = raw_output.find("=== METADATA ===")
                if js_end == -1:
                    js_end = len(raw_output)
                
                result["js"] = raw_output[js_start:js_end].strip()
                logger.info(f"[architect] Extracted JS: {len(result['js'])} chars")
            
            # Extract metadata (this is small, JSON is OK here)
            if "=== METADATA ===" in raw_output:
                metadata_start = raw_output.find("=== METADATA ===") + len("=== METADATA ===")
                metadata_text = raw_output[metadata_start:].strip()
                
                # Try to parse JSON from metadata section
                import json
                try:
                    # Clean markdown if present
                    if "```json" in metadata_text:
                        metadata_text = metadata_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in metadata_text:
                        metadata_text = metadata_text.split("```")[1].split("```")[0].strip()
                    
                    # Find JSON object
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', metadata_text)
                    if json_match:
                        result["metadata"] = json.loads(json_match.group())
                        logger.info("[architect] Extracted metadata")
                except json.JSONDecodeError:
                    logger.warning("[architect] Could not parse metadata, using defaults")
                    result["metadata"] = {
                        "sections": ["hero", "contact"],
                        "features": ["responsive"],
                        "technologies": ["HTML5", "CSS3"]
                    }
        
        except Exception as e:
            logger.error(f"[architect] Error parsing delimited output: {str(e)}")
            
            # Save full output for debugging
            from datetime import datetime
            debug_file = Path(__file__).parent.parent.parent / "test_output" / f"debug_architect_parse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"Failed to parse delimited output\n")
                f.write(f"Error: {str(e)}\n")
                f.write(f"="*80 + "\n")
                f.write(raw_output)
            
            logger.error(f"[architect] Full output saved to: {debug_file}")
            raise
        
        # Fallback if no HTML extracted
        if not result["html"]:
            logger.warning("[architect] No HTML found in delimited output, creating fallback")
            result = self._create_simple_website(business_data)
        
        return result
    
    def _create_simple_website(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a simple but professional fallback website."""
        name = business_data.get("name", "Business")
        category = business_data.get("category", "Service")
        location = business_data.get("location", {})
        phone = business_data.get("phone", "")
        rating = business_data.get("rating", 0)
        
        city = location.get("city", "")
        state = location.get("state", "")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - Professional {category.title()} Services</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-blue-50 to-purple-50 min-h-screen flex items-center justify-center p-4">
    <div class="max-w-2xl w-full bg-white rounded-2xl shadow-2xl p-8 md:p-12">
        <div class="text-center">
            <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-4">{name}</h1>
            <p class="text-xl text-gray-600 mb-6">{category.title()} • {city}, {state}</p>
            
            {f'<div class="flex items-center justify-center mb-6"><span class="text-3xl font-bold text-yellow-500">{rating}★</span><span class="text-gray-600 ml-2">Rated by customers</span></div>' if rating > 0 else ''}
            
            {f'<p class="text-2xl text-gray-800 mb-8"><a href="tel:{phone}" class="hover:text-blue-600 transition">{phone}</a></p>' if phone else ''}
            
            <button onclick="window.location.href='tel:{phone}'" class="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-4 rounded-full text-lg font-semibold hover:shadow-lg transition transform hover:scale-105">
                Get In Touch
            </button>
        </div>
    </div>
</body>
</html>"""
        
        return {
            "html": html,
            "css": "",
            "js": "",
            "metadata": {
                "sections": ["hero"],
                "features": ["responsive", "fallback"],
                "technologies": ["HTML5", "Tailwind CSS"]
            }
        }
    
    def _prepare_content(
        self,
        business_data: Dict[str, Any],
        creative_dna: Dict[str, Any]
    ) -> Dict[str, str]:
        """Prepare content structure for website."""
        contact_strategy = business_data.get("contact_strategy", {})
        
        return {
            "headline": creative_dna.get("brand_story", f"Professional {business_data.get('category', 'services')}"),
            "subheadline": creative_dna.get("value_proposition", "Quality service you can trust"),
            "cta_primary": contact_strategy.get("primary_cta", "Get In Touch"),
            "cta_secondary": contact_strategy.get("secondary_cta", "Learn More"),
            "about": business_data.get("about_text", creative_dna.get("brand_story", "")),
            "trust_message": creative_dna.get("emotional_core", "trust")
        }
    
    def _prepare_services_data(self, business_data: Dict[str, Any]) -> list:
        """Format services for display."""
        services = business_data.get("common_services", [])
        
        return [
            {
                "name": service.get("name", ""),
                "description": service.get("description", ""),
                "icon": service.get("icon", "⚙️")
            }
            for service in services[:6]  # Limit to 6 services
        ]
