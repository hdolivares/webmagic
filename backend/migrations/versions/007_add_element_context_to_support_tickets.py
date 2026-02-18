"""
Migration 007: Add element_context JSONB column to support_tickets

Stores a snapshot of the DOM element the customer selected using the
visual element picker in the ticket creation form.

Fields stored (all optional):
  css_selector    — shortest unique CSS selector for the target element
  tag             — HTML tag name (h1, section, button, …)
  id              — element id attribute (if present)
  classes         — list of class names
  text_content    — visible text, truncated at 300 chars
  html            — outerHTML, truncated at 600 chars
  dom_path        — human-readable ancestry breadcrumb
  computed_styles — font-size, color, background-color, font-weight, …
  bounding_box    — { top, left, width, height } in viewport pixels
  captured_at     — ISO timestamp

Consumed by: SiteEditProcessor._stage2_decompose_request
"""
from sqlalchemy import text


async def upgrade(conn):
    await conn.execute(text(
        "ALTER TABLE support_tickets ADD COLUMN IF NOT EXISTS element_context JSONB"
    ))


async def downgrade(conn):
    await conn.execute(text(
        "ALTER TABLE support_tickets DROP COLUMN IF EXISTS element_context"
    ))
