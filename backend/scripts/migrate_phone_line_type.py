"""
One-time migration: add phone_line_type and phone_lookup_at columns to businesses.

Run with: python scripts/migrate_phone_line_type.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def run():
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Load from .env
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
        url = os.environ.get("DATABASE_URL")

    engine = create_async_engine(url, echo=True)

    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS "
            "phone_line_type VARCHAR(20) DEFAULT NULL"
        ))
        await conn.execute(text(
            "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS "
            "phone_lookup_at TIMESTAMP DEFAULT NULL"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_businesses_phone_line_type "
            "ON businesses(phone_line_type)"
        ))
        print("Migration complete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
