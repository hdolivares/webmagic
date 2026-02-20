"""
Architect Agent - Generates website HTML/CSS/JS code
Uses delimited output format instead of JSON for reliability
"""
import logging
import re
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

from .base import BaseAgent
from ..prompts.builder import PromptBuilder
from services.creative.category_knowledge import CategoryKnowledgeService
from core.exceptions import ValidationException
from core.config import get_settings

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
            max_tokens=64000  # Max for Claude Sonnet 4.5
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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="...">
    <title>...</title>
    <!-- Google Fonts (preconnect + font link with &display=swap) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=...&display=swap" rel="stylesheet">
    <!-- NO Tailwind CDN. NO external CSS frameworks. All styles go in styles.css -->
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    ...semantic HTML5 here (nav, main, section, article, footer)...
    <script src="script.js"></script>
</body>
</html>

=== CSS ===
/* ALL styles go here — this is the ONLY stylesheet. No Tailwind. No frameworks. */
/* Every brand color, font, and spacing value MUST be a CSS variable in :root */
:root {
  --color-primary: #1e40af;
  --color-secondary: #7c3aed;
  --color-accent: #fbbf24;
  --color-bg: #FAFAFA;
  --color-surface: #ffffff;
  --color-text: #1f2937;
  --color-text-muted: #6b7280;
  --font-heading: 'YourHeadingFont', serif;
  --font-body: 'YourBodyFont', sans-serif;
  --spacing-sm: 0.75rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 3rem;
  --border-radius: 0.5rem;
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
  --transition: all 0.3s ease;
}
/* Then all other CSS using var(--...) throughout */

=== JS ===
// Your JavaScript code here - will be saved as script.js
document.addEventListener('DOMContentLoaded', () => {
  ...
});

=== METADATA ===
{
  "sections": ["hero", "about", "services", "testimonials", "contact"],
  "features": ["responsive", "seo-optimized", "fast-loading"],
  "technologies": ["HTML5", "CSS3", "Vanilla JS"]
}

**CRITICAL CSS RULES** (violations will break the site editor):
1. ALL CSS goes in the === CSS === section — styles.css is the ONLY stylesheet
2. NEVER include Tailwind CDN, Bootstrap, or any CSS framework `<script>` or `<link>` in HTML
3. EVERY color, font, and brand value MUST be a CSS variable in `:root { }` — use var(--...) everywhere
4. NEVER use hardcoded hex colors like `color: #1e40af` outside of `:root` — always reference variables
5. Use SEMANTIC HTML class names (.hero, .nav-link, .service-card) — NEVER Tailwind utility classes
6. COLOR CONTRAST IS MANDATORY — every text element MUST have a contrast ratio of at least 4.5:1 against its background (WCAG AA). Never place gray, light, or muted text on a dark or colored background without verifying readability. On dark/colored sections (hero, banners, footers), always set text to #ffffff or a near-white color explicitly — do NOT rely on inheritance.
7. HERO BUTTONS — the secondary/outline button in the hero section MUST use white text and a white/semi-transparent border, never the primary color. The hero has a dark or saturated background, so `color: var(--color-primary)` makes an invisible button. Always define `.hero .btn-secondary` (or a dedicated `.btn-outline-light` class) with `color: rgba(255,255,255,0.9)`, `border-color: rgba(255,255,255,0.6)`, and `background: rgba(255,255,255,0.08)`. On hover: `background: rgba(255,255,255,0.18)`, `color: #ffffff`, `border-color: white`. NEVER put a dark-colored outline button on a dark or colored hero background.

