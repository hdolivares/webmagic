"""
One-time backfill script: populate ``business_status`` and
``last_review_date`` columns from ``raw_data`` for existing records.

Background
----------
Both columns were added after the initial scrape runs, so historical records
have ``NULL`` in those columns even though the data is already stored inside
the ``raw_data`` JSONB field.  This script reads from ``raw_data`` and writes
the extracted values to the dedicated columns so the filtering logic that
relies on them (``analyzer.compute_activity_status`` and the early-exit
guards in the Celery tasks) works correctly for all businesses.

What is backfilled
------------------
``business_status``
    Copied directly from ``raw_data['business_status']``.
    Only updated when the column is currently NULL.

``last_review_date``
    Extracted from ``raw_data['reviews_data']`` — a list of review dicts
    each containing a ``review_datetime_utc`` or ``date`` key.  The newest
    parsed date is stored.  Only updated when the column is currently NULL.

Usage (run from /var/www/webmagic/backend)
------------------------------------------
    # Dry run — prints what would change, writes nothing
    python scripts/backfill_business_fields.py --dry-run

    # Live run
    python scripts/backfill_business_fields.py
"""
import sys
import os
import argparse
import logging
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import celery_app  # noqa: F401 — must be imported first to bind shared_task decorators
from core.database import get_db_session_sync
from models.business import Business
from services.activity.analyzer import extract_last_review_date

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _extract_review_date_from_raw(raw_data: dict) -> Optional[datetime]:
    """
    Extract the most recent review date from the ``reviews_data`` list stored
    in ``raw_data``.

    Outscraper stores reviews under ``reviews_data`` as a list of dicts with a
    ``review_datetime_utc`` key (ISO-8601 string).  We normalise each entry to
    the format expected by ``extract_last_review_date`` (which reads the
    ``date`` key) so the same parsing logic is reused.
    """
    reviews_raw = raw_data.get("reviews_data")
    if not reviews_raw or not isinstance(reviews_raw, list):
        return None

    normalised = []
    for review in reviews_raw:
        if not isinstance(review, dict):
            continue
        date_str = (
            review.get("review_datetime_utc")
            or review.get("date")
            or review.get("timestamp")
        )
        if date_str:
            normalised.append({"date": str(date_str)})

    return extract_last_review_date(normalised)


def run_backfill(dry_run: bool = False) -> None:
    status_updated = 0
    status_skipped = 0
    review_date_updated = 0
    review_date_skipped = 0
    total = 0

    with get_db_session_sync() as db:
        businesses = db.query(Business).all()
        total = len(businesses)
        print(f"Total businesses: {total}")

        for biz in businesses:
            raw = biz.raw_data or {}

            # ── business_status ───────────────────────────────────────────────
            if biz.business_status is None:
                raw_status = raw.get("business_status")
                if raw_status:
                    if dry_run:
                        print(
                            f"  [DRY] {biz.name!r} business_status: NULL → {raw_status!r}"
                        )
                    else:
                        biz.business_status = raw_status
                    status_updated += 1
                else:
                    status_skipped += 1
            else:
                status_skipped += 1

            # ── last_review_date ──────────────────────────────────────────────
            if biz.last_review_date is None:
                extracted_date = _extract_review_date_from_raw(raw)
                if extracted_date:
                    if dry_run:
                        print(
                            f"  [DRY] {biz.name!r} last_review_date: NULL → {extracted_date.isoformat()}"
                        )
                    else:
                        biz.last_review_date = extracted_date
                    review_date_updated += 1
                else:
                    review_date_skipped += 1
            else:
                review_date_skipped += 1

        if not dry_run:
            db.commit()

    action = "Would update" if dry_run else "Updated"
    print(
        f"\n{'DRY RUN — ' if dry_run else ''}{action}:\n"
        f"  business_status:   {status_updated} records\n"
        f"  last_review_date:  {review_date_updated} records\n"
        f"Skipped (already set or no data in raw_data):\n"
        f"  business_status:   {status_skipped}\n"
        f"  last_review_date:  {review_date_skipped}\n"
        f"Total businesses scanned: {total}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to the database.",
    )
    args = parser.parse_args()
    run_backfill(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
