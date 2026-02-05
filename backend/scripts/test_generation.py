"""
Test website generation with safe businesses.

This script manually triggers generation for businesses that:
- Have NO website URL (definitely need one)
- Are marked as 'missing' or 'pending'
- Are safe to test with

Usage: python -m scripts.test_generation --business-ids <id1> <id2> ...
"""
import asyncio
import sys
from pathlib import Path
from typing import List
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from core.database import AsyncSessionLocal
from models.business import Business
from tasks.generation_sync import generate_site_for_business
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_generation(business_ids: List[str], dry_run: bool = False):
    """Test generation for specific businesses."""
    
    logger.info("="*80)
    logger.info("WEBSITE GENERATION TEST")
    logger.info("="*80)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"Testing {len(business_ids)} businesses\n")
    
    async with AsyncSessionLocal() as db:
        results = []
        
        for idx, business_id in enumerate(business_ids, 1):
            logger.info(f"[{idx}/{len(business_ids)}] Testing business: {business_id}")
            
            # Get business details
            result = await db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                logger.error(f"  ❌ Business not found: {business_id}")
                results.append({'id': business_id, 'status': 'not_found'})
                continue
            
            logger.info(f"  📋 Name: {business.name}")
            logger.info(f"  📍 Location: {business.city}, {business.state}")
            logger.info(f"  ⭐ Rating: {business.rating}/5.0 ({business.review_count} reviews)")
            logger.info(f"  🌐 Website URL: {business.website_url or 'NONE'}")
            logger.info(f"  🔍 Validation Status: {business.website_validation_status}")
            logger.info(f"  📊 Queue Status: {business.website_status}")
            
            # Safety checks
            if business.website_validation_status == 'valid':
                logger.warning(f"  ⚠️  SKIP: Business already has valid website")
                results.append({'id': business_id, 'status': 'already_valid', 'business': business})
                continue
            
            if business.website_url and business.website_validation_status != 'invalid':
                logger.warning(f"  ⚠️  CAUTION: Business has URL but not marked invalid")
            
            if dry_run:
                logger.info(f"  🔵 DRY RUN: Would trigger generation for {business.name}")
                results.append({'id': business_id, 'status': 'dry_run', 'business': business})
            else:
                logger.info(f"  🚀 Triggering generation...")
                try:
                    # Trigger the Celery task
                    task = generate_site_for_business.apply_async(
                        args=[str(business_id)],
                        priority=9  # High priority for tests
                    )
                    logger.info(f"  ✅ Task queued: {task.id}")
                    results.append({
                        'id': business_id,
                        'status': 'queued',
                        'task_id': task.id,
                        'business': business
                    })
                except Exception as e:
                    logger.error(f"  ❌ Error queuing task: {e}")
                    results.append({'id': business_id, 'status': 'error', 'error': str(e)})
            
            logger.info("")
        
        # Summary
        logger.info("="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total Businesses: {len(business_ids)}")
        
        status_counts = {}
        for r in results:
            status = r['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count}")
        
        if not dry_run:
            logger.info("\n" + "="*80)
            logger.info("MONITORING")
            logger.info("="*80)
            logger.info("To monitor task progress:")
            logger.info("  1. Check Celery logs: tail -f /tmp/celery_worker.log")
            logger.info("  2. Check active tasks: celery -A celery_app inspect active")
            logger.info("  3. Check database: SELECT * FROM businesses WHERE id IN (...);")
            logger.info("="*80)
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Test website generation')
    parser.add_argument('--business-ids', nargs='+', required=True, help='Business IDs to test')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual generation)')
    
    args = parser.parse_args()
    
    asyncio.run(test_generation(args.business_ids, args.dry_run))


if __name__ == "__main__":
    main()

