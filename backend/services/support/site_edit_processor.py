"""
Site Edit Processor — 3-Stage AI Pipeline

Converts a plain-English site edit request from a customer into a structured
set of edit operations and applies them to the current HTML/CSS.

Stage 1 — Context Extraction:
    Read generation_context from SiteVersion (or parse HTML/CSS as fallback).
    Now also extracts CSS *rules* for key sections so Stage 2 has visual context.

Stage 2 — Request Decomposition (one Claude call):
    Map the customer's natural-language request to a structured list of
    edit_operations (text changes, CSS variable updates, etc.).
    Receives full CSS rules for hero/nav/key sections, not just variable names.

Stage 3 — Edit Execution (smart dispatch, minimal AI):
    - css_var_change  → direct Python regex on the CSS string (no AI)
    - text_change     → direct Python string replacement on HTML (no AI)
    - complex ops     → targeted AI call with only the affected section
    Returns (updated_html, updated_css).

The result is stored as a new SiteVersion with is_preview=True.
The ticket's ai_processing_notes stores the edit_summary, edit_operations,
and preview_version_id so admin can review and approve.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.html_utils import strip_claim_bar, strip_claim_bar_css
from models.site_models import Site, SiteVersion
from models.support_ticket import SupportTicket

logger = logging.getLogger(__name__)
settings = get_settings()


class SiteEditProcessor:
    """3-stage pipeline that processes site_edit support tickets."""

    MODEL = "claude-sonnet-4-5"

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # ── Public entry point ─────────────────────────────────────────────────

    async def process(
        self,
        db: AsyncSession,
        ticket: SupportTicket,
    ) -> Dict[str, Any]:
        """
        Run the full 3-stage pipeline for a site_edit ticket.

        Returns a dict with:
            edit_summary        — one-sentence description of changes
            edit_operations     — structured list from Stage 2
            preview_version_id  — UUID of the new SiteVersion (is_preview=True)
            complexity          — "simple" | "moderate" | "complex"
            requires_review     — bool
        """
        if not ticket.site_id:
            return {
                "error": "Ticket has no associated site",
                "requires_review": True,
            }

        # Stage 1: Extract site context
        logger.info(f"[SiteEditProcessor] Stage 1: extracting context for site {ticket.site_id}")
        context = await self._stage1_extract_context(db, ticket.site_id)

        # Stage 2: Decompose customer request.
        # ticket.element_context stores List[TicketChange dicts] for structured tickets,
        # or None for plain-text tickets (legacy / non-site_edit).
        raw_changes = ticket.element_context  # Optional[List[Dict]]
        changes: List[Dict[str, Any]] = []
        if isinstance(raw_changes, list):
            changes = raw_changes
        elif isinstance(raw_changes, dict):
            # Legacy single-element format — wrap in a list
            changes = [{"description": ticket.description, "element_context": raw_changes}]

        change_count = len(changes)
        pin_count = sum(1 for c in changes if c.get("element_context"))
        logger.info(
            f"[SiteEditProcessor] Stage 2: {change_count} change(s), {pin_count} pinned. "
            f"Request: {ticket.description[:100]!r}"
        )
        decomposition = await self._stage2_decompose_request(
            site_context=context,
            changes=changes,
            fallback_description=ticket.description,
        )

        if decomposition.get("error"):
            logger.error(f"[SiteEditProcessor] Stage 2 failed: {decomposition}")
            return {**decomposition, "requires_review": True}

        ops = decomposition.get("edit_operations", [])
        logger.info(f"[SiteEditProcessor] Stage 2 produced {len(ops)} operations: {json.dumps(ops, indent=2)}")

        # Stage 3: Execute edits against full HTML/CSS
        current_version = context.get("_current_version")
        if not current_version:
            return {
                "error": "No current site version found",
                "requires_review": True,
            }

        # Strip claim bar before passing to AI — owned sites don't need it,
        # and it confuses the LLM into preserving or regenerating it.
        clean_html = strip_claim_bar(current_version.html_content)
        clean_css = strip_claim_bar_css(current_version.css_content or "")

        logger.info(f"[SiteEditProcessor] Stage 3: applying {len(ops)} operations")
        updated_html, updated_css, applied_ops = await self._stage3_execute_edits(
            html_content=clean_html,
            css_content=clean_css,
            edit_operations=ops,
        )

        # Ensure claim bar never ends up in the preview version
        updated_html = strip_claim_bar(updated_html)
        updated_css = strip_claim_bar_css(updated_css)

        logger.info(f"[SiteEditProcessor] Stage 3 applied {applied_ops}/{len(ops)} operations. "
                    f"HTML: {len(clean_html)} → {len(updated_html)} chars, "
                    f"CSS: {len(clean_css)} → {len(updated_css)} chars")

        if updated_html == clean_html and updated_css == clean_css:
            logger.warning("[SiteEditProcessor] Stage 3 produced NO changes vs input — edit may have failed")

        # Store preview version
        preview_version = await self._create_preview_version(
            db=db,
            site_id=ticket.site_id,
            current_version=current_version,
            updated_html=updated_html,
            updated_css=updated_css,
            edit_summary=decomposition.get("edit_summary", "Site changes"),
            edit_operations=ops,
        )

        return {
            "edit_summary": decomposition.get("edit_summary", ""),
            "edit_operations": ops,
            "preview_version_id": str(preview_version.id),
            "complexity": decomposition.get("complexity", "simple"),
            "requires_review": decomposition.get("requires_review", True),
            "operations_applied": applied_ops,
        }

    # ── Stage 1: Context Extraction ────────────────────────────────────────

    async def _stage1_extract_context(
        self,
        db: AsyncSession,
        site_id: UUID,
    ) -> Dict[str, Any]:
        """
        Load the current SiteVersion and extract structured context.
        Prefers generation_context JSONB; falls back to parsing CSS/HTML.
        Also extracts the actual CSS *rules* for the top sections so Stage 2
        has real visual context (not just variable names).
        """
        stmt = (
            select(SiteVersion)
            .where(SiteVersion.site_id == site_id)
            .where(SiteVersion.is_current == True)  # noqa: E712
        )
        result = await db.execute(stmt)
        current_version = result.scalar_one_or_none()

        if not current_version:
            stmt2 = (
                select(SiteVersion)
                .where(SiteVersion.site_id == site_id)
                .order_by(SiteVersion.version_number.desc())
            )
            result2 = await db.execute(stmt2)
            current_version = result2.scalars().first()

        if not current_version:
            return {"_current_version": None}

        css_content = strip_claim_bar_css(current_version.css_content or "")
        html_content = strip_claim_bar(current_version.html_content or "")

        # Parse CSS variables from :root
        css_variables: Dict[str, str] = {}
        root_match = re.search(r":root\s*\{([^}]+)\}", css_content)
        if root_match:
            for line in root_match.group(1).splitlines():
                line = line.strip()
                if line.startswith("--") and ":" in line:
                    name, _, value = line.partition(":")
                    css_variables[name.strip()] = value.strip().rstrip(";")

        # Extract full :root block as text (for Stage 2 prompt)
        root_block = root_match.group(0) if root_match else ""

        # Extract CSS rules for key visual sections (hero, nav, header, body, footer)
        key_section_rules = self._extract_key_css_rules(css_content)

        # Extract section headings from HTML
        heading_matches = re.findall(
            r'<(?:h1|h2)[^>]*>([^<]{3,60})</(?:h1|h2)>',
            html_content,
            re.IGNORECASE,
        )
        sections = [h.strip() for h in heading_matches[:8]]

        # Extract first ~2KB of body content to show structure
        body_preview = ""
        body_match = re.search(r'<body[^>]*>(.*)', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_preview = body_match.group(1)[:2000]

        ctx: Dict[str, Any] = {
            "_current_version": current_version,
            "css_variables": css_variables,
            "css_root_block": root_block,
            "key_section_rules": key_section_rules,
            "sections": sections,
            "body_preview": body_preview,
            "features": [],
            "design_brief_summary": {},
        }

        # Overlay stored generation_context if available (preserves design intent)
        if current_version.generation_context:
            stored = dict(current_version.generation_context)
            stored.pop("_current_version", None)
            for k, v in stored.items():
                if k not in ctx or not ctx[k]:
                    ctx[k] = v

        return ctx

    def _extract_key_css_rules(self, css: str) -> str:
        """
        Extract the CSS rules for visually important sections (hero, nav, header,
        footer, body) so Stage 2 can see which selectors/variables control what.
        Returns up to 3000 chars of the most relevant rules.
        """
        key_selectors = [
            "body", ".nav", "nav", ".hero", "#hero", "header",
            ".hero::before", ".header", ".site-header",
            ".top", ".banner", ".section-hero", "footer", ".footer",
        ]
        collected: List[str] = []
        total = 0

        # Find each rule block by selector
        for sel in key_selectors:
            escaped = re.escape(sel)
            pattern = rf"{escaped}[^{{]*\{{[^}}]*\}}"
            matches = re.findall(pattern, css, re.DOTALL)
            for m in matches:
                block = m.strip()
                if block and block not in collected:
                    collected.append(block)
                    total += len(block)
                    if total > 3000:
                        break
            if total > 3000:
                break

        return "\n\n".join(collected) if collected else "(could not extract section rules)"

    # ── Stage 2: Request Decomposition ────────────────────────────────────

    async def _stage2_decompose_request(
        self,
        site_context: Dict[str, Any],
        changes: List[Dict[str, Any]],
        fallback_description: str = "",
    ) -> Dict[str, Any]:
        """
        Map structured customer changes → concrete edit operations.

        Each change in `changes` is a dict with:
          - description     : plain-language intent (required)
          - element_context : exact DOM snapshot from the visual picker (optional)

        Having one (intent, optional_target) pair per change gives the LLM
        zero-ambiguity matching — no cross-referencing across a global description
        and a separate pin list.
        """
        css_vars = site_context.get("css_variables", {})
        key_section_rules = site_context.get("key_section_rules", "")
        sections = site_context.get("sections", [])
        body_preview = site_context.get("body_preview", "")

        css_vars_summary = "\n".join(
            f"  {k}: {v}" for k, v in css_vars.items()
        ) or "  (none found)"
        sections_summary = "\n".join(f"  - {s}" for s in sections) or "  (none found)"

        # ── Build per-change blocks ───────────────────────────────────────────
        # If no structured changes were provided, wrap the fallback description
        # in a single change block so the prompt structure stays consistent.
        if not changes:
            changes = [{"description": fallback_description, "element_context": None}]

        change_blocks = []
        for idx, change in enumerate(changes, start=1):
            desc = change.get("description", "").strip()
            pin = change.get("element_context")

            pin_detail = ""
            if pin and isinstance(pin, dict):
                styles = pin.get("computed_styles", {})
                styles_fmt = "\n".join(
                    f"        {k}: {v}" for k, v in styles.items() if v
                )
                pin_detail = (
                    f"\n  Pinned element (customer clicked this EXACT element):\n"
                    f"    CSS selector : {pin.get('css_selector', 'unknown')}\n"
                    f"    Tag          : <{pin.get('tag', '?')}>\n"
                    f"    DOM path     : {pin.get('dom_path', '')}\n"
                    f"    Text content : \"{pin.get('text_content', '')[:150]}\"\n"
                    f"    HTML snippet : {pin.get('html', '')[:300]}\n"
                    f"    Computed styles:\n{styles_fmt}\n"
                    f"  → For this change, target_selector MUST be: {pin.get('css_selector', '')}"
                )
            else:
                pin_detail = "\n  Pinned element: (none — infer the target from the description and site structure)"

            change_blocks.append(
                f"Change {idx} of {len(changes)}:\n"
                f"  Customer says: \"{desc}\""
                + pin_detail
            )

        changes_block = "\n\n".join(change_blocks)

        prompt = f"""You are a website editing assistant. A customer has submitted a structured list of changes for their website.
