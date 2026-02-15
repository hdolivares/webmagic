"""
Queue all pending businesses for validation.
This script finds businesses stuck in 'pending' status and queues them for Playwright+LLM validation.
"""
import asyncio
import logging
from sqlalchemy import select
from core.database import get_db
from models.business import Business
from tasks.validation_tasks import batch_validate_websites

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def queue_pending_validations(batch_size: int = 10, dry_run: bool = False):
    """
    Queue all businesses with 'pending' validation status.
    
    Args:
        batch_size: Number of businesses to queue per batch
        dry_run: If True, only count businesses without queuing
    """
    async for db in get_db():
        try:
            # Get all pending businesses
            result = await db.execute(
                select(Business)
                .where(Business.website_validation_status == 'pending')
                .order_by(Business.created_at.desc())
            )
            pending_businesses = result.scalars().all()
            
            total = len(pending_businesses)
            logger.info(f"Found {total} businesses with pending validation status")
            
            if dry_run:
                logger.info("DRY RUN - No tasks queued")
                return total
            
            # Queue in batches
            queued = 0
            for i in range(0, total, batch_size):
                batch = pending_businesses[i:i+batch_size]
                business_ids = [str(b.id) for b in batch]
                
                try:
                    batch_validate_websites.delay(business_ids)
                    queued += len(business_ids)
                    logger.info(f"Queued batch {i//batch_size + 1}: {len(business_ids)} businesses (Total: {queued}/{total})")
                except Exception as e:
                    logger.error(f"Failed to queue batch {i//batch_size + 1}: {e}")
            
            logger.info(f"✅ Successfully queued {queued}/{total} businesses for validation")
            return queued
            
        except Exception as e:
            logger.error(f"Error queuing pending validations: {e}", exc_info=True)
            raise
        finally:
            break  # Exit async for loop


if __name__ == "__main__":
    import sys
    
    dry_run = "--dry-run" in sys.argv
    batch_size = 10
    
    # Parse batch size from args
    for arg in sys.argv:
        if arg.startswith("--batch-size="):
            batch_size = int(arg.split("=")[1])
    
    print(f"{'DRY RUN: ' if dry_run else ''}Queueing pending validations (batch size: {batch_size})...")
    result = asyncio.run(queue_pending_validations(batch_size=batch_size, dry_run=dry_run))
    print(f"Done! {'Would queue' if dry_run else 'Queued'} {result} businesses")
