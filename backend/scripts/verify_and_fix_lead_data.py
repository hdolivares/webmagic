"""
Lead Data Verification & Fix Script

Ensures all scraped business data is accurate before website generation.
Implements triple-verification:
  1. Raw Data Check: Fix website_url from raw_data if Outscraper had it but we didn't parse it
  2. Playwright Validation: Verify websites load and work (existing validation_tasks)
  3. ScrapingDog/Google Search: Cross-reference - confirm no website exists for "no website" leads

Also audits:
  - raw_data presence (avoid re-scraping with Outscraper credits)
  - Data consistency (website_status vs website_validation_status)

Usage:
    python -m scripts.verify_and_fix_lead_data --stage 1 --dry-run   # Fix raw_data parsing
    python -m scripts.verify_and_fix_lead_data --stage 2 --dry-run   # Playwright validation
    python -m scripts.verify_and_fix_lead_data --stage 3 --limit 10   # ScrapingDog search
    python -m scripts.verify_and_fix_lead_data --audit               # Data audit only
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional
import argparse
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update, or_
from core.database import AsyncSessionLocal
from models.business import Business
from services.hunter.google_search_service import GoogleSearchService
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

WEBSITE_FIELDS = ["website", "site", "url", "domain", "website_url", "business_url", "web", "homepage"]


def extract_website_from_raw_data(raw_data: dict) -> Optional[str]:
    """Extract website URL from raw Outscraper data."""
    if not raw_data or not isinstance(raw_data, dict):
        return None
    for field in WEBSITE_FIELDS:
        val = raw_data.get(field)
        if val and isinstance(val, str) and len(val.strip()) > 5:
            url = val.strip()
            if url.lower() not in ("", "null", "none", "n/a"):
                return url
    return None


async def stage1_fix_raw_data_parsing(dry_run: bool = True) -> dict:
    """
    Stage 1: Fix businesses where raw_data has website but website_url is null.
    These were parsed incorrectly - no Outscraper credits needed.
    """
    logger.info("=" * 70)
    logger.info("STAGE 1: Fix raw_data → website_url parsing")
    logger.info("=" * 70)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Business).where(
                Business.raw_data.isnot(None),
                or_(Business.website_url.is_(None), Business.website_url == ""),
            )
        )
        businesses = result.scalars().all()

        fixed = 0
        for biz in businesses:
            url = extract_website_from_raw_data(biz.raw_data)
            if url:
                logger.info(f"  Fix: {biz.name} - found in raw_data: {url[:50]}...")
                if not dry_run:
                    biz.website_url = url
                    biz.website_validation_status = "pending"  # Re-validate with Playwright
                    biz.website_validated_at = None
                    fixed += 1

        if not dry_run and fixed > 0:
            await db.commit()
            logger.info(f"Fixed {fixed} businesses")
        elif dry_run:
            logger.info(f"Would fix {sum(1 for b in businesses if extract_website_from_raw_data(b.raw_data))} businesses")

        return {"checked": len(businesses), "fixed": fixed}


async def stage3_scrapingdog_verification(limit: int = 50, dry_run: bool = True) -> dict:
    """
    Stage 3: Use ScrapingDog/Google Search to verify businesses truly have no website.
    Only runs on businesses that passed stages 1 & 2 (no website in raw_data, not validated as having one).
    """
    logger.info("=" * 70)
    logger.info("STAGE 3: ScrapingDog cross-reference - confirm no website")
    logger.info("=" * 70)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Business)
            .where(
                or_(Business.website_url.is_(None), Business.website_url == ""),
                Business.website_validation_status == "missing",
                Business.website_status.in_(["none", "queued", "generating"]),
            )
            .order_by(Business.qualification_score.desc())
            .limit(limit)
        )
        businesses = result.scalars().all()

        if not businesses:
            logger.info("No businesses in 'missing' status to verify")
            return {"total": 0}

        service = GoogleSearchService()
        if not service.api_key:
            logger.warning("SCRAPINGDOG_API_KEY not configured - skipping")
            return {"total": len(businesses), "skipped": True}

        found = 0
        confirmed_missing = 0
        errors = 0

        for idx, biz in enumerate(businesses, 1):
            logger.info(f"[{idx}/{len(businesses)}] {biz.name}")
            try:
                website = await service.search_business_website(
                    business_name=biz.name,
                    city=biz.city,
                    state=biz.state,
                    country=biz.country or "US",
                )
                if website:
                    logger.info(f"  Found website: {website}")
                    found += 1
                    if not dry_run:
                        biz.website_url = website
                        biz.website_validation_status = "pending"
                        biz.website_validated_at = None
                else:
                    logger.info(f"  Confirmed: no website")
                    confirmed_missing += 1
                    if not dry_run:
                        biz.website_validation_status = "missing"
                        biz.website_validated_at = datetime.utcnow()
            except Exception as e:
                logger.error(f"  Error: {e}")
                errors += 1

            await asyncio.sleep(1)

        if not dry_run and (found > 0 or confirmed_missing > 0):
            await db.commit()

        return {
            "total": len(businesses),
            "found_website": found,
            "confirmed_no_website": confirmed_missing,
            "errors": errors,
        }


async def run_audit() -> dict:
    """Audit data quality - raw_data presence, validation status, inconsistencies."""
    logger.info("=" * 70)
    logger.info("LEAD DATA AUDIT")
    logger.info("=" * 70)

    async with AsyncSessionLocal() as db:
        # Raw data presence
        r1 = await db.execute(
            select(Business).where(Business.raw_data.isnot(None))
        )
        all_with_raw = r1.scalars().all()
        has_raw = sum(1 for b in all_with_raw if b.raw_data and (not isinstance(b.raw_data, dict) or len(b.raw_data) > 0))

        r2 = await db.execute(select(Business))
        total = len(r2.scalars().all())

        # Raw data has website but website_url null
        r3 = await db.execute(
            select(Business).where(
                Business.raw_data.isnot(None),
                or_(Business.website_url.is_(None), Business.website_url == ""),
            )
        )
        missing_parse = [
            b for b in r3.scalars().all()
            if extract_website_from_raw_data(b.raw_data)
        ]

        # Inconsistency: have website_url but website_status=none
        r4 = await db.execute(
            select(Business).where(
                Business.website_url.isnot(None),
                Business.website_url != "",
                Business.website_status == "none",
            )
        )
        inconsistent = r4.scalars().all()

        # Triple-verified (missing + validated)
        r5 = await db.execute(
            select(Business).where(
                Business.website_validation_status == "missing",
                Business.website_validated_at.isnot(None),
                or_(Business.website_url.is_(None), Business.website_url == ""),
            )
        )
        triple_verified = r5.scalars().all()

    logger.info(f"Total businesses: {total}")
    logger.info(f"With raw_data: {has_raw} ({100*has_raw/max(1,total):.1f}%)")
    logger.info(f"Without raw_data: {total - has_raw} (would need re-scrape for credits)")
    logger.info(f"")
    logger.info(f"Parsing bugs (website in raw_data, website_url null): {len(missing_parse)}")
    for b in missing_parse[:5]:
        logger.info(f"  - {b.name}: {extract_website_from_raw_data(b.raw_data)[:50]}...")
    logger.info(f"")
    logger.info(f"Triple-verified no website: {len(triple_verified)}")
    logger.info(f"Inconsistent (have URL, status=none): {len(inconsistent)}")

    return {
        "total": total,
        "has_raw_data": has_raw,
        "parsing_bugs": len(missing_parse),
        "triple_verified": len(triple_verified),
        "inconsistent": len(inconsistent),
    }


async def main():
    parser = argparse.ArgumentParser(description="Verify and fix lead data")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3], help="Run specific stage")
    parser.add_argument("--audit", action="store_true", help="Audit only, no fixes")
    parser.add_argument("--limit", type=int, default=50, help="Limit for stage 3")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no DB changes)")
    parser.add_argument("--execute", action="store_true", help="Actually apply changes")
    args = parser.parse_args()

    dry_run = args.dry_run or not args.execute

    if args.audit:
        await run_audit()
        return

    if args.stage == 1:
        await stage1_fix_raw_data_parsing(dry_run=dry_run)
    elif args.stage == 2:
        logger.info("Stage 2: Use validation_tasks / revalidate_all_websites.py for Playwright")
        logger.info("  python -m scripts.revalidate_all_websites --limit 50")
        return
    elif args.stage == 3:
        await stage3_scrapingdog_verification(limit=args.limit, dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