Each change has a plain-language description and optionally a pinned element (the exact DOM node they clicked).
The customer is NOT technical — interpret their words visually and concretely.

=== CUSTOMER CHANGES ===
{changes_block}

=== AVAILABLE CSS VARIABLES (:root) ===
{css_vars_summary}

=== KEY SECTION CSS RULES (actual selectors controlling layout & color) ===
{key_section_rules}

=== PAGE SECTIONS (headings) ===
{sections_summary}

=== TOP OF PAGE HTML STRUCTURE ===
{body_preview[:1500]}

=== YOUR TASK ===
For EACH customer change above, produce one or more edit_operations.
Match the change index (1, 2, 3) to the edit_operations via a "change_index" field.

Interpretation rules:
  - "the top section" / "the banner" / "the header" usually means .hero or nav
  - "background color" means a `background` or `background-color` CSS property
  - "the black one" / "the dark one" means find which variable is dark (e.g. #0a0a0f)
  - For color changes, prefer css_var_change if the color is controlled by a :root variable
  - For gradient backgrounds, you may need to change MULTIPLE variables
  - If a pinned element is provided, its css_selector is authoritative — use it exactly
  - Do NOT guess which element the customer means when a pin is provided

Return ONLY valid JSON with no markdown fences:

{{
  "edit_summary": "One clear sentence describing ALL changes that will be made",
  "edit_operations": [
    {{
      "change_index": 1,
      "type": "css_var_change",
      "target_variable": "--color-off-black",
      "current_value": "#0a0a0f",
      "new_value": "#0d1b2e",
      "reason": "Change 1: hero background uses --color-off-black; customer wants navy"
    }},
    {{
      "change_index": 2,
      "type": "text_change",
      "selector_hint": "h1 in .hero section",
      "current_value": "exact current text here",
      "new_value": "exact new text here",
      "reason": "Change 2: customer asked to update the main heading"
    }},
    {{
      "change_index": 2,
      "type": "css_rule_change",
      "css_selector": "section.hero > h1",
      "property": "font-size",
      "current_value": "48px",
      "new_value": "60px",
      "reason": "Change 2: customer pinned this h1 and asked for larger text"
    }}
  ],
  "complexity": "simple",
  "requires_review": true
}}

Operation types:
- css_var_change  : change a CSS custom property in :root (best for colors / fonts / spacing)
- text_change     : change visible text (headings, paragraphs, phone numbers, CTAs)
- css_rule_change : change a CSS property that is NOT a variable — use the exact selector
- section_add     : add a new page section
- section_remove  : remove an existing section
- image_change    : swap an image src

Rules:
- For css_var_change, target_variable MUST be one of the variables listed in AVAILABLE CSS VARIABLES.
- For text_change, current_value must exactly match the text currently in the HTML.
- For css_rule_change with a pinned element, copy the css_selector from the pinned element block.
- Include a "change_index" on every operation so Stage 3 can log which change it came from.
"""
        try:
            response = await self._client.messages.create(
                model=self.MODEL,
                max_tokens=4096,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
                raw = re.sub(r"```\s*$", "", raw).strip()

            result = json.loads(raw)
            logger.info(f"[SiteEditProcessor] Stage 2 result: {json.dumps(result, indent=2)}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[SiteEditProcessor] Stage 2 JSON parse error: {e}\nRaw response: {raw!r}")
            return {
                "error": "Failed to parse decomposition response",
                "edit_summary": "Manual review required",
                "edit_operations": [],
                "complexity": "complex",
                "requires_review": True,
            }
        except Exception as e:
            logger.error(f"[SiteEditProcessor] Stage 2 error: {e}")
            return {
                "error": str(e),
                "requires_review": True,
            }

    # ── Stage 3: Edit Execution (smart dispatch) ──────────────────────────

    async def _stage3_execute_edits(
        self,
        html_content: str,
        css_content: str,
        edit_operations: List[Dict[str, Any]],
    ) -> Tuple[str, str, int]:
        """
        Apply edit operations with a smart dispatch strategy:
        - css_var_change  → direct Python regex on CSS (reliable, instant)
        - text_change     → direct Python string replacement on HTML (reliable, instant)
        - css_rule_change → direct Python regex on CSS (reliable, instant)
        - complex ops     → targeted AI call with only relevant section (not full file)

        Returns (updated_html, updated_css, num_operations_applied).
        """
        updated_html = html_content
        updated_css = css_content
        applied = 0

        for op in edit_operations:
            op_type = op.get("type", "")
            try:
                if op_type == "css_var_change":
                    result_css = self._apply_css_var_change(updated_css, op)
                    if result_css != updated_css:
                        updated_css = result_css
                        applied += 1
                        logger.info(f"[SiteEditProcessor] ✓ Applied css_var_change: {op.get('target_variable')} → {op.get('new_value')}")
                    else:
                        logger.warning(f"[SiteEditProcessor] ✗ css_var_change made no change: {op.get('target_variable')!r} not found or already matches")

                elif op_type == "text_change":
                    result_html = self._apply_text_change(updated_html, op)
                    if result_html != updated_html:
                        updated_html = result_html
                        applied += 1
                        logger.info(f"[SiteEditProcessor] ✓ Applied text_change: {op.get('current_value','')[:40]!r} → {op.get('new_value','')[:40]!r}")
                    else:
                        logger.warning(f"[SiteEditProcessor] ✗ text_change made no change: {op.get('current_value','')[:60]!r} not found")

                elif op_type == "css_rule_change":
                    result_css = self._apply_css_rule_change(updated_css, op)
                    if result_css != updated_css:
                        updated_css = result_css
                        applied += 1
                        logger.info(f"[SiteEditProcessor] ✓ Applied css_rule_change")
                    else:
                        logger.warning(f"[SiteEditProcessor] ✗ css_rule_change made no change")

                else:
                    # Complex operation — use AI with targeted context
                    logger.info(f"[SiteEditProcessor] Complex op '{op_type}' → AI call")
                    result_html, result_css = await self._apply_complex_op_with_ai(
                        updated_html, updated_css, op
                    )
                    if result_html != updated_html or result_css != updated_css:
                        updated_html = result_html
                        updated_css = result_css
                        applied += 1
                        logger.info(f"[SiteEditProcessor] ✓ Applied complex op '{op_type}' via AI")
                    else:
                        logger.warning(f"[SiteEditProcessor] ✗ Complex op '{op_type}' via AI made no change")

            except Exception as e:
                logger.error(f"[SiteEditProcessor] Error applying op {op_type}: {e}", exc_info=True)

        return updated_html, updated_css, applied

    def _apply_css_var_change(self, css: str, op: Dict[str, Any]) -> str:
        """Replace a single CSS custom property value inside :root { }."""
        var_name = op.get("target_variable", "").strip()
        new_value = op.get("new_value", "").strip()
        if not var_name or not new_value:
            return css

        # Replace inside :root block specifically
        def replace_in_root(m: re.Match) -> str:
            root_block = m.group(0)
            # Replace the variable line
            updated = re.sub(
                rf"({re.escape(var_name)}\s*:\s*)[^;]+",
                rf"\g<1>{new_value}",
                root_block,
            )
            return updated

        updated = re.sub(r":root\s*\{[^}]+\}", replace_in_root, css, flags=re.DOTALL)

        # Fallback: replace anywhere in file if not found in :root
        if updated == css:
            updated = re.sub(
                rf"({re.escape(var_name)}\s*:\s*)[^;]+",
                rf"\g<1>{new_value}",
                css,
            )

        return updated

    def _apply_text_change(self, html: str, op: Dict[str, Any]) -> str:
        """Replace text content in HTML. Tries exact match then fuzzy."""
        current = op.get("current_value", "").strip()
        new_val = op.get("new_value", "").strip()
        if not current or not new_val:
            return html

        # 1. Exact substring match (case-insensitive)
        idx = html.lower().find(current.lower())
        if idx != -1:
            return html[:idx] + new_val + html[idx + len(current):]

        # 2. Fuzzy: collapse whitespace and try again
        normalized_current = re.sub(r'\s+', ' ', current)
        pattern = re.sub(r'\s+', r'\\s+', re.escape(normalized_current))
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            return html[:match.start()] + new_val + html[match.end():]

        return html

    def _apply_css_rule_change(self, css: str, op: Dict[str, Any]) -> str:
        """Change a hardcoded CSS property value in a rule (not a variable)."""
        selector = op.get("selector", "").strip()
        prop = op.get("property", "").strip()
        new_value = op.get("new_value", "").strip()
        current_value = op.get("current_value", "").strip()

        if not prop or not new_value:
            return css

        if selector:
            # Target change within selector block
            def replace_in_selector(m: re.Match) -> str:
                block = m.group(0)
                if current_value:
                    return block.replace(current_value, new_value, 1)
                return re.sub(
                    rf"({re.escape(prop)}\s*:\s*)[^;]+",
                    rf"\g<1>{new_value}",
                    block,
                )
            escaped_sel = re.escape(selector)
            css = re.sub(
                rf"{escaped_sel}\s*\{{[^}}]+\}}",
                replace_in_selector,
                css,
                flags=re.DOTALL,
            )
        elif current_value:
            css = css.replace(current_value, new_value, 1)

        return css

    async def _apply_complex_op_with_ai(
        self,
        html: str,
        css: str,
        op: Dict[str, Any],
    ) -> Tuple[str, str]:
        """
        For complex operations (section_add, section_remove, image_change),
        use an AI call with ONLY the relevant section of HTML, not the full file.
        """
        op_type = op.get("type", "")
        op_json = json.dumps(op, indent=2)

        # Extract relevant section to minimize tokens sent
        relevant_html = self._extract_relevant_section(html, op)

        prompt = f"""You are a professional web developer. Apply EXACTLY this one edit operation to the website section below.

OPERATION:
{op_json}

RELEVANT HTML SECTION:
{relevant_html[:8000]}

RULES:
- Make ONLY the change described in the operation
- Return the updated HTML section ONLY (no explanation, no full page)
- Preserve all existing classes, IDs, and attributes
- If you cannot make the change cleanly, return the HTML UNCHANGED

Return ONLY the updated HTML section:"""

        try:
            response = await self._client.messages.create(
                model=self.MODEL,
                max_tokens=8000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            updated_section = response.content[0].text.strip()

            # Strip markdown code fences — the AI often wraps HTML in ```html ... ```
            if updated_section.startswith("```"):
                updated_section = re.sub(
                    r"^```(?:html|css|javascript|js)?\s*", "", updated_section, flags=re.IGNORECASE
                )
                updated_section = re.sub(r"\s*```\s*$", "", updated_section).strip()

            # If the operation affected HTML, splice back the updated section
            if op_type in ("section_add", "section_remove", "image_change"):
                if relevant_html and relevant_html in html and updated_section != relevant_html:
                    html = html.replace(relevant_html, updated_section, 1)

        except Exception as e:
            logger.error(f"[SiteEditProcessor] AI complex op error: {e}")

        return html, css

    def _extract_relevant_section(self, html: str, op: Dict[str, Any]) -> str:
        """Extract the most relevant HTML section for a complex operation."""
        op_type = op.get("type", "")
        location = op.get("location", "").lower()

        if "hero" in location or "header" in location or "top" in location:
            # Extract the hero/header section
            match = re.search(
                r'(<(?:section|div|header)[^>]*(?:hero|header|banner)[^>]*>.*?</(?:section|div|header)>)',
                html, re.DOTALL | re.IGNORECASE
            )
            if match:
                return match.group(1)

        if "footer" in location:
            match = re.search(r'(<footer[^>]*>.*?</footer>)', html, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1)

        # Default: return first 5KB of body
        body_match = re.search(r'<body[^>]*>(.*)', html, re.DOTALL | re.IGNORECASE)
        if body_match:
            return body_match.group(1)[:5000]
        return html[:5000]

    # ── Helper: create preview SiteVersion ────────────────────────────────

    async def _create_preview_version(
        self,
        db: AsyncSession,
        site_id: UUID,
        current_version: SiteVersion,
        updated_html: str,
        updated_css: str,
        edit_summary: str,
        edit_operations: List[Dict[str, Any]],
    ) -> SiteVersion:
        """Store the AI-generated edit as a preview SiteVersion (not yet current)."""
        from sqlalchemy import func

        count_result = await db.execute(
            select(func.count()).select_from(SiteVersion).where(SiteVersion.site_id == site_id)
        )
        version_count = count_result.scalar() or 0

        # Build updated generation_context (reflect css var changes)
        new_ctx: Dict[str, Any] = dict(current_version.generation_context or {})
        new_css_vars: Dict[str, str] = dict(new_ctx.get("css_variables", {}))
        for op in edit_operations:
            if op.get("type") == "css_var_change":
                var_name = op.get("target_variable", "")
                new_val = op.get("new_value", "")
                if var_name:
                    new_css_vars[var_name] = new_val
        new_ctx["css_variables"] = new_css_vars
        new_ctx["generated_at"] = datetime.now(timezone.utc).isoformat()
        new_ctx["architect_version"] = "v2-edit"

        preview = SiteVersion(
            site_id=site_id,
            version_number=version_count + 1,
            html_content=updated_html,
            css_content=updated_css,
            js_content=current_version.js_content,
            generation_context=new_ctx,
            change_description=edit_summary,
            change_type="edit",
            created_by_type="ai",
            is_current=False,
            is_preview=True,
        )
        db.add(preview)
        await db.commit()
        await db.refresh(preview)

        logger.info(
            f"[SiteEditProcessor] Created preview version {preview.id} "
            f"(v{preview.version_number}) for site {site_id}"
        )
        return preview
