"""
Standalone revalidation script - NO Celery/RabbitMQ/Redis required.

Runs ScrapingDog and Playwright validation inline. Use when the broker
is unreachable or for one-off batch runs.

Usage:
    # ScrapingDog only (find websites for businesses without them)
    python -m scripts.revalidate_standalone --scrapingdog --limit 50 --country US

    # Playwright only (validate businesses that have website_url)
    python -m scripts.revalidate_standalone --playwright --limit 50

    # Both stages
    python -m scripts.revalidate_standalone --all --limit 100

    # Dry run (no DB updates)
    python -m scripts.revalidate_standalone --scrapingdog --limit 10 --dry-run
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Optional
import argparse
import logging
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, or_
from core.database import AsyncSessionLocal
from core.config import get_settings
from models.business import Business
from services.hunter.google_search_service import GoogleSearchService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# --- ScrapingDog (Stage 3) - Find websites for businesses without them ---

async def run_scrapingdog(
    limit: Optional[int] = None,
    country: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """
    Use Google Search (ScrapingDog) to find websites for businesses without them.
    """
    service = GoogleSearchService()
    if not service.api_key:
        logger.error("SCRAPINGDOG_API_KEY not configured - cannot run ScrapingDog")
        return {"found": 0, "confirmed_missing": 0, "errors": 0}

    async with AsyncSessionLocal() as db:
        query = select(Business).where(
            or_(
                Business.website_url.is_(None),
                Business.website_url == "",
            )
        )
        if country:
            query = query.where(Business.country == country)
        if limit:
            query = query.limit(limit)
        query = query.order_by(Business.created_at.desc())

        result = await db.execute(query)
        businesses = result.scalars().all()

    if not businesses:
        logger.info("No businesses without website_url to verify")
        return {"found": 0, "confirmed_missing": 0, "errors": 0}

    logger.info(f"ScrapingDog: processing {len(businesses)} businesses without websites")
    found = 0
    confirmed = 0
    errors = 0

    for idx, biz in enumerate(businesses, 1):
        try:
            url = await service.search_business_website(
                business_name=biz.name,
                city=biz.city,
                state=biz.state,
                country=biz.country or "US",
            )
            if url:
                found += 1
                logger.info(f"  [{idx}/{len(businesses)}] {biz.name}: found {url}")
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
                logger.info(f"  [{idx}/{len(businesses)}] {biz.name}: no website found")
                if not dry_run:
                    async with AsyncSessionLocal() as db2:
                        b = await db2.get(Business, biz.id)
                        if b:
                            b.website_validation_status = "missing"
                            b.website_validated_at = datetime.utcnow()
                            await db2.commit()
        except Exception as e:
            errors += 1
            logger.error(f"  [{idx}/{len(businesses)}] {biz.name}: {e}")

        await asyncio.sleep(1)  # Rate limit

    logger.info(f"ScrapingDog complete: found={found}, confirmed_missing={confirmed}, errors={errors}")
    return {"found": found, "confirmed_missing": confirmed, "errors": errors}


# --- Playwright (Stage 2) - Validate businesses with website_url ---

async def run_playwright(limit: Optional[int] = None, dry_run: bool = False) -> dict:
    """
    Run Playwright validation inline (no Celery). Validates businesses that have website_url.
    """
    from services.validation.playwright_service import PlaywrightValidationService

    settings = get_settings()
    async with AsyncSessionLocal() as db:
        query = (
            select(Business)
            .where(Business.website_url.isnot(None), Business.website_url != "")
            .order_by(Business.website_validated_at.asc().nullsfirst())
        )
        if limit:
            query = query.limit(limit)
        result = await db.execute(query)
        businesses = result.scalars().all()

    if not businesses:
        logger.info("No businesses with website_url to validate")
        return {"valid": 0, "invalid": 0, "errors": 0}

    logger.info(f"Playwright: validating {len(businesses)} businesses")
    valid_count = 0
    invalid_count = 0
    error_count = 0

    async with PlaywrightValidationService() as validator:
        for idx, biz in enumerate(businesses, 1):
            try:
                result = await validator.validate_website(
                    biz.website_url,
                    timeout=settings.VALIDATION_TIMEOUT_MS,
                    capture_screenshot=settings.VALIDATION_CAPTURE_SCREENSHOTS,
                )
                is_valid = result.get("is_valid", False)
                quality = result.get("quality_score", 0)

                if is_valid:
                    valid_count += 1
                    logger.info(f"  [{idx}/{len(businesses)}] {biz.name}: valid (score={quality})")
                else:
                    invalid_count += 1
                    logger.info(f"  [{idx}/{len(businesses)}] {biz.name}: invalid")

                if not dry_run:
                    async with AsyncSessionLocal() as db2:
                        b = await db2.get(Business, biz.id)
                        if b:
                            b.website_validation_status = "valid" if is_valid else "invalid"
                            b.website_validation_result = result
                            b.website_validated_at = datetime.utcnow()
                            await db2.commit()
            except Exception as e:
                error_count += 1
                logger.error(f"  [{idx}/{len(businesses)}] {biz.name}: {e}")
                if not dry_run:
                    async with AsyncSessionLocal() as db2:
                        b = await db2.get(Business, biz.id)
                        if b:
                            b.website_validation_status = "error"
                            b.website_validation_result = {"error": str(e), "is_valid": False}
                            b.website_validated_at = datetime.utcnow()
                            await db2.commit()

    logger.info(f"Playwright complete: valid={valid_count}, invalid={invalid_count}, errors={error_count}")
    return {"valid": valid_count, "invalid": invalid_count, "errors": error_count}


def main():
    parser = argparse.ArgumentParser(
        description="Standalone revalidation (no Celery) - run ScrapingDog and/or Playwright inline"
    )
    parser.add_argument(
        "--scrapingdog",
        action="store_true",
        help="Run ScrapingDog to find websites for businesses without them",
    )
    parser.add_argument(
        "--playwright",
        action="store_true",
        help="Run Playwright to validate businesses that have website_url",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run both ScrapingDog and Playwright",
    )
    parser.add_argument("--limit", type=int, default=50, help="Max businesses per stage (default: 50)")
    parser.add_argument(
        "--country",
        type=str,
        default="US",
        help="Country filter for ScrapingDog (default: US)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No database updates",
    )

    args = parser.parse_args()

    if not args.scrapingdog and not args.playwright and not args.all:
        parser.error("Specify --scrapingdog, --playwright, or --all")

    logger.info("=" * 70)
    logger.info("STANDALONE REVALIDATION (no Celery/broker required)")
    logger.info("=" * 70)

    if args.all or args.scrapingdog:
        logger.info("\n--- Stage: ScrapingDog ---")
        asyncio.run(
            run_scrapingdog(limit=args.limit, country=args.country, dry_run=args.dry_run)
        )

    if args.all or args.playwright:
        logger.info("\n--- Stage: Playwright ---")
        asyncio.run(run_playwright(limit=args.limit, dry_run=args.dry_run))

    logger.info("\n" + "=" * 70)
    logger.info("Complete")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
