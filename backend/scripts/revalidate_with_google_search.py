"""
Re-validate all businesses with enhanced Google Search.

This script:
1. Finds all businesses without website_url
2. Uses Google Search (Scrapingdog) to find their websites
3. Updates database with found websites
4. Generates accurate list of businesses truly needing sites

Usage:
    python -m scripts.revalidate_with_google_search --limit 50 --dry-run
    python -m scripts.revalidate_with_google_search --all --country US
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Optional
import argparse
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, or_
from core.database import AsyncSessionLocal
from models.business import Business
from services.hunter.google_search_service import GoogleSearchService
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def revalidate_businesses(
    limit: Optional[int] = None,
    country: Optional[str] = None,
    dry_run: bool = True
):
    """
    Re-validate businesses using Google Search.
    
    Args:
        limit: Maximum number of businesses to process
        country: Filter by country (e.g., "US", "GB")
        dry_run: If True, don't update database
    """
    logger.info("="*80)
    logger.info("RE-VALIDATE BUSINESSES WITH GOOGLE SEARCH")
    logger.info("="*80)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"Limit: {limit or 'ALL'}")
    logger.info(f"Country filter: {country or 'ALL'}")
    logger.info("")
    
    async with AsyncSessionLocal() as db:
        # Build query for businesses without websites
        query = select(Business).where(
            or_(
                Business.website_url.is_(None),
                Business.website_url == ""
            )
        )
        
        if country:
            query = query.where(Business.country == country)
        
        if limit:
            query = query.limit(limit)
        
        query = query.order_by(Business.created_at.desc())
        
        result = await db.execute(query)
        businesses = result.scalars().all()
        
        logger.info(f"📊 Found {len(businesses)} businesses without website_url")
        logger.info("")
        
        if not businesses:
            logger.info("✅ No businesses to process")
            return
        
        # Initialize Google Search service
        search_service = GoogleSearchService()
        
        # Statistics
        stats = {
            "total": len(businesses),
            "found": 0,
            "not_found": 0,
            "errors": 0,
            "updated": 0
        }
        
        # Process each business
        for idx, business in enumerate(businesses, 1):
            logger.info(f"[{idx}/{len(businesses)}] Processing: {business.name}")
            logger.info(f"  Location: {business.city}, {business.state}, {business.country}")
            logger.info(f"  Current website_url: {business.website_url or 'NULL'}")
            
            try:
                # Search for website
                website = await search_service.search_business_website(
                    business_name=business.name,
                    city=business.city,
                    state=business.state,
                    country=business.country or "US"
                )
                
                if website:
                    logger.info(f"  ✅ Found website: {website}")
                    stats["found"] += 1
                    
                    if not dry_run:
                        # Update business
                        business.website_url = website
                        business.website_validation_status = "pending"  # Will be validated by Playwright
                        business.website_validated_at = None
                        stats["updated"] += 1
                        logger.info(f"  💾 Updated database")
                    else:
                        logger.info(f"  🔵 DRY RUN: Would update database")
                else:
                    logger.info(f"  ❌ No website found")
                    stats["not_found"] += 1
                    
                    if not dry_run:
                        # Mark as confirmed no website
                        business.website_validation_status = "missing"
                        business.website_validated_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"  ⚠️  Error: {e}")
                stats["errors"] += 1
            
            logger.info("")
            
            # Rate limiting (1 second between requests)
            await asyncio.sleep(1)
        
        # Commit changes
        if not dry_run and stats["updated"] > 0:
            await db.commit()
            logger.info(f"✅ Committed {stats['updated']} updates to database")
        
        # Summary
        logger.info("="*80)
        logger.info("SUMMARY")
        logger.info("="*80)
        logger.info(f"Total businesses processed: {stats['total']}")
        logger.info(f"  ✅ Websites found: {stats['found']} ({stats['found']/stats['total']*100:.1f}%)")
        logger.info(f"  ❌ No website found: {stats['not_found']} ({stats['not_found']/stats['total']*100:.1f}%)")
        logger.info(f"  ⚠️  Errors: {stats['errors']}")
        if not dry_run:
            logger.info(f"  💾 Database updated: {stats['updated']} businesses")
        logger.info("")
        
        # Generate list of businesses truly needing sites
        if stats["not_found"] > 0:
            logger.info("="*80)
            logger.info("BUSINESSES TRULY NEEDING SITES")
            logger.info("="*80)
            
            # Query businesses with confirmed no website
            if not dry_run:
                no_website_query = select(Business).where(
                    Business.website_validation_status == "missing"
                )
                if country:
                    no_website_query = no_website_query.where(Business.country == country)
                
                no_website_result = await db.execute(no_website_query)
                no_website_businesses = no_website_result.scalars().all()
                
                logger.info(f"Found {len(no_website_businesses)} businesses confirmed without websites:")
                logger.info("")
                
                for biz in no_website_businesses[:20]:  # Show first 20
                    logger.info(f"  • {biz.name}")
                    logger.info(f"    Location: {biz.city}, {biz.state}, {biz.country}")
                    logger.info(f"    Rating: {biz.rating}/5.0 ({biz.review_count} reviews)")
                    logger.info(f"    ID: {biz.id}")
                    logger.info("")
                
                if len(no_website_businesses) > 20:
                    logger.info(f"  ... and {len(no_website_businesses) - 20} more")
        
        logger.info("="*80)
        logger.info("✅ Re-validation complete!")
        logger.info("="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Re-validate businesses with Google Search'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of businesses to process'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all businesses (no limit)'
    )
    parser.add_argument(
        '--country',
        type=str,
        help='Filter by country code (e.g., US, GB, CA)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no database updates)'
    )
    
    args = parser.parse_args()
    
    limit = None if args.all else (args.limit or 50)
    
    asyncio.run(revalidate_businesses(
        limit=limit,
        country=args.country,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()

