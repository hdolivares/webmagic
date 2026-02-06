"""
Test script to manually trigger generation queueing for debugging.
"""
import asyncio
import logging
from uuid import UUID
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.business import Business
from services.hunter.website_generation_queue_service import WebsiteGenerationQueueService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_queue_generation():
    """Test queueing a business for generation."""
    async with AsyncSessionLocal() as db:
        # Get the most recent business that needs generation
        result = await db.execute(
            select(Business).where(
                Business.website_validation_status == 'missing',
                Business.generation_queued_at.isnot(None)
            ).order_by(Business.generation_queued_at.desc()).limit(1)
        )
        business = result.scalar_one_or_none()
        
        if not business:
            logger.error("No businesses found needing generation")
            return
        
        logger.info(f"Found business: {business.name} (ID: {business.id})")
        logger.info(f"  - website_validation_status: {business.website_validation_status}")
        logger.info(f"  - generation_queued_at: {business.generation_queued_at}")
        logger.info(f"  - generation_started_at: {business.generation_started_at}")
        logger.info(f"  - generation_attempts: {business.generation_attempts}")
        logger.info(f"  - website_status: {business.website_status}")
        
        # Reset the queued status to test again
        business.generation_queued_at = None
        business.generation_attempts = 0
        business.website_status = 'none'
        await db.commit()
        logger.info("Reset business status for testing")
        
        # Now try to queue it
        service = WebsiteGenerationQueueService(db)
        logger.info(f"\nAttempting to queue business {business.id}...")
        
        try:
            result = await service.queue_for_generation(business.id, priority=7)
            logger.info(f"Queue result: {result}")
            
            # Check if task was actually created in Redis
            import subprocess
            redis_result = subprocess.run(
                ['redis-cli', '-h', '127.0.0.1', '-p', '6379', 'llen', 'generation'],
                capture_output=True,
                text=True
            )
            logger.info(f"Redis generation queue length: {redis_result.stdout.strip()}")
            
        except Exception as e:
            logger.error(f"Exception during queueing: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_queue_generation())

