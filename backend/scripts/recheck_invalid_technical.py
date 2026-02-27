#!/usr/bin/env python3
"""
Re-check businesses stuck in invalid_technical status.

For each invalid_technical business:
  - If domain does NOT resolve (NXDOMAIN): clear URL, reset to needs_discovery,
    re-queue ScrapingDog (the URL was wrong/fake).
  - If domain DOES resolve: domain exists but Playwright failed — likely
    bot-detection or a temporary outage. Keep as invalid_technical.

Usage:
  python recheck_invalid_technical.py           # dry run
  python recheck_invalid_technical.py --execute # live run
"""
import sys
import os
import socket
import copy
from datetime import datetime
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import get_db_session_sync
from models.business import Business
from models.site import GeneratedSite
from celery_app import celery_app

DRY_RUN = "--execute" not in sys.argv
DISCOVERY_TASK = "tasks.discovery.discover_missing_websites_v2"
QUEUE = "discovery"


def domain_resolves(url: str) -> bool:
    """Returns True if the domain has a DNS record."""
    try:
        host = urlparse(url).netloc.split(":")[0].strip()
        if not host:
            return False
        socket.getaddrinfo(host, 80, proto=socket.IPPROTO_TCP)
        return True
    except (socket.gaierror, OSError):
        return False


def main():
    print("=" * 70)
    print("RE-CHECK invalid_technical BUSINESSES (DNS VERIFICATION)")
    print("=" * 70)
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}\n")

    with get_db_session_sync() as db:
        # Get all invalid_technical businesses that have a URL (generated site or not)
        businesses = (
            db.query(Business)
            .filter(
                Business.website_validation_status == "invalid_technical",
                Business.website_url.isnot(None),
            )
            .all()
        )

        print(f"Found {len(businesses)} invalid_technical businesses with a URL:\n")

        dead = []
        alive = []

        for b in businesses:
            resolves = domain_resolves(b.website_url)
            status = "DNS OK  " if resolves else "DEAD DNS"
            print(f"  [{status}]  {b.name}")
            print(f"            URL: {b.website_url}")
            if resolves:
                alive.append(b)
            else:
                dead.append(b)

        print(f"\nSummary:")
        print(f"  Dead domain (will re-queue ScrapingDog): {len(dead)}")
        print(f"  Domain resolves (needs human review):    {len(alive)}")

        if alive:
            print(f"\nBusinesses with live domains (Playwright may have been blocked):")
            for b in alive:
                print(f"  - {b.name}: {b.website_url}")

        if DRY_RUN:
            print(f"\n[DRY RUN] Pass --execute to re-queue dead-domain businesses.\n")
            return

        # ---- LIVE RUN ----
        if not dead:
            print("\nNo dead-domain businesses to re-queue.")
            return

        print(f"\nClearing {len(dead)} dead-domain businesses and re-queuing ScrapingDog...")
        requeued = 0
        for b in dead:
            cleared_url = b.website_url

            # Reset scrapingdog attempt flag
            meta = copy.deepcopy(b.website_metadata or {})
            history = meta.get("validation_history", [])
            history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "dead_domain_cleared",
                "url": cleared_url,
                "invalid_reason": "domain_not_found",
                "notes": "DNS NXDOMAIN — domain unregistered. Re-queuing ScrapingDog.",
            })
            meta["validation_history"] = history
            attempts = meta.get("discovery_attempts", {})
            attempts["scrapingdog"] = {}  # clear so task won't skip
            meta["discovery_attempts"] = attempts
            b.website_metadata = meta

            b.website_url = None
            b.website_validation_status = "needs_discovery"
            b.website_validation_result = None
            b.website_validated_at = None

        db.commit()
        print(f"  ✅ Cleared {len(dead)} records.\n")

        print(f"Queuing {len(dead)} ScrapingDog discovery tasks...")
        failed = 0
        for b in dead:
            try:
                celery_app.send_task(DISCOVERY_TASK, args=[str(b.id)], queue=QUEUE)
                print(f"  ✅ Queued: {b.name}")
                requeued += 1
            except Exception as exc:
                print(f"  ❌ Failed to queue {b.name}: {exc}")
                failed += 1

        print()
        print("=" * 70)
        print("DONE")
        print(f"  Re-queued for ScrapingDog: {requeued}")
        print(f"  Queue failures:            {failed}")
        print(f"  Kept as invalid_technical: {len(alive)}")
        print("=" * 70)

        if alive:
            print("\nBusinesses kept as invalid_technical (domain resolves — may need human review):")
            for b in alive:
                print(f"  - {b.name}: {b.website_url}")


if __name__ == "__main__":
    main()
