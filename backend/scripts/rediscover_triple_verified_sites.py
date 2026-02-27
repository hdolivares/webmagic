#!/usr/bin/env python3
"""
Re-run ScrapingDog discovery on US businesses that were marked triple_verified
by the OLD pipeline (before Outscraper was integrated).

These businesses have raw_data = NULL, meaning Outscraper was never run on them.
Their triple_verified status was set by an earlier, less reliable pipeline that
may have missed real websites.

Only targets US businesses (campaigns are US-only — no point spending credits
on international businesses).

After discovery+validation, any business found to have a real website will:
  1. Get website_validation_status = valid_scrapingdog
  2. Have its generated_site.status updated to 'superseded' by the post-run
     SQL at the bottom of this script (run manually after Celery tasks complete).

Usage:
  python rediscover_triple_verified_sites.py           # dry run
  python rediscover_triple_verified_sites.py --execute # live run
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import get_db_session_sync
from models.business import Business
from models.site import GeneratedSite
from celery_app import celery_app

DRY_RUN = "--execute" not in sys.argv
TASK_NAME = "tasks.discovery.discover_missing_websites_v2"
QUEUE = "discovery"

# The 25 US triple_verified businesses with generated sites
# (A-1 Plumbing Co. already fixed manually — excluded here)
TARGET_BUSINESS_IDS = [
    "c3d4e024-4430-4a5b-ab20-39daec56ff41",  # 24/7 Plumber Mr Rooter - NY
    "d0530b7d-c4b9-462a-96a4-c911859f914f",  # A & M Plumbing Repair LLC - FL
    "991456a3-37b1-4e3a-81be-87e89e69a9b6",  # Alert Plumbing Heat and Air - OK
    "2d98d1a8-4c7f-4015-99be-c57c938a88e1",  # Apple Plumbing LLC - TX
    "362efff0-5952-4f34-8ae5-79a3487321b5",  # Beetz Jos H Plumbing Co Inc - MO
    "018366de-5ff1-4ae1-95cb-4f5295a38359",  # Caden's Plumbers - CA
    "7c88c2c6-2572-4288-a39f-7ce66cb79959",  # Einstein's Plumbing and Heating - NY
    "fc96e5c6-37a2-4304-8b32-0c6b6f41ac03",  # Goin Plumbing - IN
    "d89f3734-b970-47cf-8799-f91829d03c70",  # Higdon Service Heating Cooling Plumbing - AL
    "1e306b58-abe5-4fd0-b52d-93343ec6b02b",  # Homestead Plumbing and Heating - CO
    "dcfac76d-68af-4312-9b41-dd35db3690c7",  # Lee's Plumbing - OK
    "76902318-5475-423f-aaa8-3ed4b4fcdc52",  # Louisiana Hydro Blast Solutions LLC - LA
    "4e00a261-d142-4099-b6e8-cf0edea18f61",  # Mister Sewer Plumbing & HVAC - PA
    "fa35cfad-07fe-4762-bab4-94ee448e0af6",  # Nix Plumbing - unknown/US
    "fe955ad3-9e62-4e1c-9670-509423a0cf9f",  # NYC Plumbing Heating Drain Cleaning - NY
    "2b73d830-b68a-4e6d-badc-cdea7f89dec7",  # PENASCINO PLUMBING AND HEATING Inc - PA
    "f2ea1cab-c7c0-496a-8f97-062e5284e346",  # Plumbing The Bay - CA
    "95b7c63a-fe36-442b-8b6d-15109d3279de",  # Premier Plumbing Company NYC 24/7 - NY
    "accdfdd4-4076-498b-9962-81438130fbe1",  # Puget Seattle Plumbers and Drain Cleaning Co. - WA
    "d6dfc31c-98e3-4e0c-a3cd-548b956ccbf4",  # Quality Plumbing - CO
    "2652dd7a-a3a1-4464-bec4-2d62bdeecd1e",  # R D Eikey Plumbing LLC - unknown/US
    "6f51580b-8458-44f2-a2a2-b38d50d2a9ba",  # RR Plumbing Roto-Rooter - NY
    "e0fc0a90-615c-4f7e-ac9a-84f8d1d8cee8",  # SITTIG'S PLUMBING LLC - LA
    "fa20b0c6-4268-41b1-8850-ccfa4d3b9f47",  # Sparks plumbing and drain cleaning - OH
    "1dd289fa-5a32-448f-a9e4-b7bee7706a9e",  # Walker Plumbing & Heating - KS
]


def main():
    print("=" * 70)
    print("RE-DISCOVER TRIPLE_VERIFIED US BUSINESSES (OLD PIPELINE)")
    print("=" * 70)
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"Target: {len(TARGET_BUSINESS_IDS)} businesses\n")

    with get_db_session_sync() as db:
        businesses = (
            db.query(Business)
            .filter(Business.id.in_(TARGET_BUSINESS_IDS))
            .all()
        )

        print(f"Found {len(businesses)} records in DB:\n")
        for b in sorted(businesses, key=lambda x: x.name):
            sd_attempted = False
            if b.website_metadata:
                attempts = b.website_metadata.get("discovery_attempts", {})
                sd_attempted = attempts.get("scrapingdog", {}).get("attempted", False)
            print(
                f"  {'[SD-DONE]' if sd_attempted else '[PENDING ]'}"
                f"  {b.website_validation_status:<20}"
                f"  {b.name}  ({b.city}, {b.state})"
            )

        if DRY_RUN:
            print(f"\n[DRY RUN] Pass --execute to reset statuses and queue tasks.\n")
            print("What will happen:")
            print("  1. website_validation_status  → needs_discovery")
            print("  2. website_validation_result  → NULL")
            print("  3. website_validated_at       → NULL")
            print("  4. website_metadata.discovery_attempts.scrapingdog → {} (cleared)")
            print("  5. Celery task discover_missing_websites_v2 queued for each")
            return

        # ---- LIVE RUN ----
        print(f"\nResetting {len(businesses)} records...")
        reset_count = 0
        for b in businesses:
            # Clear scrapingdog attempt flag so the task won't skip this business
            meta = b.website_metadata or {}
            discovery_attempts = meta.get("discovery_attempts", {})
            discovery_attempts["scrapingdog"] = {}  # clear the attempted flag
            meta["discovery_attempts"] = discovery_attempts
            import copy
            b.website_metadata = copy.deepcopy(meta)  # force SQLAlchemy to detect the change

            b.website_validation_status = "needs_discovery"
            b.website_validation_result = None
            b.website_validated_at = None
            reset_count += 1

        db.commit()
        print(f"  ✅ Reset {reset_count} records.\n")

        # Queue discovery tasks
        print(f"Queuing {len(businesses)} discovery tasks on '{QUEUE}' queue...")
        queued = 0
        failed = 0
        for b in businesses:
            try:
                celery_app.send_task(TASK_NAME, args=[str(b.id)], queue=QUEUE)
                print(f"  ✅ Queued: {b.name}")
                queued += 1
            except Exception as exc:
                print(f"  ❌ Failed to queue {b.name}: {exc}")
                failed += 1

        print()
        print("=" * 70)
        print("DONE")
        print(f"  Records reset:  {reset_count}")
        print(f"  Tasks queued:   {queued}")
        print(f"  Queue failures: {failed}")
        print("=" * 70)
        print()
        print("Monitor progress:")
        print("  python scripts/monitor_discovery_progress.py")
        print()
        print("After all tasks complete, run this SQL to mark any discovered sites as superseded:")
        print("""
  UPDATE generated_sites gs
  SET status = 'superseded'
  FROM businesses b
  WHERE gs.business_id = b.id
    AND gs.status = 'completed'
    AND b.website_validation_status IN ('valid_scrapingdog', 'valid_outscraper', 'valid_manual')
    AND b.id IN (
      'c3d4e024-4430-4a5b-ab20-39daec56ff41',
      'd0530b7d-c4b9-462a-96a4-c911859f914f',
      '991456a3-37b1-4e3a-81be-87e89e69a9b6',
      '2d98d1a8-4c7f-4015-99be-c57c938a88e1',
      '362efff0-5952-4f34-8ae5-79a3487321b5',
      '018366de-5ff1-4ae1-95cb-4f5295a38359',
      '7c88c2c6-2572-4288-a39f-7ce66cb79959',
      'fc96e5c6-37a2-4304-8b32-0c6b6f41ac03',
      'd89f3734-b970-47cf-8799-f91829d03c70',
      '1e306b58-abe5-4fd0-b52d-93343ec6b02b',
      'dcfac76d-68af-4312-9b41-dd35db3690c7',
      '76902318-5475-423f-aaa8-3ed4b4fcdc52',
      '4e00a261-d142-4099-b6e8-cf0edea18f61',
      'fa35cfad-07fe-4762-bab4-94ee448e0af6',
      'fe955ad3-9e62-4e1c-9670-509423a0cf9f',
      '2b73d830-b68a-4e6d-badc-cdea7f89dec7',
      'f2ea1cab-c7c0-496a-8f97-062e5284e346',
      '95b7c63a-fe36-442b-8b6d-15109d3279de',
      'accdfdd4-4076-498b-9962-81438130fbe1',
      'd6dfc31c-98e3-4e0c-a3cd-548b956ccbf4',
      '2652dd7a-a3a1-4464-bec4-2d62bdeecd1e',
      '6f51580b-8458-44f2-a2a2-b38d50d2a9ba',
      'e0fc0a90-615c-4f7e-ac9a-84f8d1d8cee8',
      'fa20b0c6-4268-41b1-8850-ccfa4d3b9f47',
      '1dd289fa-5a32-448f-a9e4-b7bee7706a9e'
    );
""")


if __name__ == "__main__":
    main()
