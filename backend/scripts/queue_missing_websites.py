"""
Queue businesses without websites for AI generation.

SAFETY: Use --triple-verified to ONLY queue businesses that have been
triple-verified (raw_data check + Playwright + ScrapingDog) to have no website.
This prevents wasting credits on businesses that actually have websites.

Usage:
    python -m scripts.queue_missing_websites --triple-verified --dry-run  # Safe: only verified
    python -m scripts.queue_missing_websites --triple-verified            # Queue verified only
    python -m scripts.queue_missing_websites --limit 100                  # All eligible (risk)
"""
import asyncio
import argparse
import logging
from core.database import AsyncSessionLocal
from services.hunter.website_generation_queue_service import WebsiteGenerationQueueService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def queue_missing_websites(limit: int = 100, dry_run: bool = False, triple_verified_only: bool = False):
    """Queue qualified businesses without websites for generation."""
    logger.info("=" * 70)
    logger.info("QUEUE MISSING WEBSITES FOR AI GENERATION")
    logger.info("=" * 70)
    if triple_verified_only:
        logger.info("MODE: Triple-verified only (website_validation_status=missing + validated_at set)")

    async with AsyncSessionLocal() as db:
        service = WebsiteGenerationQueueService(db)

        if triple_verified_only:
            businesses = await service.get_triple_verified_businesses_needing_generation(
                limit=limit,
                min_qualification_score=50
            )
        else:
            businesses = await service.get_businesses_needing_generation(
                limit=limit,
                min_qualification_score=50
            )

        if not businesses:
            logger.info("No businesses found needing generation.")
            logger.info("All qualified leads without websites may already be queued.")
            return

        logger.info(f"Found {len(businesses)} businesses needing website generation:")
        for i, biz in enumerate(businesses[:10], 1):
            logger.info(f"  {i}. {biz.name} - {biz.city}, {biz.state} (score: {biz.qualification_score})")
        if len(businesses) > 10:
            logger.info(f"  ... and {len(businesses) - 10} more")

        if dry_run:
            logger.info(f"\n[DRY RUN] Would queue {len(businesses)} businesses. Run without --dry-run to execute.")
            return

        logger.info(f"\nQueuing {len(businesses)} businesses for generation...")
        result = await service.queue_multiple(
            business_ids=[b.id for b in businesses],
            priority=6  # Medium-high priority
        )

        logger.info("=" * 70)
        logger.info(f"Queued: {result['queued']}")
        logger.info(f"Already queued: {result['already_queued']}")
        logger.info(f"Already generated: {result['already_generated']}")
        logger.info(f"Errors: {result['errors']}")
        logger.info("=" * 70)
        logger.info("Celery workers will process these. Check: celery -A celery_app inspect active")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Queue businesses without websites for AI generation")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max businesses to queue (default: 100)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be queued without actually queuing")
    parser.add_argument("--triple-verified", action="store_true",
                        help="Only queue triple-verified businesses (prevents wasting credits)")
    args = parser.parse_args()

    asyncio.run(queue_missing_websites(
        limit=args.limit,
        dry_run=args.dry_run,
        triple_verified_only=args.triple_verified
    ))
