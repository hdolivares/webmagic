"""
Clear Website Generation Queue

Resets all businesses in the generation queue (queued/generating) so that
no websites are created until lead data is triple-verified.

This script:
  1. Resets database: website_status='none', generation_queued_at=NULL for queued businesses
  2. Provides instructions to purge Celery queue on server (requires celery purge)

Important: Run this BEFORE verification. After verification, only re-queue
businesses that are triple-verified (raw_data check + Playwright + ScrapingDog).

Usage:
    python -m scripts.clear_generation_queue --dry-run
    python -m scripts.clear_generation_queue --execute
"""
import asyncio
import sys
from pathlib import Path
import argparse
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from core.database import AsyncSessionLocal
from models.business import Business

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def clear_queue(dry_run: bool = True) -> dict:
    """Reset queued/generating businesses to 'none' - removes from generation pipeline."""
    logger.info("=" * 70)
    logger.info("CLEAR WEBSITE GENERATION QUEUE")
    logger.info("=" * 70)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Business).where(
                Business.website_status.in_(["queued", "generating"])
            )
        )
        businesses = result.scalars().all()

        logger.info(f"Found {len(businesses)} businesses in queue (queued or generating)")

        if not businesses:
            logger.info("Nothing to clear")
            return {"cleared": 0}

        for b in businesses[:10]:
            logger.info(f"  - {b.name} ({b.website_status})")
        if len(businesses) > 10:
            logger.info(f"  ... and {len(businesses) - 10} more")

        if dry_run:
            logger.info("")
            logger.info("[DRY RUN] Would clear these. Run with --execute to apply.")
            return {"would_clear": len(businesses)}

        # Reset status
        await db.execute(
            update(Business)
            .where(Business.website_status.in_(["queued", "generating"]))
            .values(
                website_status="none",
                generation_queued_at=None,
                generation_started_at=None,
            )
        )
        await db.commit()

        logger.info(f"Cleared {len(businesses)} businesses from database queue")
        logger.info("")
        logger.info("IMPORTANT: Also purge Celery queue on server:")
        logger.info("  ssh root@104.251.211.183")
        logger.info("  cd /path/to/webmagic/backend  # or your app path")
        logger.info("  celery -A celery_app purge -f   # Purge 'generation' queue")
        logger.info("  # Or purge all: celery -A celery_app purge -f")

        return {"cleared": len(businesses)}


def main():
    parser = argparse.ArgumentParser(description="Clear website generation queue")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true", help="Actually clear the queue")
    args = parser.parse_args()
    dry_run = not args.execute
    asyncio.run(clear_queue(dry_run=dry_run))


if __name__ == "__main__":
    main()
