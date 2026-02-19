#!/usr/bin/env python3
"""
Reset businesses stuck with placeholder-valid-website.com back into the
discovery pipeline so ScrapingDog can properly validate them.

Root cause: cleanup_validation_statuses.py set website_url to a fake URL to
block further generation attempts. discover_missing_websites_v2 skips any
business that already has a website_url set, so these businesses were
permanently frozen out of the pipeline.

Fix:
  1. Clear website_url back to None
  2. Set website_validation_status = 'needs_discovery'
  3. Clear website_validation_result / website_validated_at
  4. Queue discover_missing_websites_v2 for each business (sorted high-score first)

Usage:
  python reset_placeholder_businesses.py           # dry run
  python reset_placeholder_businesses.py --execute # actually run
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_session_sync
from models.business import Business
from celery_app import celery_app

PLACEHOLDER_URL = "https://placeholder-valid-website.com"
BATCH_SIZE = 20
DRY_RUN = "--execute" not in sys.argv


def main():
    print("=" * 70)
    print("RESET PLACEHOLDER BUSINESSES -> DISCOVERY PIPELINE")
    print("=" * 70)

    with get_db_session_sync() as db:
        businesses = (
            db.query(Business)
            .filter(
                Business.website_url == PLACEHOLDER_URL,
                Business.website_validation_status == "valid",
                Business.country == "US",
            )
            .order_by(Business.qualification_score.desc())
            .all()
        )

        total = len(businesses)
        eligible = [b for b in businesses if (b.qualification_score or 0) >= 70]

        print(f"\nFound {total} placeholder US businesses total")
        print(f"  Score >= 70 (priority): {len(eligible)}")
        print(f"  Score <  70 (low tier): {total - len(eligible)}")
        print(f"\nProcessing order: highest score first  |  batch size: {BATCH_SIZE}")

        if DRY_RUN:
            print(f"\n[DRY RUN] -- pass --execute to actually run\n")
            print("Top 15 that would be reset:")
            for b in businesses[:15]:
                print(
                    f"  [{b.qualification_score or 0:3.0f}] {b.name}"
                    f"  ({b.city}, {b.state})"
                )
            if total > 15:
                print(f"  ... and {total - 15} more")
            return

        # ---- LIVE RUN ----
        print(f"\nResetting {total} business records...")

        failed_ids = []
        for i, business in enumerate(businesses):
            try:
                business.website_url = None
                business.website_validation_status = "needs_discovery"
                business.website_validation_result = None
                business.website_validated_at = None
                # Leave website_metadata intact; discovery_attempts is already
                # {} for these records so has_attempted_scrapingdog() = False
            except Exception as exc:
                print(f"  FAIL reset {business.id} ({business.name}): {exc}")
                failed_ids.append(str(business.id))
                continue

            if (i + 1) % BATCH_SIZE == 0:
                db.commit()
                print(f"  ... committed batch up to #{i + 1}")

        db.commit()
        print(f"All {total} records reset in DB.\n")

        # Re-query IDs that were successfully reset
        reset_ids = [
            str(row.id)
            for row in db.query(Business.id).filter(
                Business.website_url.is_(None),
                Business.website_validation_status == "needs_discovery",
                Business.country == "US",
            ).all()
        ]

        print(f"Queuing {len(reset_ids)} discovery tasks...")
        task_name = "tasks.discovery.discover_missing_websites_v2"
        queued = 0
        queue_failed = 0

        for i, business_id in enumerate(reset_ids):
            try:
                celery_app.send_task(
                    task_name,
                    args=[business_id],
                    queue="discovery",
                )
                queued += 1
            except Exception as exc:
                print(f"  FAIL queue {business_id}: {exc}")
                queue_failed += 1

            if (i + 1) % BATCH_SIZE == 0:
                print(f"  ... queued {i + 1}/{len(reset_ids)}")

        print()
        print("=" * 70)
        print("DONE")
        print(f"  DB records reset:       {total - len(failed_ids)}")
        print(f"  DB reset failures:      {len(failed_ids)}")
        print(f"  Discovery tasks queued: {queued}")
        print(f"  Queue failures:         {queue_failed}")
        print("=" * 70)
        print()
        print("Monitor progress with:")
        print(
            "  tail -f /var/log/webmagic/celery.log"
            " | grep -E 'discover|ScrapingDog|country|GEO'"
        )


if __name__ == "__main__":
    main()
