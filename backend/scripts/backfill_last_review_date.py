"""
One-time backfill: populate last_review_date for all existing businesses
that have review timestamps stored in raw_data["reviews_data"].

Safe to run multiple times — skips businesses that already have a value
and businesses whose raw_data contains no individual review dates.

Usage (from /var/www/webmagic/backend):
    source .venv/bin/activate
    python -m scripts.backfill_last_review_date

Optional flags:
    --dry-run        Print counts without writing to the database.
    --batch-size N   Number of businesses to process per DB chunk (default 200).
    --limit N        Stop after updating N businesses (useful for testing).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure the backend package root is on the path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from models.business import Business
from services.activity.analyzer import extract_last_review_date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def backfill(dry_run: bool, batch_size: int, limit: int) -> None:
    async with AsyncSessionLocal() as db:
        total_candidates = await _count_candidates(db)
        logger.info(
            "Businesses with raw_data reviews but no last_review_date: %d",
            total_candidates,
        )

        if dry_run:
            logger.info("DRY RUN — no changes will be written.")
            return

        updated = 0
        skipped = 0
        offset = 0

        while True:
            if limit and updated >= limit:
                logger.info("Reached --limit %d, stopping.", limit)
                break

            batch = await _fetch_batch(db, offset, batch_size)
            if not batch:
                break

            for business in batch:
                reviews_list = _get_reviews_list(business)
                last_date = extract_last_review_date(reviews_list)

                if last_date is None:
                    skipped += 1
                    continue

                await db.execute(
                    update(Business)
                    .where(Business.id == business.id)
                    .values(last_review_date=last_date)
                )
                updated += 1

                if updated % 100 == 0:
                    await db.commit()
                    logger.info("  Committed %d updates so far ...", updated)

            await db.commit()
            offset += batch_size

            if limit and updated >= limit:
                break

        logger.info(
            "Backfill complete: updated=%d, skipped_no_dates=%d",
            updated,
            skipped,
        )


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _count_candidates(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Business.id)).where(
            and_(
                Business.last_review_date.is_(None),
                Business.raw_data.isnot(None),
            )
        )
    )
    return result.scalar() or 0


async def _fetch_batch(
    db: AsyncSession, offset: int, batch_size: int
) -> list[Business]:
    result = await db.execute(
        select(Business)
        .where(
            and_(
                Business.last_review_date.is_(None),
                Business.raw_data.isnot(None),
            )
        )
        .order_by(Business.created_at.desc())
        .offset(offset)
        .limit(batch_size)
    )
    return list(result.scalars().all())


def _get_reviews_list(business: Business) -> list[dict]:
    """Extract the normalised reviews list from raw_data."""
    raw = business.raw_data or {}
    return raw.get("reviews_data") or []


# ── Entry point ───────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill last_review_date for existing businesses."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts without writing to the database.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        metavar="N",
        help="Number of businesses per DB query (default: 200).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Stop after updating N businesses (0 = no limit).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(backfill(dry_run=args.dry_run, batch_size=args.batch_size, limit=args.limit))
