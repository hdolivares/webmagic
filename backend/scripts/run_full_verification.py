"""
Run Full Verification Pipeline (No Prompts)

Runs all three verification stages for businesses.
Use for automated/CI or when you want to skip confirmations.

Usage:
    python -m scripts.run_full_verification --stage 2 --limit 150   # Playwright only
    python -m scripts.run_full_verification --stage 3 --limit 100    # ScrapingDog only
    python -m scripts.run_full_verification --all --limit 100        # Stages 2+3
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, or_
from core.database import AsyncSessionLocal
from models.business import Business
from services.hunter.google_search_service import GoogleSearchService
from datetime import datetime


async def run_playwright_validation(limit: int = 150, batch_size: int = 10):
    """Stage 2: Queue Playwright validation for businesses with website_url (requires Celery broker)."""
    from tasks.validation_tasks import batch_validate_websites

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Business)
            .where(Business.website_url.isnot(None), Business.website_url != "")
            .order_by(Business.website_validated_at.asc().nullsfirst())
            .limit(limit)
        )
        businesses = result.scalars().all()

    if not businesses:
        print("No businesses with website_url to validate")
        return 0

    ids = [str(b.id) for b in businesses]
    tasks_queued = 0
    for i in range(0, len(ids), batch_size):
        batch = ids[i : i + batch_size]
        batch_validate_websites.delay(batch)
        tasks_queued += 1

    print(f"Queued {tasks_queued} Playwright validation batches ({len(ids)} businesses)")
    return len(ids)


async def run_scrapingdog_verification(limit: int = 100, country: str = "US", dry_run: bool = False):
    """Stage 3: ScrapingDog/Google search for businesses without website_url."""
    service = GoogleSearchService()
    if not service.api_key:
        print("SCRAPINGDOG_API_KEY not configured - skipping Stage 3")
        return {"found": 0, "confirmed_missing": 0}

    from sqlalchemy import and_
    conditions = [
        or_(Business.website_url.is_(None), Business.website_url == ""),
    ]
    if country:
        conditions.append(Business.country == country)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Business)
            .where(and_(*conditions))
            .order_by(Business.qualification_score.desc().nullslast())
            .limit(limit)
        )
        businesses = result.scalars().all()

    if not businesses:
        print("No businesses without website_url to verify")
        return {"found": 0, "confirmed_missing": 0}

    found = 0
    confirmed = 0
    for i, biz in enumerate(businesses, 1):
        try:
            url = await service.search_business_website(
                business_name=biz.name,
                city=biz.city,
                state=biz.state,
                country=biz.country or "US",
            )
            if url:
                found += 1
                if not dry_run:
                    async with AsyncSessionLocal() as db2:
                        b = await db2.get(Business, biz.id)
                        if b:
                            b.website_url = url
                            b.website_validation_status = "pending"
                            b.website_validated_at = None
                            await db2.commit()
            else:
                confirmed += 1
                if not dry_run:
                    async with AsyncSessionLocal() as db2:
                        b = await db2.get(Business, biz.id)
                        if b:
                            b.website_validation_status = "missing"
                            b.website_validated_at = datetime.utcnow()
                            await db2.commit()
        except Exception as e:
            print(f"  Error {biz.name}: {e}")
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(businesses)}")
        await asyncio.sleep(1)

    print(f"ScrapingDog: found={found}, confirmed_no_website={confirmed}")
    return {"found": found, "confirmed_missing": confirmed}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=[2, 3])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--country", default="US")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.stage == 2:
        asyncio.run(run_playwright_validation(limit=args.limit))
    elif args.stage == 3:
        asyncio.run(run_scrapingdog_verification(limit=args.limit, country=args.country, dry_run=args.dry_run))
    elif args.all:
        print("Stage 2: Playwright...")
        asyncio.run(run_playwright_validation(limit=args.limit))
        print("\nStage 3: ScrapingDog...")
        asyncio.run(run_scrapingdog_verification(limit=args.limit, country=args.country, dry_run=args.dry_run))
    else:
        parser.error("Specify --stage 2, --stage 3, or --all")


if __name__ == "__main__":
    main()
