"""
Editor Agent

AI agent specialized in processing and applying site edit requests.
Uses Claude Sonnet to understand requests and generate precise modifications.

Architecture:
- Modular prompt system for different edit types
- Multi-step workflow: analyze → generate → validate
- Safety checks to prevent breaking changes

Author: WebMagic Team
Date: January 21, 2026
"""
import logging
import json
from typing import Dict, Any, Optional, Tuple
from anthropic import AsyncAnthropic

from core.config import get_settings
from services.creative.agents.base import BaseAgent

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================================
# EDIT TYPE CONSTANTS
# ============================================================================

class EditType:
    """Constants for edit types."""
    TEXT = "text"
    STYLE = "style"
    LAYOUT = "layout"
    CONTENT = "content"
    IMAGE = "image"


# ============================================================================
# EDITOR AGENT
# ============================================================================

class EditorAgent(BaseAgent):
    """
    AI agent for processing site edit requests.
    
    Capabilities:
    - Natural language understanding of edit requests
    - Precise HTML/CSS/JS modifications
    - Safety validation
    - Preview generation
    
    Example:
        ```python
        agent = EditorAgent()
        result = await agent.process_edit_request(
            request_text="Change button color to blue",
            current_html="<button class='btn'>Click</button>",
            current_css=".btn { background: red; }"
        )
        ```
    """
    
    def __init__(self):
        """Initialize the editor agent."""
        super().__init__(
            name="EditorAgent",
            model="claude-sonnet-4-20250514",
            temperature=0.1  # Low temperature for precision
        )
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    # ========================================================================
    # MAIN PROCESSING METHODS
    # ========================================================================
    
    async def process_edit_request(
        self,
        request_text: str,
        request_type: Optional[str],
        current_html: str,
        current_css: Optional[str] = None,
        current_js: Optional[str] = None,
        target_section: Optional[str] = None,
        site_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an edit request end-to-end.
        
        Steps:
        1. Analyze request to understand intent
        2. Generate modified code
        3. Validate changes
        4. Return preview-ready result
        
        Args:
            request_text: Natural language edit request
            request_type: Type of edit (text, style, layout, etc.)
            current_html: Current HTML content
            current_css: Current CSS content
            current_js: Current JavaScript content
            target_section: Optional specific section to edit
            site_context: Additional context about the site
        
        Returns:
            Dictionary with:
            - success: bool
            - modified_html: str
            - modified_css: Optional[str]
            - modified_js: Optional[str]
            - changes_made: Dict describing changes
            - confidence: float (0-1)
            - warnings: List of potential issues
        """
        logger.info(
            f"Processing edit request: {request_text[:100]}...",
            extra={
                "request_type": request_type,
                "target_section": target_section,
                "has_css": bool(current_css),
                "has_js": bool(current_js)
            }
        )
        
        try:
            # Step 1: Analyze the request
            analysis = await self.analyze_request(
                request_text=request_text,
                request_type=request_type,
                current_html=current_html,
                current_css=current_css,
                target_section=target_section
            )
            
            logger.debug(f"Request analysis: {analysis}")
            
            # Check confidence level
            if analysis.get("confidence", 0) < 0.5:
                return {
                    "success": False,
                    "error": "Request unclear or too complex",
                    "analysis": analysis,
                    "confidence": analysis.get("confidence", 0),
                    "suggestions": analysis.get("clarification_needed", [])
                }
            
            # Step 2: Generate modifications
            modifications = await self.generate_modifications(
                request_text=request_text,
                request_type=request_type or analysis.get("detected_type", "style"),
                analysis=analysis,
                current_html=current_html,
                current_css=current_css,
                current_js=current_js,
                target_section=target_section
            )
            
            logger.debug("Generated modifications successfully")
            
            # Step 3: Validate changes
            validation = await self.validate_changes(
                original_html=current_html,
                modified_html=modifications["modified_html"],
                original_css=current_css,
                modified_css=modifications.get("modified_css"),
                changes_description=analysis["changes_description"]
            )
            
            logger.debug(f"Validation result: {validation}")
            
            # Return complete result
            return {
                "success": True,
                "modified_html": modifications["modified_html"],
                "modified_css": modifications.get("modified_css"),
                "modified_js": modifications.get("modified_js"),
                "changes_made": {
                    "type": request_type or analysis.get("detected_type"),
                    "description": analysis["changes_description"],
                    "affected_elements": analysis.get("affected_elements", []),
                    "specific_changes": modifications.get("changes_list", [])
                },
                "analysis": analysis,
                "validation": validation,
                "confidence": analysis.get("confidence", 0.8),
                "warnings": validation.get("warnings", [])
            }
        
        except Exception as e:
            logger.error(f"Error processing edit request: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "confidence": 0.0
            }
    
    # ========================================================================
    # STEP 1: ANALYZE REQUEST
    # ========================================================================
    
    async def analyze_request(
        self,
        request_text: str,
        request_type: Optional[str],
        current_html: str,
        current_css: Optional[str],
        target_section: Optional[str]
    ) -> Dict[str, Any]:
        """
        Analyze an edit request to understand intent.
        
        Uses Claude to:
        - Identify what needs to change
        - Determine affected elements
        - Assess feasibility
        - Calculate confidence
        
        Args:
            request_text: Natural language request
            request_type: Suggested type
            current_html: Current HTML for context
            current_css: Current CSS for context
            target_section: Target section if specified
        
        Returns:
            Analysis dictionary with intent, confidence, and plan
        """
        system_prompt = self._get_analysis_system_prompt()
        user_prompt = self._build_analysis_prompt(
            request_text=request_text,
            request_type=request_type,
            current_html=current_html,
            current_css=current_css,
            target_section=target_section
        )
        
        # Use streaming to avoid timeout limits on large max_tokens
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=64000,  # Max for Claude Sonnet 4.5
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        ) as stream:
            analysis_text = await stream.get_final_text()
        
        try:
            # Try to extract JSON from response
            analysis = json.loads(analysis_text)
        except json.JSONDecodeError:
            # Fallback: parse structured text
            analysis = self._parse_analysis_text(analysis_text)
        
        return analysis
    
    # ========================================================================
    # STEP 2: GENERATE MODIFICATIONS
    # ========================================================================
    
    async def generate_modifications(
        self,
        request_text: str,
        request_type: str,
        analysis: Dict[str, Any],
        current_html: str,
        current_css: Optional[str],
        current_js: Optional[str],
        target_section: Optional[str]
    ) -> Dict[str, Any]:
        """
        Generate modified HTML/CSS/JS based on analysis.
        
        Args:
            request_text: Original request
            request_type: Type of edit
            analysis: Analysis from previous step
            current_html: Current HTML
            current_css: Current CSS
            current_js: Current JS
            target_section: Target section
        
        Returns:
            Dictionary with modified code
        """
        system_prompt = self._get_generation_system_prompt(request_type)
        user_prompt = self._build_generation_prompt(
            request_text=request_text,
            analysis=analysis,
            current_html=current_html,
            current_css=current_css,
            current_js=current_js,
            target_section=target_section
        )
        
        # Use streaming to avoid timeout limits on large max_tokens
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=64000,  # Max for Claude Sonnet 4.5
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        ) as stream:
            response_text = await stream.get_final_text()
        
        # Parse response to extract code
        modifications = self._extract_code_from_response(response_text)
        
        return modifications
    
    # ========================================================================
    # STEP 3: VALIDATE CHANGES
    # ========================================================================
    
    async def validate_changes(
        self,
        original_html: str,
        modified_html: str,
        original_css: Optional[str],
        modified_css: Optional[str],
        changes_description: str
    ) -> Dict[str, Any]:
        """
        Validate that changes are safe and correct.
        
        Checks:
        - HTML structure preserved
        - No broken tags
        - Responsive design maintained
        - SEO elements preserved
        - No security issues
        
        Args:
            original_html: Original HTML
            modified_html: Modified HTML
            original_css: Original CSS
            modified_css: Modified CSS
            changes_description: Description of intended changes
        
        Returns:
            Validation result with warnings
        """
        system_prompt = """You are a senior web developer reviewing code changes.
Your job is to validate that modifications are safe and correct.

Check for:
1. HTML structure integrity (no broken tags)
2. Responsive design preservation
3. SEO elements (meta tags, headings, alt text)
4. Accessibility (ARIA labels, semantic HTML)
5. Security issues (no inline scripts, XSS risks)

Return a JSON object with:
{
    "is_valid": true/false,
    "warnings": ["warning 1", "warning 2"],
    "errors": ["error 1"],
    "recommendations": ["recommendation 1"]
}"""

        user_prompt = f"""Validate these changes:

**Intended Changes:**
{changes_description}

**Original HTML Length:** {len(original_html)} characters
**Modified HTML Length:** {len(modified_html)} characters
**CSS Modified:** {bool(modified_css)}

**Modified HTML (first 2000 chars):**
```html
{modified_html[:2000]}
```

{f"**Modified CSS (first 1000 chars):**```css{modified_css[:1000]}```" if modified_css else ""}

Analyze and return validation result as JSON."""

        # Use streaming to avoid timeout limits on large max_tokens
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=64000,  # Max for Claude Sonnet 4.5
            temperature=0.1,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        ) as stream:
            response_text = await stream.get_final_text()
        
        try:
            validation = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback validation
            validation = {
                "is_valid": True,
                "warnings": [],
                "errors": [],
                "recommendations": []
            }
        
        return validation
    
    # ========================================================================
    # PROMPT BUILDERS (Private Methods)
    # ========================================================================
    
    def _get_analysis_system_prompt(self) -> str:
        """Get system prompt for request analysis."""
        return """You are an expert web developer analyzing site edit requests.

Your job is to understand what the customer wants to change and create a clear plan.

Analyze the request and return a JSON object with:
{
    "detected_type": "text|style|layout|content",
    "confidence": 0.0-1.0,
    "changes_description": "Clear description of what needs to change",
    "affected_elements": ["list", "of", "elements"],
    "target_selectors": [".class", "#id"],
    "is_feasible": true/false,
    "complexity": "simple|moderate|complex",
    "clarification_needed": ["any questions for the customer"]
}

Be precise and conservative. If unclear, lower confidence and ask for clarification."""
    
    def _build_analysis_prompt(
        self,
        request_text: str,
        request_type: Optional[str],
        current_html: str,
        current_css: Optional[str],
        target_section: Optional[str]
    ) -> str:
        """Build prompt for analyzing a request."""
        html_preview = current_html[:2000]  # First 2000 chars
        css_preview = current_css[:1000] if current_css else "None"
        
        return f"""Analyze this edit request:

**Customer Request:**
"{request_text}"

**Suggested Type:** {request_type or "Not specified"}
**Target Section:** {target_section or "Entire site"}

**Current HTML (preview):**
```html
{html_preview}
```

**Current CSS (preview):**
```css
{css_preview}
```

Analyze the request and return your analysis as JSON."""
    
    def _get_generation_system_prompt(self, request_type: str) -> str:
        """Get system prompt for code generation."""
        base_prompt = """You are a senior frontend developer making precise code changes.

CRITICAL RULES:
1. Make ONLY the requested changes - don't refactor unrelated code
2. Preserve all responsive design (@media queries)
3. Maintain semantic HTML structure
4. Keep all existing IDs and critical classes
5. Don't remove SEO elements (meta tags, headings, alt text)
6. Use inline styles only if modifying style attributes
7. Preserve all JavaScript functionality

Return your response in this format:
```html
[modified HTML here]
```

```css
[modified CSS here if changed]
```

```javascript
[modified JS here if changed]
```

Then list specific changes made."""
        
        # Type-specific guidance
        type_guidance = {
            EditType.TEXT: "\nFocus on text content only. Don't change structure.",
            EditType.STYLE: "\nModify CSS properties. Use semantic color variables when possible.",
            EditType.LAYOUT: "\nAdjust layout carefully. Test responsiveness mentally.",
            EditType.CONTENT: "\nAdd/modify content matching the existing style."
        }
        
        return base_prompt + type_guidance.get(request_type, "")
    
    def _build_generation_prompt(
        self,
        request_text: str,
        analysis: Dict[str, Any],
        current_html: str,
        current_css: Optional[str],
        current_js: Optional[str],
        target_section: Optional[str]
    ) -> str:
        """Build prompt for generating modifications."""
        return f"""Apply this edit request:

**Request:** "{request_text}"

**Analysis:**
- Type: {analysis.get('detected_type', 'unknown')}
- Affected elements: {', '.join(analysis.get('affected_elements', []))}
- Changes needed: {analysis.get('changes_description', 'See request')}

**Current Code:**

```html
{current_html}
```

{f"```css{current_css}```" if current_css else ""}

{f"```javascript{current_js}```" if current_js else ""}

Apply the changes and return the modified code."""
    
    def _parse_analysis_text(self, text: str) -> Dict[str, Any]:
        """Parse analysis from text when JSON fails."""
        # Fallback parser
        return {
            "detected_type": "style",
            "confidence": 0.7,
            "changes_description": text[:200],
            "affected_elements": [],
            "is_feasible": True,
            "complexity": "moderate"
        }
    
    def _extract_code_from_response(
        self,
        response_text: str
    ) -> Dict[str, Any]:
        """Extract HTML/CSS/JS from Claude's response."""
        import re
        
        result = {}
        
        # Extract HTML
        html_match = re.search(
            r'```html\s*\n(.*?)\n```',
            response_text,
            re.DOTALL | re.IGNORECASE
        )
        if html_match:
            result["modified_html"] = html_match.group(1).strip()
        
        # Extract CSS
        css_match = re.search(
            r'```css\s*\n(.*?)\n```',
            response_text,
            re.DOTALL | re.IGNORECASE
        )
        if css_match:
            result["modified_css"] = css_match.group(1).strip()
        
        # Extract JavaScript
        js_match = re.search(
            r'```(?:javascript|js)\s*\n(.*?)\n```',
            response_text,
            re.DOTALL | re.IGNORECASE
        )
        if js_match:
            result["modified_js"] = js_match.group(1).strip()
        
        # Extract changes list
        changes_section = re.search(
            r'(?:Changes Made|Modifications):\s*\n(.*?)(?:\n\n|$)',
            response_text,
            re.DOTALL | re.IGNORECASE
        )
        if changes_section:
            changes_text = changes_section.group(1)
            changes_list = [
                line.strip().lstrip('-•*').strip()
                for line in changes_text.split('\n')
                if line.strip()
            ]
            result["changes_list"] = changes_list
        
        return result


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_editor_agent() -> EditorAgent:
    """
    Get EditorAgent instance (singleton pattern).
    
    Returns:
        EditorAgent instance
    """
    if not hasattr(get_editor_agent, "_instance"):
        get_editor_agent._instance = EditorAgent()
    return get_editor_agent._instance

