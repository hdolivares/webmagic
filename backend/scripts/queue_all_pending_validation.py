"""
Queue all pending businesses for LLM validation.
Uses the same pattern as queue_missing_websites.py for reliable execution.

Usage:
    python -m scripts.queue_all_pending_validation --limit 500 --dry-run
    python -m scripts.queue_all_pending_validation --limit 500
"""
import asyncio
import argparse
import logging
from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.business import Business

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def queue_pending_validations(limit: int = 500, dry_run: bool = False, batch_size: int = 10):
    """Queue pending businesses for LLM validation."""
    logger.info("=" * 70)
    logger.info("QUEUE PENDING BUSINESSES FOR LLM VALIDATION")
    logger.info("=" * 70)

    async with AsyncSessionLocal() as db:
        # Find businesses with pending validation
        result = await db.execute(
            select(Business)
            .where(
                Business.website_url.isnot(None),
                Business.website_url != "",
                Business.website_validation_status == "pending"
            )
            .order_by(Business.website_validated_at.asc().nullsfirst())
            .limit(limit)
        )
        businesses = result.scalars().all()

        if not businesses:
            logger.info("No pending businesses found!")
            return

        logger.info(f"Found {len(businesses)} businesses needing validation:")
        for i, biz in enumerate(businesses[:10], 1):
            logger.info(f"  {i}. {biz.name} - {biz.city}, {biz.state}")
            logger.info(f"      URL: {biz.website_url[:80]}...")
        if len(businesses) > 10:
            logger.info(f"  ... and {len(businesses) - 10} more")

        if dry_run:
            logger.info(f"\n[DRY RUN] Would queue {len(businesses)} businesses. Run without --dry-run to execute.")
            return

        # Lazy import to avoid early Celery broker connection
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
        logger.info("  SELECT website_validation_status, COUNT(*) FROM businesses GROUP BY website_validation_status;")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Queue pending businesses for LLM validation")
    parser.add_argument("--limit", type=int, default=500,
                        help="Max businesses to queue (default: 500)")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Batch size for queueing (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be queued without actually queuing")
    args = parser.parse_args()

    asyncio.run(queue_pending_validations(
        limit=args.limit,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    ))
