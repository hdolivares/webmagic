"""
Generate websites for the 8 confirmed businesses without websites.
"""
import asyncio
import logging
from datetime import datetime
from core.database import AsyncSessionLocal
from models.business import Business
from tasks.generation_sync import generate_website_for_business
from sqlalchemy import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def generate_confirmed_businesses():
    """Generate websites for businesses confirmed without websites."""
    logger.info("="*80)
    logger.info("GENERATING WEBSITES FOR CONFIRMED BUSINESSES")
    logger.info("="*80)
    
    async with AsyncSessionLocal() as db:
        # Get the 8 confirmed businesses
        query = select(Business).where(
            Business.website_validation_status == "missing",
            Business.country == "US",
            Business.website_status == "queued"
        ).order_by(Business.rating.desc(), Business.review_count.desc())
        
        result = await db.execute(query)
        businesses = result.scalars().all()
        
        if not businesses:
            logger.info("No confirmed businesses found for generation.")
            return
        
        logger.info(f"Found {len(businesses)} businesses to generate websites for:")
        for i, biz in enumerate(businesses, 1):
            logger.info(f"  {i}. {biz.name} - {biz.city}, {biz.state} ({biz.rating}⭐, {biz.review_count} reviews)")
        
        logger.info("\n" + "="*80)
        logger.info("Starting generation tasks...")
        logger.info("="*80 + "\n")
        
        for i, business in enumerate(businesses, 1):
            logger.info(f"[{i}/{len(businesses)}] Queuing generation for: {business.name}")
            try:
                # Queue the Celery task
                from tasks.generation_sync import generate_website_for_business
                task = generate_website_for_business.delay(str(business.id))
                logger.info(f"  ✅ Task queued: {task.id}")
                
                # Update generation_started_at to prevent duplicate processing
                business.generation_started_at = datetime.utcnow()
                await db.commit()
                
            except Exception as e:
                logger.error(f"  ❌ Error queuing {business.name}: {e}")
        
        logger.info("\n" + "="*80)
        logger.info(f"✅ Queued {len(businesses)} businesses for generation!")
        logger.info("="*80)
        logger.info("\nGeneration tasks are now running in Celery workers.")
        logger.info("Monitor progress: tail -f /var/log/webmagic/celery.log")

if __name__ == "__main__":
    asyncio.run(generate_confirmed_businesses())


