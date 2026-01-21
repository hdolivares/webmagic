"""
Add grace_period_ends column to sites table.

Phase 3 addition for failed payment handling.

Run: python backend/scripts/add_grace_period_column.py

Author: WebMagic Team
Date: January 21, 2026
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from core.config import get_settings

settings = get_settings()


async def add_grace_period_column():
    """Add grace_period_ends column to sites table."""
    engine = create_async_engine(settings.DATABASE_URL)
    
    print("=" * 70)
    print("Adding grace_period_ends column to sites table")
    print("=" * 70)
    print()
    
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE sites 
            ADD COLUMN IF NOT EXISTS grace_period_ends TIMESTAMP WITH TIME ZONE;
        """))
        
        print("✅ Column grace_period_ends added to sites table")
    
    await engine.dispose()
    print()
    print("Migration complete!")
    print()


if __name__ == "__main__":
    asyncio.run(add_grace_period_column())
