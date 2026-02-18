"""
Site Edit Processor — 3-Stage AI Pipeline

Converts a plain-English site edit request from a customer into a structured
set of edit operations and applies them to the current HTML/CSS.

Stage 1 — Context Extraction:
    Read generation_context from SiteVersion (or parse HTML/CSS as fallback).

Stage 2 — Request Decomposition (one Claude call):
    Map the customer's natural-language request to a structured list of
    edit_operations (text changes, CSS variable updates, etc.).

Stage 3 — Edit Execution (one Claude call):
    Apply the structured operations to the full HTML + CSS and return
    complete updated files.

The result is stored as a new SiteVersion with is_preview=True.
The ticket's ai_processing_notes stores the edit_summary, edit_operations,
and preview_version_id so admin can review and approve.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
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
        context = await self._stage1_extract_context(db, ticket.site_id)

        # Stage 2: Decompose customer request
        decomposition = await self._stage2_decompose_request(
            edit_request=ticket.description,
            site_context=context,
        )

        if decomposition.get("error"):
            return {**decomposition, "requires_review": True}

        # Stage 3: Execute edits against full HTML/CSS
        current_version = context.get("_current_version")
        if not current_version:
            return {
                "error": "No current site version found",
                "requires_review": True,
            }

        updated_html, updated_css = await self._stage3_execute_edits(
            html_content=current_version.html_content,
            css_content=current_version.css_content or "",
            edit_operations=decomposition.get("edit_operations", []),
        )

        # Store preview version
        preview_version = await self._create_preview_version(
            db=db,
            site_id=ticket.site_id,
            current_version=current_version,
            updated_html=updated_html,
            updated_css=updated_css,
            edit_summary=decomposition.get("edit_summary", "Site changes"),
            edit_operations=decomposition.get("edit_operations", []),
        )

        return {
            "edit_summary": decomposition.get("edit_summary", ""),
            "edit_operations": decomposition.get("edit_operations", []),
            "preview_version_id": str(preview_version.id),
            "complexity": decomposition.get("complexity", "simple"),
            "requires_review": decomposition.get("requires_review", True),
        }

    # ── Stage 1: Context Extraction ────────────────────────────────────────

    async def _stage1_extract_context(
        self,
        db: AsyncSession,
        site_id: UUID,
    ) -> Dict[str, Any]:
        """
        Load the current SiteVersion and extract structured context.
        Prefers generation_context JSONB; falls back to parsing CSS.
        """
        stmt = (
            select(SiteVersion)
            .where(SiteVersion.site_id == site_id)
            .where(SiteVersion.is_current == True)  # noqa: E712
        )
        result = await db.execute(stmt)
        current_version = result.scalar_one_or_none()

        if not current_version:
            # Try any version
            stmt2 = (
                select(SiteVersion)
                .where(SiteVersion.site_id == site_id)
                .order_by(SiteVersion.version_number.desc())
            )
            result2 = await db.execute(stmt2)
            current_version = result2.scalars().first()

        if not current_version:
            return {"_current_version": None}

        # Use stored generation_context if available
        if current_version.generation_context:
            ctx = dict(current_version.generation_context)
            ctx["_current_version"] = current_version
            return ctx

        # Fallback: parse CSS variables from css_content
        css_variables: Dict[str, str] = {}
        css_content = current_version.css_content or ""
        root_match = re.search(r":root\s*\{([^}]+)\}", css_content)
        if root_match:
            for line in root_match.group(1).splitlines():
                line = line.strip()
                if line.startswith("--") and ":" in line:
                    name, _, value = line.partition(":")
                    css_variables[name.strip()] = value.strip().rstrip(";")

        # Extract section headings from HTML
        sections: List[str] = []
        html_content = current_version.html_content or ""
        heading_matches = re.findall(
            r'<(?:h1|h2)[^>]*>([^<]{3,60})</(?:h1|h2)>',
            html_content,
            re.IGNORECASE,
        )
        sections = [h.strip() for h in heading_matches[:8]]

        return {
            "_current_version": current_version,
            "css_variables": css_variables,
            "sections": sections,
            "features": [],
            "design_brief_summary": {},
        }

    # ── Stage 2: Request Decomposition ────────────────────────────────────

    async def _stage2_decompose_request(
        self,
        edit_request: str,
        site_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Use Claude to map the customer's natural-language request to a structured
        list of edit operations.
        """
        css_vars = site_context.get("css_variables", {})
        sections = site_context.get("sections", [])

        css_summary = "\n".join(f"  {k}: {v}" for k, v in css_vars.items()) or "  (none found)"
        sections_summary = "\n".join(f"  - {s}" for s in sections) or "  (none found)"

        prompt = f"""You are a website editing assistant. A customer has submitted a change request for their website.

SITE CONTEXT:
CSS Variables (brand values):
{css_summary}

Page Sections (headings detected):
{sections_summary}

CUSTOMER REQUEST:
\"{edit_request}\"

TASK:
Analyze the customer request and return a JSON object describing exactly what needs to change.
The customer is NOT technical — interpret their intent clearly.

Return ONLY valid JSON (no markdown, no explanation):
{{
  "edit_summary": "One sentence describing the overall change",
  "edit_operations": [
    {{
      "type": "text_change",
      "location": "Hero section — main heading",
      "selector_hint": "h1 in the hero / header section",
      "current_value": "approximate current text if known, or leave empty",
      "new_value": "exact replacement text"
    }},
    {{
      "type": "css_var_change",
      "target_variable": "--color-primary",
      "current_value": "#1e40af",
      "new_value": "#10b981",
      "reason": "customer asked for green color"
    }}
  ],
  "complexity": "simple | moderate | complex",
  "requires_review": true
}}

Operation types:
- text_change: change visible text (headings, paragraphs, button labels, phone numbers, etc.)
- css_var_change: change a CSS variable in :root (colors, fonts, spacing)
- section_add: add a new section (specify content in new_value as HTML description)
- section_remove: remove a section
- image_change: swap an image (describe in new_value)
"""
        try:
            response = await self._client.messages.create(
                model=self.MODEL,
                max_tokens=4096,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
                raw = re.sub(r"```\s*$", "", raw).strip()

            return json.loads(raw)

        except json.JSONDecodeError as e:
            logger.error(f"[SiteEditProcessor] Stage 2 JSON parse error: {e}")
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

    # ── Stage 3: Edit Execution ────────────────────────────────────────────

    async def _stage3_execute_edits(
        self,
        html_content: str,
        css_content: str,
        edit_operations: List[Dict[str, Any]],
    ) -> tuple[str, str]:
        """
        Apply the structured edit operations to the full HTML + CSS using Claude.
        Returns (updated_html, updated_css).
        """
        ops_json = json.dumps(edit_operations, indent=2, ensure_ascii=False)

        prompt = f"""You are a professional web developer making precise, surgical edits to a website.

EDIT OPERATIONS TO APPLY:
{ops_json}

CURRENT HTML:
{html_content[:40000]}

CURRENT CSS:
{css_content[:15000]}

TASK:
Apply EXACTLY the edit operations above — nothing more, nothing less.
Do not add, remove, or restructure any sections or elements beyond what is specified.
Preserve all existing HTML structure, CSS classes, and JavaScript.
For css_var_change operations: update only the matching variable inside :root {{ }}.
For text_change operations: find the closest matching text and replace it with the new_value.

Return ONLY in this format (no explanation):

=== HTML ===
[complete updated HTML]

=== CSS ===
[complete updated CSS]
"""
        try:
            # Use streaming to handle large responses (64k tokens) without timeout
            async with self._client.messages.stream(
                model=self.MODEL,
                max_tokens=64000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                raw = await stream.get_final_text()

            updated_html = html_content
            updated_css = css_content

            if "=== HTML ===" in raw:
                html_start = raw.find("=== HTML ===") + len("=== HTML ===")
                html_end = raw.find("=== CSS ===")
                if html_end == -1:
                    html_end = len(raw)
                updated_html = raw[html_start:html_end].strip()

            if "=== CSS ===" in raw:
                css_start = raw.find("=== CSS ===") + len("=== CSS ===")
                updated_css = raw[css_start:].strip()

            return updated_html, updated_css

        except Exception as e:
            logger.error(f"[SiteEditProcessor] Stage 3 error: {e}")
            return html_content, css_content

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

        # Build updated generation_context
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
