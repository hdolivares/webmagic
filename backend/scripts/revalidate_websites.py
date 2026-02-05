"""
Re-validate websites marked as invalid

Many websites were marked invalid due to 403/429 errors (anti-bot protection).
This script re-validates them with proper user-agent and retry logic.

Run with: python -m scripts.revalidate_websites
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.business import Business
from services.hunter.website_validation_service import WebsiteValidationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def revalidate_invalid_websites():
    """Re-validate businesses marked as invalid."""
    
    async with AsyncSessionLocal() as db:
        try:
            # Find businesses marked as invalid
            result = await db.execute(
                select(Business).where(
                    Business.website_validation_status == 'invalid',
                    Business.website_url.is_not(None)
                )
            )
            businesses = result.scalars().all()
            
            if not businesses:
                logger.info("✅ No invalid websites to revalidate")
                return
            
            logger.info(f"Found {len(businesses)} businesses with invalid status")
            logger.info("Re-validating with improved logic (proper user-agent, 403/429 handling)...")
            
            revalidated = 0
            now_valid = 0
            still_invalid = 0
            
            async with WebsiteValidationService(db) as validation_service:
                for business in businesses:
                    try:
                        logger.info(f"  Validating: {business.name} - {business.website_url}")
                        
                        validation_result = await validation_service.validate_business_website(
                            {
                                "id": str(business.id),
                                "name": business.name,
                                "website_url": business.website_url,
                                "gmb_place_id": business.gmb_place_id
                            },
                            store_result=True
                        )
                        
                        # Update business with new validation status
                        business.website_validation_status = validation_result.status
                        from datetime import datetime
                        business.website_validated_at = datetime.utcnow()
                        
                        if validation_result.status == 'valid':
                            now_valid += 1
                            logger.info(f"    ✅ Now VALID!")
                            
                            # Remove from queue if it was queued
                            if business.website_status == 'queued':
                                business.website_status = 'none'
                                business.generation_queued_at = None
                                business.generation_attempts = 0
                                logger.info(f"    Removed from generation queue")
                        else:
                            still_invalid += 1
                            logger.info(f"    ❌ Still invalid: {validation_result.status}")
                        
                        revalidated += 1
                        
                        # Commit every 10 to avoid losing progress
                        if revalidated % 10 == 0:
                            await db.commit()
                            logger.info(f"  Progress: {revalidated}/{len(businesses)}")
                        
                    except Exception as e:
                        logger.error(f"    Error validating {business.name}: {e}")
                        still_invalid += 1
                        continue
            
            # Final commit
            await db.commit()
            
            logger.info("\n" + "="*60)
            logger.info(f"✅ Revalidation complete!")
            logger.info(f"  Total processed: {revalidated}")
            logger.info(f"  Now valid: {now_valid}")
            logger.info(f"  Still invalid: {still_invalid}")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Error during revalidation: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(revalidate_invalid_websites())

