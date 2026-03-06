#!/usr/bin/env python3
"""
Regenerate specific generated sites by subdomain using the full architect pipeline.

Use when a site was truncated (e.g. 64k token limit) and is missing content like the hero.
Looks up business_id from generated_sites, then queues the same Celery task used for
initial generation: Analyst → Concept → Art Director → Architect.

The task (generate_site_for_business) will:
- Find the existing site by business_id
- If status is "completed" but HTML fails quality check (e.g. missing hero/nav), mark
  site as failed and re-run the full pipeline, reusing the same subdomain.

Usage:
  # From repo root with backend on PYTHONPATH, or from backend/ with -m
  python backend/scripts/regenerate_sites_by_subdomain.py florence-pet-clinic-1771107215496-f85c9b01 nyc-plumbing-heating-drain-cleaning-1770270516683-fe955ad3

  # Or run with default list (the two known broken sites)
  python backend/scripts/regenerate_sites_by_subdomain.py
"""
import sys
import os

# Allow running from repo root or backend/
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, text

# Default: the two sites with missing hero (likely 64k truncation)
DEFAULT_SUBDOMAINS = [
    "florence-pet-clinic-1771107215496-f85c9b01",
    "nyc-plumbing-heating-drain-cleaning-1770270516683-fe955ad3",
]


def main():
    from core.config import get_settings
    from tasks.generation_sync import generate_site_for_business

    subdomains = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_SUBDOMAINS
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))

    print("\n🔄 Regenerate sites by subdomain (full Architect pipeline)")
    print("   Subdomains:", subdomains)

    queued = []
    with engine.connect() as conn:
        for subdomain in subdomains:
            row = conn.execute(
                text(
                    "SELECT business_id, status FROM generated_sites WHERE subdomain = :sub"
                ),
                {"sub": subdomain},
            ).fetchone()

            if not row:
                print(f"❌ Site not found: {subdomain}")
                continue

            business_id = str(row[0])
            status = row[1]
            print(f"✅ {subdomain} → business_id={business_id} (status={status})")

            result = generate_site_for_business.apply_async(
                args=[business_id],
                queue="generation",
            )
            queued.append((subdomain, business_id, result.id))
            print(f"   Queued task: {result.id}")

    if not queued:
        print("\n❌ No sites queued.")
        sys.exit(1)

    print("\n📋 Queued:")
    for subdomain, bid, task_id in queued:
        print(f"   https://sites.lavish.solutions/{subdomain}  (task {task_id})")
    print("\n💡 Check progress: celery -A celery_app inspect active")
    print()


if __name__ == "__main__":
    main()
