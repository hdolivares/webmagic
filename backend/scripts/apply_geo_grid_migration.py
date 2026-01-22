"""
Apply Geo-Grid Migration

This script applies the geo-grid zone migration to the database.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from core.database import get_db_session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def apply_migration():
    """Apply the geo-grid migration to the database."""
    
    migration_sql = """
-- Add Geo-Grid Zone Support to Coverage Grid
ALTER TABLE coverage_grid 
ADD COLUMN IF NOT EXISTS zone_id VARCHAR(20),
ADD COLUMN IF NOT EXISTS zone_lat VARCHAR(20),
ADD COLUMN IF NOT EXISTS zone_lon VARCHAR(20),
ADD COLUMN IF NOT EXISTS zone_radius_km VARCHAR(10);

-- Add index for zone_id lookups
CREATE INDEX IF NOT EXISTS idx_coverage_grid_zone_id ON coverage_grid(zone_id);
"""
    
    try:
        async with get_db_session() as db:
            logger.info("Applying geo-grid migration...")
            
            # Execute migration
            await db.execute(text(migration_sql))
            await db.commit()
            
            logger.info("✅ Migration applied successfully!")
            logger.info("   Added fields: zone_id, zone_lat, zone_lon, zone_radius_km")
            logger.info("   Added index: idx_coverage_grid_zone_id")
            
            # Verify migration
            result = await db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'coverage_grid' 
                AND column_name IN ('zone_id', 'zone_lat', 'zone_lon', 'zone_radius_km')
            """))
            columns = [row[0] for row in result]
            
            logger.info(f"\n✅ Verified columns exist: {', '.join(columns)}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        return False


async def check_migration_status():
    """Check if migration has already been applied."""
    try:
        async with get_db_session() as db:
            result = await db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'coverage_grid' 
                AND column_name = 'zone_id'
            """))
            exists = result.scalar_one_or_none()
            
            if exists:
                logger.info("✅ Geo-grid migration already applied!")
                return True
            else:
                logger.info("⚠️  Geo-grid migration not yet applied")
                return False
                
    except Exception as e:
        logger.error(f"❌ Failed to check migration status: {str(e)}")
        return False


async def main():
    """Main entry point."""
    logger.info("="*60)
    logger.info("GEO-GRID MIGRATION TOOL")
    logger.info("="*60)
    
    # Check if already applied
    already_applied = await check_migration_status()
    
    if already_applied:
        logger.info("\nMigration already applied. No action needed.")
        return
    
    # Apply migration
    logger.info("\nApplying migration...")
    success = await apply_migration()
    
    if success:
        logger.info("\n" + "="*60)
        logger.info("✅ MIGRATION COMPLETE!")
        logger.info("="*60)
        logger.info("\nYou can now use geo-grid features:")
        logger.info("  • City subdivision into geographic zones")
        logger.info("  • Zone-specific business searches")
        logger.info("  • Complete metropolitan area coverage")
    else:
        logger.info("\n❌ Migration failed. Please check the error above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