**IMPORTANT**:
1. The HTML MUST include `<link rel="stylesheet" href="styles.css">` in the <head>
2. The HTML MUST include `<script src="script.js"></script>` before </body>
3. Use exactly these delimiters: === HTML ===, === CSS ===, === JS ===, === METADATA ===
"""
        
        # STEP 6: Generate code using text (not JSON)
        raw_output = await self.generate(system_prompt, user_prompt, max_tokens=64000)
        
        # STEP 7: Parse delimited output using LLM-friendly parsing
        website = self._parse_delimited_output(raw_output, enhanced_data)
        
        # STEP 8: Post-process — enforce CSS variables, strip Tailwind CDN, inject SEO head
        slug = enhanced_data.get("slug") or self._generate_slug(enhanced_data.get("name", ""))
        website["css"] = self._enforce_css_variables(website.get("css", ""), design_brief)
        website["html"] = self._strip_external_css_frameworks(website.get("html", ""))
        website["html"] = self._inject_seo_head(website.get("html", ""), enhanced_data, slug)
        
        # STEP 9: Inject proper claim bar with checkout link
        website["html"] = self._inject_claim_bar(website.get("html", ""), slug)
        website["css"] = self._add_claim_bar_css(website.get("css", ""))
        website["js"] = self._add_claim_bar_js(website.get("js", ""), slug)
        
        # STEP 10: Extract generation context for edit pipeline
        website["generation_context"] = self._extract_generation_context(
            css=website.get("css", ""),
            metadata=website.get("metadata", {}),
            design_brief=design_brief,
        )
        
        # STEP 11: Validate
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
    
    # ── Post-processing guards ────────────────────────────────────────────────

    def _enforce_css_variables(self, css: str, design_brief: Dict[str, Any]) -> str:
        """
        Ensure the stylesheet has a :root {} block with CSS variables.
        If the LLM omitted it, inject one built from the design brief.
        """
        if not css.strip():
            css = ""

        if "--color-primary" not in css:
            logger.warning("[architect] CSS variables missing — injecting from design_brief")
            root_block = self._build_root_block(design_brief)
            css = root_block + "\n" + css

        return css

    def _build_root_block(self, design_brief: Dict[str, Any]) -> str:
        """Build a :root { } block from design_brief color palette and typography."""
        palette = design_brief.get("color_palette", {})
        typography = design_brief.get("typography", {})

        primary = palette.get("primary", "#1e40af")
        secondary = palette.get("secondary", "#7c3aed")
        accent = palette.get("accent", "#fbbf24")
        bg = palette.get("background", "#fafafa")
        text = palette.get("text", "#1f2937")

        heading_font = typography.get("heading_font", "Georgia, serif")
        body_font = typography.get("body_font", "system-ui, sans-serif")

        return f""":root {{
  --color-primary: {primary};
  --color-secondary: {secondary};
  --color-accent: {accent};
  --color-bg: {bg};
  --color-surface: #ffffff;
  --color-text: {text};
  --color-text-muted: #6b7280;
  --font-heading: {heading_font};
  --font-body: {body_font};
  --spacing-sm: 0.75rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 3rem;
  --border-radius: 0.5rem;
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
  --transition: all 0.3s ease;
}}"""

    def _strip_external_css_frameworks(self, html: str) -> str:
        """
        Remove Tailwind CDN and any other runtime CSS framework scripts/links.
        Sites must be fully self-contained via styles.css.
        """
        # Remove Tailwind CDN <script> tags
        html = re.sub(
            r'<script[^>]+cdn\.tailwindcss\.com[^>]*>.*?</script>',
            '',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        html = re.sub(
            r'<script[^>]+cdn\.tailwindcss\.com[^>]*/?>',
            '',
            html,
            flags=re.IGNORECASE,
        )
        # Remove Bootstrap CDN links
        html = re.sub(
            r'<link[^>]+bootstrapcdn[^>]*/?>',
            '',
            html,
            flags=re.IGNORECASE,
        )
        return html

    def _inject_seo_head(self, html: str, business_data: Dict[str, Any], slug: str) -> str:
        """
        Programmatically inject canonical URL, Open Graph, Twitter Card, JSON-LD
        LocalBusiness schema, favicon, robots meta, and theme-color into <head>.
        Uses business_data so tags are always correct and never hallucinated.
        """
        settings = get_settings()
        site_url = f"{settings.SITES_BASE_URL}/{slug}"

        name = business_data.get("name", "")
        category = business_data.get("category", "")
        location = business_data.get("location", {})
        city = location.get("city", "")
        state = location.get("state", "")
        phone = business_data.get("phone", "")
        rating = business_data.get("rating", "")
        review_count = business_data.get("review_count", "")
        hours = business_data.get("hours", "")

        meta_description = (
            f"Professional {category} services in {city}, {state}. "
            f"Trusted by customers with a {rating}★ rating. Call {phone}."
        ).strip(". ")

        # Build JSON-LD schema
        schema: Dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": name,
            "description": meta_description,
            "url": site_url,
            "telephone": phone,
            "address": {
                "@type": "PostalAddress",
                "addressLocality": city,
                "addressRegion": state,
                "addressCountry": "US",
            },
        }
        if hours:
            schema["openingHours"] = hours
        if rating and review_count:
            try:
                schema["aggregateRating"] = {
                    "@type": "AggregateRating",
                    "ratingValue": str(rating),
                    "reviewCount": str(review_count),
                }
            except Exception:
                pass

        schema_json = json.dumps(schema, ensure_ascii=False, indent=2)

        # Detect primary color from existing CSS variable comment or fall back
        primary_color = "#6366f1"
        primary_match = re.search(r'--color-primary\s*:\s*([^;]+);', html)
        if not primary_match:
            # html may not have CSS; look for it separately via a flag
            primary_color = "#6366f1"
        else:
            primary_color = primary_match.group(1).strip()

        seo_tags = f"""
    <!-- SEO: Canonical -->
    <link rel="canonical" href="{site_url}">

    <!-- SEO: Favicon -->
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">

    <!-- SEO: Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{site_url}">
    <meta property="og:title" content="{name}">
    <meta property="og:description" content="{meta_description}">
    <meta property="og:site_name" content="{name}">

    <!-- SEO: Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{name}">
    <meta name="twitter:description" content="{meta_description}">

    <!-- SEO: Mobile / Robots -->
    <meta name="theme-color" content="{primary_color}">
    <meta name="robots" content="index, follow">

    <!-- SEO: JSON-LD LocalBusiness -->
    <script type="application/ld+json">
{schema_json}
    </script>"""

        # Insert just before </head>
        if "</head>" in html:
            head_close = html.find("</head>")
            html = html[:head_close] + seo_tags + "\n" + html[head_close:]
        elif "<body" in html:
            body_pos = html.find("<body")
            html = html[:body_pos] + seo_tags + "\n" + html[body_pos:]

        return html

    def _extract_generation_context(
        self,
        css: str,
        metadata: Dict[str, Any],
        design_brief: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract structured metadata about the generated site for the edit pipeline.
        Stored in SiteVersion.generation_context as JSONB.
        """
        css_variables: Dict[str, str] = {}
        root_match = re.search(r':root\s*\{([^}]+)\}', css)
        if root_match:
            for line in root_match.group(1).splitlines():
                line = line.strip()
                if line.startswith('--') and ':' in line:
                    name, _, value = line.partition(':')
                    css_variables[name.strip()] = value.strip().rstrip(';')

        return {
            "sections": metadata.get("sections", []),
            "features": metadata.get("features", []),
            "css_variables": css_variables,
            "design_brief_summary": {
                "brand_personality": design_brief.get("brand_personality", ""),
                "color_palette": design_brief.get("color_palette", {}),
                "typography": design_brief.get("typography", {}),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "architect_version": "v2",
        }

    # ── Simple fallback website ───────────────────────────────────────────────

    def _create_simple_website(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a simple but professional fallback website."""
        name = business_data.get("name", "Business")
        category = business_data.get("category", "Service")
        location = business_data.get("location", {})
        phone = business_data.get("phone", "")
        rating = business_data.get("rating", 0)
        
        city = location.get("city", "")
        state = location.get("state", "")
        
        fallback_css = f""":root {{
  --color-primary: #1e40af;
  --color-secondary: #7c3aed;
  --color-accent: #fbbf24;
  --color-bg: #f0f4ff;
  --color-surface: #ffffff;
  --color-text: #1f2937;
  --color-text-muted: #6b7280;
  --font-heading: Georgia, serif;
  --font-body: system-ui, sans-serif;
  --border-radius: 1rem;
  --shadow-md: 0 4px 24px rgba(0,0,0,0.12);
}}
*, *::before, *::after {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 0;
  font-family: var(--font-body);
  background: var(--color-bg);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}}
.card {{
  background: var(--color-surface);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-md);
  max-width: 40rem;
  width: 100%;
  padding: 3rem 2rem;
  text-align: center;
}}
h1 {{ margin: 0 0 0.5rem; font-family: var(--font-heading); font-size: 2.5rem; color: var(--color-text); }}
.subtitle {{ font-size: 1.1rem; color: var(--color-text-muted); margin: 0 0 1.5rem; }}
.rating {{ font-size: 1.75rem; color: var(--color-accent); font-weight: 700; margin-bottom: 1.5rem; }}
.phone {{ font-size: 1.4rem; color: var(--color-text); margin: 0 0 2rem; }}
.phone a {{ color: inherit; text-decoration: none; }}
.btn {{
  display: inline-block;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  color: #fff;
  border: none;
  padding: 1rem 2rem;
  border-radius: 2rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition, all 0.3s ease);
  text-decoration: none;
}}
.btn:hover {{ opacity: 0.9; transform: scale(1.03); }}"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - Professional {category.title()} Services</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="card">
        <h1>{name}</h1>
        <p class="subtitle">{category.title()} &bull; {city}, {state}</p>
        {f'<p class="rating">{rating}★ Rated by customers</p>' if rating and float(rating) > 0 else ''}
        {f'<p class="phone"><a href="tel:{phone}">{phone}</a></p>' if phone else ''}
        <a href="tel:{phone}" class="btn">Get In Touch</a>
    </div>
    <script src="script.js"></script>
