"""
Add updated_at column to edit_requests table.

This fixes the missing updated_at column that BaseModel expects.
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


async def main():
    """Add updated_at column to edit_requests."""
    engine = create_async_engine(settings.DATABASE_URL)
    
    print("=" * 70)
    print("Adding updated_at column to edit_requests table")
    print("=" * 70)
    print()
    
    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='edit_requests' AND column_name='updated_at'
        """))
        
        if result.fetchone():
            print("✅ updated_at column already exists")
        else:
            # Add the column
            await conn.execute(text("""
                ALTER TABLE edit_requests 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            """))
            print("✅ Added updated_at column to edit_requests")
    
    await engine.dispose()
    print()
    print("Migration complete!")


if __name__ == "__main__":
    asyncio.run(main())
