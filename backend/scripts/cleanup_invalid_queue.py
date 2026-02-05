"""
Cleanup Script: Remove businesses with valid websites from generation queue

This script identifies and removes businesses that were incorrectly queued
for website generation when they already have valid websites.

Run with: python -m scripts.cleanup_invalid_queue
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from core.database import AsyncSessionLocal
from models.business import Business
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cleanup_queue():
    """Remove businesses with valid websites from generation queue."""
    
    async with AsyncSessionLocal() as db:
        try:
            # Find businesses that are queued but have valid websites
            result = await db.execute(
                select(Business).where(
                    Business.website_status == 'queued',
                    Business.website_validation_status == 'valid'
                )
            )
            businesses = result.scalars().all()
            
            if not businesses:
                logger.info("✅ No incorrectly queued businesses found")
                return
            
            logger.info(f"Found {len(businesses)} businesses with valid websites in queue:")
            
            for business in businesses:
                logger.info(
                    f"  - {business.name} ({business.city}, {business.state})\n"
                    f"    Website: {business.website_url}\n"
                    f"    Status: {business.website_validation_status}"
                )
            
            # Ask for confirmation
            response = input(f"\nRemove these {len(businesses)} from queue? (yes/no): ")
            
            if response.lower() != 'yes':
                logger.info("Aborted by user")
                return
            
            # Remove from queue by resetting queue fields
            await db.execute(
                update(Business)
                .where(
                    Business.website_status == 'queued',
                    Business.website_validation_status == 'valid'
                )
                .values(
                    website_status='none',  # Reset to none
                    generation_queued_at=None,
                    generation_attempts=0
                )
            )
            
            await db.commit()
            logger.info(f"✅ Successfully removed {len(businesses)} businesses from queue")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(cleanup_queue())

