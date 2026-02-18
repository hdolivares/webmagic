"""
Migration 006: Add generation_context JSONB column to site_versions

Stores structured metadata from site generation (CSS variables, sections,
design_brief summary) to power the AI site edit pipeline without needing
to re-parse HTML/CSS on each edit.

Applied: 2026-02-18
"""
from sqlalchemy import text


async def upgrade(conn):
    await conn.execute(text(
        "ALTER TABLE site_versions ADD COLUMN IF NOT EXISTS generation_context JSONB"
    ))


async def downgrade(conn):
    await conn.execute(text(
        "ALTER TABLE site_versions DROP COLUMN IF EXISTS generation_context"
    ))
