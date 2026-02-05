"""
Run migration 009: Make html_content nullable
"""
import asyncio
import sys
sys.path.insert(0, '/var/www/webmagic/backend')

from sqlalchemy import text
from core.database import AsyncSessionLocal


async def run_migration():
    """Apply migration 009."""
    async with AsyncSessionLocal() as db:
        try:
            # Make html_content nullable
            await db.execute(text(
                "ALTER TABLE generated_sites ALTER COLUMN html_content DROP NOT NULL"
            ))
            await db.commit()
            print("✅ Migration 009 applied successfully!")
            print("   - html_content is now nullable during generation")
        except Exception as e:
            await db.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_migration())