</body>
</html>"""

        return {
            "html": html,
            "css": fallback_css,
            "js": "",
            "metadata": {
                "sections": ["hero"],
                "features": ["responsive", "fallback"],
                "technologies": ["HTML5", "CSS3"],
            },
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
    
    def _generate_slug(self, name: str) -> str:
        """Generate a URL-safe slug from business name."""
        import re
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s_-]+', '-', slug)
        slug = slug.strip('-')
        return slug[:50] if slug else "my-business"
    
    def _inject_claim_bar(self, html: str, slug: str) -> str:
        """
        Inject the proper claim bar with correct pricing and checkout link.
        Removes any LLM-generated claim bars and adds the official one.
        """
        import re
        
        # Remove any existing claim bars (various patterns the LLM might generate)
        patterns_to_remove = [
            r'<div[^>]*id=["\']?claim[^>]*>.*?</div>',
            r'<div[^>]*class=["\'][^"\']*claim[^"\']*["\'][^>]*>.*?</div>',
            r'<!--\s*Claim.*?-->.*?(?=<(?:footer|section|div|script|/body))',
            r'<div[^>]*>.*?(?:claim|free|FREE).*?(?:website|site).*?</div>',
        ]
        
        for pattern in patterns_to_remove:
            html = re.sub(pattern, '', html, flags=re.IGNORECASE | re.DOTALL)
        
        # Also remove the claimSite function if present
        html = re.sub(
            r'<script[^>]*>.*?function\s+claimSite.*?</script>',
            '',
            html,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # Build the official claim bar HTML
        api_url = get_settings().API_URL
        checkout_url = f"{api_url}/api/v1/sites/{slug}/purchase"
        
        claim_bar_html = f'''
<!-- WebMagic Claim Bar - Official -->
<div id="webmagic-claim-bar" style="position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999; all: initial; display: block;">
    <div style="all: unset; display: flex; background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%); padding: 12px 20px; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; box-shadow: 0 -4px 20px rgba(0,0,0,0.25);">
        <div style="all: unset; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
            <span style="all: unset; font-size: 20px; line-height: 1;">🏢</span>
            <div style="all: unset; display: block;">
                <p style="all: unset; display: block; margin: 0; font-weight: 700; font-size: 15px; color: #ffffff !important; text-shadow: 0 1px 3px rgba(0,0,0,0.4); font-family: system-ui, sans-serif; line-height: 1.4;">Is this your business?</p>
                <p style="all: unset; display: block; margin: 0; font-size: 13px; color: #e0e7ff !important; text-shadow: 0 1px 2px rgba(0,0,0,0.3); font-family: system-ui, sans-serif; line-height: 1.4;">Claim this website for only <strong style="color: #ffffff !important; font-weight: 700;">$497</strong> · Then just $97/month for hosting, maintenance &amp; updates</p>
                <a href="https://web.lavish.solutions/how-it-works" target="_blank" rel="noopener noreferrer" style="all: unset; display: inline-block; color: #bfdbfe !important; font-size: 12px; text-decoration: underline; margin-top: 3px; font-family: system-ui, sans-serif; cursor: pointer;">See what&#39;s included →</a>
            </div>
        </div>
        <button id="webmagic-claim-btn" style="all: unset; display: inline-block; background: #fbbf24; color: #1e3a5f !important; border: none; padding: 12px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; cursor: pointer; transition: all 0.2s; text-transform: uppercase; letter-spacing: 0.5px; font-family: system-ui, sans-serif; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
            Claim for $497
        </button>
    </div>
</div>
'''
        
        # Insert before closing body tag
        if "</body>" in html.lower():
            # Find the position case-insensitively
            body_pos = html.lower().rfind("</body>")
            html = html[:body_pos] + claim_bar_html + "\n" + html[body_pos:]
        else:
            html += claim_bar_html
        
        return html
    
    def _add_claim_bar_css(self, css: str) -> str:
        """Add claim bar hover styles."""
        claim_css = '''
/* WebMagic Claim Bar Styles */
#webmagic-claim-bar button:hover {
    transform: scale(1.05);
    background: #f59e0b !important;
}

@media (max-width: 640px) {
    #webmagic-claim-bar > div {
        flex-direction: column;
        text-align: center;
        padding: 16px !important;
    }
    #webmagic-claim-bar button {
        width: 100%;
    }
}
'''
        return css + "\n" + claim_css
    
    def _add_claim_bar_js(self, js: str, slug: str) -> str:
        """Add claim bar click handler."""
        api_url = get_settings().API_URL
        
        claim_js = f'''
// WebMagic Claim Bar Handler
(function() {{
    const claimBtn = document.getElementById('webmagic-claim-btn');
    if (claimBtn) {{
        claimBtn.addEventListener('click', function() {{
            // Open claim modal
            const modal = document.createElement('div');
            modal.id = 'webmagic-claim-modal';
            modal.innerHTML = `
                <div style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 10000; padding: 20px;">
                    <div style="background: white; border-radius: 16px; max-width: 480px; width: 100%; padding: 32px; position: relative; box-shadow: 0 25px 50px rgba(0,0,0,0.25);">
                        <button onclick="this.closest('#webmagic-claim-modal').remove()" style="position: absolute; top: 16px; right: 16px; background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">×</button>
                        <h2 style="margin: 0 0 8px; font-size: 24px; color: #1e3a5f;">Claim This Website</h2>
                        <p style="color: #64748b; margin: 0 0 24px; font-size: 15px;">Get your professional website today!</p>
                        
                        <div style="background: #f8fafc; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                                <span style="color: #475569;">One-time setup fee</span>
                                <span style="font-weight: 700; color: #1e3a5f;">$497</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid #e2e8f0;">
                                <span style="color: #475569;">Hosting, Maintenance & Updates</span>
                                <span style="font-weight: 700; color: #1e3a5f;">$97/mo</span>
                            </div>
                        </div>
                        
                        <p style="font-size: 13px; color: #64748b; margin: 0 0 20px;">
                            ✓ Premium custom website design & development<br>
                            ✓ Monthly content & image updates<br>
                            ✓ Fast, secure hosting included<br>
                            ✓ SEO optimization included<br>
                            ✓ Cancel anytime
                        </p>
                        
                        <form id="webmagic-claim-form" style="display: flex; flex-direction: column; gap: 12px;">
                            <input type="email" id="claim-email" placeholder="Your email address *" required style="padding: 14px 16px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 15px; outline: none; transition: border-color 0.2s;" onfocus="this.style.borderColor='#7c3aed'" onblur="this.style.borderColor='#e2e8f0'">
                            <input type="text" id="claim-name" placeholder="Your full name *" required style="padding: 14px 16px; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 15px; outline: none; transition: border-color 0.2s;" onfocus="this.style.borderColor='#7c3aed'" onblur="this.style.borderColor='#e2e8f0'">
                            <button type="submit" style="background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%); color: white; border: none; padding: 16px; border-radius: 8px; font-weight: 700; font-size: 16px; cursor: pointer; transition: transform 0.2s, opacity 0.2s;" onmouseover="this.style.opacity='0.9'" onmouseout="this.style.opacity='1'">
                                Proceed to Checkout →
                            </button>
                        </form>
                        
                        <p style="text-align: center; font-size: 12px; color: #94a3b8; margin: 16px 0 0;">
                            Secure payment powered by Recurrente
                        </p>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            // Handle form submission
            document.getElementById('webmagic-claim-form').addEventListener('submit', async function(e) {{
                e.preventDefault();
                const email = document.getElementById('claim-email').value;
                const name = document.getElementById('claim-name').value;
                const btn = this.querySelector('button[type="submit"]');
                const originalText = btn.textContent;
                btn.textContent = 'Processing...';
                btn.disabled = true;
                
                // Validate name is not empty
                if (!name || name.trim().length === 0) {{
                    alert('Please enter your full name');
                    btn.textContent = originalText;
                    btn.disabled = false;
                    return;
                }}
                
                try {{
                    const response = await fetch('{api_url}/api/v1/sites/{slug}/purchase', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            customer_email: email,
                            customer_name: name,
                            success_url: window.location.href + '?purchased=true',
                            cancel_url: window.location.href
                        }})
                    }});
                    
                    if (response.ok) {{
                        const data = await response.json();
                        window.location.href = data.checkout_url;
                    }} else {{
                        const error = await response.json();
                        alert(error.detail || 'Something went wrong. Please try again.');
                        btn.textContent = originalText;
                        btn.disabled = false;
                    }}
                }} catch (err) {{
                    alert('Connection error. Please check your internet and try again.');
                    btn.textContent = originalText;
                    btn.disabled = false;
                }}
            }});
        }});
    }}
}})();
'''
        return js + "\n" + claim_js
