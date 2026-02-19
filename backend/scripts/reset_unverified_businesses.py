#!/usr/bin/env python3
"""
Reset businesses that were marked as confirmed_missing or confirmed_no_website
WITHOUT ScrapingDog ever running on them.

These businesses came through an older pipeline that stamped them as having no
website based only on Outscraper data, skipping the ScrapingDog Google-search
double-check entirely.  They need to be re-queued for discovery so we don't
generate sites for businesses that might actually have websites.

Targets:
  - confirmed_missing  + empty metadata         (15 records)
  - confirmed_missing  + metadata but no SD run  (6 records)
  - confirmed_no_website + metadata but no SD run (14 records)

Usage:
  python reset_unverified_businesses.py           # dry run
  python reset_unverified_businesses.py --execute # live run
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import and_, or_, text
from core.database import get_db_session_sync
from models.business import Business
from celery_app import celery_app

DRY_RUN = "--execute" not in sys.argv
TASK_NAME = "tasks.discovery.discover_missing_websites_v2"
QUEUE = "discovery"
BATCH_SIZE = 20

# Already-generated businesses must not be reset
EXCLUDE_STATUSES = ("completed", "generating", "queued")


def _needs_scrapingdog(b: Business) -> bool:
    """Return True if this business skipped ScrapingDog and needs it run."""
    meta = b.website_metadata or {}
    attempts = meta.get("discovery_attempts", {})
    sd = attempts.get("scrapingdog", {})
    return not sd.get("attempted", False)


def main():
    print("=" * 70)
    print("RESET UNVERIFIED BUSINESSES -> SCRAPINGDOG DISCOVERY")
    print("=" * 70)

    with get_db_session_sync() as db:
        # Get IDs of already-generated businesses so we exclude them
        from models.site import GeneratedSite
        from sqlalchemy import select

        generated_ids_result = db.execute(
            select(GeneratedSite.business_id).where(
                GeneratedSite.status.in_(EXCLUDE_STATUSES)
            )
        )
        generated_ids = {row[0] for row in generated_ids_result}

        candidates = (
            db.query(Business)
            .filter(
                Business.country == "US",
                Business.website_url.is_(None),
                Business.website_validation_status.in_(
                    ["confirmed_missing", "confirmed_no_website"]
                ),
                ~Business.id.in_(generated_ids),
            )
            .order_by(Business.qualification_score.desc())
            .all()
        )

        # Further filter: only those that skipped ScrapingDog
        to_reset = [b for b in candidates if _needs_scrapingdog(b)]
        already_verified = [b for b in candidates if not _needs_scrapingdog(b)]

        print(f"\nFound {len(candidates)} candidates total")
        print(f"  Already ScrapingDog-verified: {len(already_verified)}  (no action needed)")
        print(f"  Skipped ScrapingDog:          {len(to_reset)}  <-- will be reset")

        if DRY_RUN:
            print(f"\n[DRY RUN] -- pass --execute to actually run\n")
            print("Businesses that would be reset:")
            for b in to_reset:
                print(
                    f"  [{b.qualification_score or 0:3.0f}] {b.website_validation_status:<22}"
                    f"  {b.name}  ({b.city}, {b.state})"
                )
            return

        # ---- LIVE RUN ----
        print(f"\nResetting {len(to_reset)} records to needs_discovery...")

        failed = []
        for i, b in enumerate(to_reset):
            try:
                b.website_validation_status = "needs_discovery"
                b.website_validation_result = None
                b.website_validated_at = None
                # Keep website_metadata as-is; discovery_attempts.scrapingdog
                # is absent/False so has_attempted_scrapingdog() = False
            except Exception as exc:
                print(f"  FAIL reset {b.id} ({b.name}): {exc}")
                failed.append(b.id)

            if (i + 1) % BATCH_SIZE == 0:
                db.commit()
                print(f"  ... committed batch up to #{i + 1}")

        db.commit()
        print(f"All {len(to_reset)} records reset.\n")

        # Queue discovery tasks
        print(f"Queuing {len(to_reset)} discovery tasks...")
        queued = 0
        queue_failed = 0
        for i, b in enumerate(to_reset):
            if b.id in failed:
                continue
            try:
                celery_app.send_task(TASK_NAME, args=[str(b.id)], queue=QUEUE)
                queued += 1
            except Exception as exc:
                print(f"  FAIL queue {b.id}: {exc}")
                queue_failed += 1

            if (i + 1) % BATCH_SIZE == 0:
                print(f"  ... queued {i + 1}/{len(to_reset)}")

        print()
        print("=" * 70)
        print("DONE")
        print(f"  DB records reset:       {len(to_reset) - len(failed)}")
        print(f"  DB reset failures:      {len(failed)}")
        print(f"  Discovery tasks queued: {queued}")
        print(f"  Queue failures:         {queue_failed}")
        print("=" * 70)
        print()
        print("Monitor:")
        print("  tail -f /var/log/webmagic/celery.log | grep -E 'discover|ScrapingDog'")


if __name__ == "__main__":
    main()
