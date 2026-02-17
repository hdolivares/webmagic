"""
Run migration 017: Add short_url column to generated_sites.

Uses SQLAlchemy to execute the migration SQL against the remote database.
"""
import asyncio
import logging
from sqlalchemy import text
from core.database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Migration SQL split into separate statements for asyncpg
MIGRATION_STATEMENTS = [
    # Step 1: Add column
    """
    ALTER TABLE generated_sites
    ADD COLUMN IF NOT EXISTS short_url VARCHAR(255) NULL
    """,
    
    # Step 2: Add index
    """
    CREATE INDEX IF NOT EXISTS idx_generated_sites_short_url
    ON generated_sites(short_url)
    """,
    
    # Step 3: Backfill existing sites
    """
    UPDATE generated_sites gs
    SET short_url = (
        SELECT CONCAT('https://lvsh.cc/', sl.slug)
        FROM short_links sl
        WHERE sl.site_id = gs.id
          AND sl.is_active = true
          AND sl.link_type = 'site_preview'
        ORDER BY sl.created_at DESC
        LIMIT 1
    )
    WHERE gs.short_url IS NULL
      AND EXISTS (
        SELECT 1 FROM short_links sl
        WHERE sl.site_id = gs.id
          AND sl.is_active = true
      )
    """
]


async def run_migration():
    """Execute migration 017."""
    logger.info("Starting migration 017: Add short_url to generated_sites")
    
    async for db in get_db():
        try:
            # Execute migration statements one by one
            for i, statement in enumerate(MIGRATION_STATEMENTS, 1):
                logger.info(f"Executing step {i}/{len(MIGRATION_STATEMENTS)}...")
                await db.execute(text(statement))
            
            await db.commit()
            logger.info("✅ Migration 017 completed successfully!")
            
            # Verify migration
            result = await db.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'generated_sites'
                  AND column_name = 'short_url';
            """))
            column_exists = result.scalar()
            
            if column_exists:
                logger.info("✅ Verified: short_url column exists")
            else:
                logger.error("❌ Verification failed: short_url column not found")
                return False
            
            # Check index
            result = await db.execute(text("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE indexname = 'idx_generated_sites_short_url';
            """))
            index_exists = result.scalar()
            
            if index_exists:
                logger.info("✅ Verified: Index created")
            else:
                logger.error("❌ Verification failed: Index not found")
                return False
            
            # Show stats
            result = await db.execute(text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(short_url) as with_url,
                    COUNT(*) - COUNT(short_url) as without_url
                FROM generated_sites
                WHERE status = 'completed';
            """))
            row = result.first()
            
            logger.info("\n" + "=" * 60)
            logger.info("Migration Statistics:")
            logger.info(f"  Total completed sites: {row[0]}")
            logger.info(f"  Sites with short_url: {row[1]}")
            logger.info(f"  Sites needing backfill: {row[2]}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}", exc_info=True)
            await db.rollback()
            return False
        finally:
            await db.close()
            break


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
