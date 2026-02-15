#!/usr/bin/env python3
"""
Re-validate businesses marked as "missing" that likely have valid websites.
This script filters out true directories/aggregators and only re-validates 
businesses with actual website domains.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from sqlalchemy import select, text
from core.database import get_db
from models.business import Business
from tasks.validation_tasks import validate_business_website

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Aggregator/directory domains to exclude (these are correctly marked as "missing")
EXCLUDE_DOMAINS = [
    'yelp.com',
    'yellowpages.com',
    'mapquest.com',
    'whitepages.com',
    'bbb.org',
    'facebook.com',
    'linkedin.com',
    'google.com',
    'foursquare.com',
    'tripadvisor.com',
    'angi.com',
    'homeadvisor.com',
    'thumbtack.com',
    'houzz.com',
    'porch.com'
]

async def get_revalidation_candidates(limit: int = None):
    """
    Get businesses marked as "missing" that have actual website domains.
    Excludes aggregators/directories.
    """
    async for db in get_db():
        # Get "missing" businesses with non-aggregator URLs
        query = """
        SELECT 
            id, name, website_url, city, state,
            website_validated_at,
            website_validation_result->'stages'->'playwright'->>'phones' as pw_phones,
            website_validation_result->'stages'->'playwright'->>'title' as pw_title
        FROM businesses
        WHERE 
            website_validation_status = 'missing'
            AND website_url IS NOT NULL
            AND website_url NOT LIKE '%yelp.com%'
            AND website_url NOT LIKE '%yellowpages.com%'
            AND website_url NOT LIKE '%mapquest.com%'
            AND website_url NOT LIKE '%whitepages.com%'
            AND website_url NOT LIKE '%bbb.org%'
            AND website_url NOT LIKE '%facebook.com%'
            AND website_url NOT LIKE '%linkedin.com%'
            AND website_url NOT LIKE '%google.com%'
            AND website_url NOT LIKE '%foursquare.com%'
            AND website_url NOT LIKE '%tripadvisor.com%'
            AND website_url NOT LIKE '%angi.com%'
            AND website_url NOT LIKE '%homeadvisor.com%'
            AND website_url NOT LIKE '%thumbtack.com%'
            AND website_url NOT LIKE '%houzz.com%'
            AND website_url NOT LIKE '%porch.com%'
        ORDER BY website_validated_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        result = await db.execute(text(query))
        businesses = result.fetchall()
        
        logger.info(f"Found {len(businesses)} businesses to re-validate")
        return businesses

async def revalidate_missing_businesses(dry_run: bool = False, batch_size: int = 10, limit: int = None):
    """
    Re-queue businesses marked as "missing" for validation with the FIXED orchestrator.
    """
    candidates = await get_revalidation_candidates(limit=limit)
    
    if not candidates:
        logger.info("No businesses need re-validation")
        return 0
    
    logger.info(f"\n{'='*80}")
    logger.info(f"RE-VALIDATION CANDIDATES")
    logger.info(f"{'='*80}\n")
    
    # Show sample
    for i, biz in enumerate(candidates[:10], 1):
        logger.info(f"{i}. {biz.name} ({biz.city}, {biz.state})")
        logger.info(f"   URL: {biz.website_url}")
        logger.info(f"   Playwright Phones: {biz.pw_phones}")
        logger.info(f"   Playwright Title: {biz.pw_title}")
        logger.info("")
    
    if len(candidates) > 10:
        logger.info(f"... and {len(candidates) - 10} more\n")
    
    if dry_run:
        logger.info("DRY RUN - No tasks queued")
        return len(candidates)
    
    # Queue for re-validation
    queued = 0
    total = len(candidates)
    
    for i in range(0, total, batch_size):
        batch = candidates[i:i+batch_size]
        business_ids = [str(biz.id) for biz in batch]
        
        try:
            # Queue each business individually to avoid batch issues
            for biz_id in business_ids:
                validate_business_website.delay(biz_id)
                queued += 1
            
            logger.info(f"✅ Queued batch {i//batch_size + 1}: {len(business_ids)} businesses (Total: {queued}/{total})")
        except Exception as e:
            logger.error(f"❌ Failed to queue batch {i//batch_size + 1}: {e}")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ Successfully queued {queued}/{total} businesses for re-validation")
    logger.info(f"{'='*80}\n")
    logger.info("These businesses will be re-validated with the FIXED orchestrator.")
    logger.info("Expected outcome: Businesses with valid websites will now be marked as 'valid'")
    logger.info("because the LLM will receive actual contact data (phones, emails, content).")
    
    return queued

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Re-validate businesses with the fixed orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Show candidates without queuing")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for queuing")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of businesses to process")
    
    args = parser.parse_args()
    
    queued = asyncio.run(revalidate_missing_businesses(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        limit=args.limit
    ))
    
    if args.dry_run:
        logger.info(f"\nTo re-validate these {queued} businesses, run without --dry-run")
