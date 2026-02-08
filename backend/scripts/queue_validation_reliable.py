"""
Queue businesses for website validation using batch tasks.

This script reliably queues validation tasks using the same pattern
as queue_missing_websites.py which has proven to work consistently.

Usage:
    python -m scripts.queue_validation_reliable --limit 100 --dry-run
    python -m scripts.queue_validation_reliable --limit 100
    python -m scripts.queue_validation_reliable --reset-errors  # Reset error statuses first
"""
import asyncio
import argparse
import logging
from core.database import AsyncSessionLocal
from models.business import Business
from sqlalchemy import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def reset_error_businesses():
    """Reset businesses with 'error' status back to 'pending'."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import update
        
        result = await db.execute(
            select(Business)
            .where(Business.website_validation_status == 'error')
            .where(Business.website_url.isnot(None))
            .where(Business.website_url != '')
        )
        businesses = result.scalars().all()
        
        if not businesses:
            logger.info("No businesses with error status found")
            return 0
        
        logger.info(f"Found {len(businesses)} businesses with error status")
        
        # Reset to pending
        for biz in businesses:
            biz.website_validation_status = 'pending'
            biz.website_validated_at = None
            biz.website_validation_result = None
        
        await db.commit()
        logger.info(f"Reset {len(businesses)} businesses to pending status")
        return len(businesses)


async def queue_pending_validations(limit: int = 100, dry_run: bool = False, batch_size: int = 10):
    """Queue pending businesses for validation."""
    logger.info("=" * 70)
    logger.info("QUEUE PENDING BUSINESSES FOR WEBSITE VALIDATION")
    logger.info("=" * 70)
    
    async with AsyncSessionLocal() as db:
        # Find pending businesses
        result = await db.execute(
            select(Business)
            .where(Business.website_validation_status == 'pending')
            .where(Business.website_url.isnot(None))
            .where(Business.website_url != '')
            .limit(limit)
        )
        businesses = result.scalars().all()
        
        if not businesses:
            logger.info("No businesses found needing validation.")
            return
        
        logger.info(f"Found {len(businesses)} businesses needing validation:")
        for i, biz in enumerate(businesses[:10], 1):
            logger.info(f"  {i}. {biz.name} - {biz.city}, {biz.state}")
            logger.info(f"      URL: {biz.website_url}")
        if len(businesses) > 10:
            logger.info(f"  ... and {len(businesses) - 10} more")
        
        if dry_run:
            logger.info(f"\n[DRY RUN] Would queue {len(businesses)} businesses. Run without --dry-run to execute.")
            return
        
        # Import here to avoid early Celery connection
        from tasks.validation_tasks import batch_validate_websites
        
        # Queue in batches
        logger.info(f"\nQueuing {len(businesses)} businesses in batches of {batch_size}...")
        business_ids = [str(b.id) for b in businesses]
        tasks_queued = 0
        
        for i in range(0, len(business_ids), batch_size):
            batch = business_ids[i:i + batch_size]
            batch_validate_websites.delay(batch)
            tasks_queued += 1
            if tasks_queued % 10 == 0:
                logger.info(f"  Queued {tasks_queued} batches ({i + len(batch)} businesses)...")
        
        logger.info("=" * 70)
        logger.info(f"✓ Successfully queued {tasks_queued} validation batches")
        logger.info(f"✓ Total businesses: {len(businesses)}")
        logger.info("=" * 70)
        logger.info("Monitor progress:")
        logger.info("  tail -f /var/log/webmagic/celery.log")
        logger.info("\nCheck validation status:")
        logger.info("  SELECT website_validation_status, COUNT(*)")
        logger.info("  FROM businesses WHERE website_url IS NOT NULL")
        logger.info("  GROUP BY website_validation_status;")


async def main():
    """Main entry point that handles both reset and queuing."""
    parser = argparse.ArgumentParser(description="Queue businesses for website validation")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max businesses to queue (default: 100)")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Batch size for validation tasks (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be queued without actually queuing")
    parser.add_argument("--reset-errors", action="store_true",
                        help="Reset error statuses to pending before queuing")
    args = parser.parse_args()
    
    if args.reset_errors:
        logger.info("Resetting error statuses to pending...")
        reset_count = await reset_error_businesses()
        logger.info(f"Reset {reset_count} businesses")
        logger.info("")
    
    await queue_pending_validations(
        limit=args.limit,
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    asyncio.run(main())
