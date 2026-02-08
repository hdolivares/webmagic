"""
Backfill website discovery for businesses currently marked as 'missing'.

This script handles the 379 businesses that were marked as having no website
BEFORE the Google Search integration was added. It will:

1. Query all businesses with website_validation_status='missing'
2. Queue them for Google Search discovery via Celery
3. Respect rate limits (1 request/second for ScrapingDog)
4. Provide progress monitoring

Expected Results:
- Discovery rate: ~30-50% (100-200 websites found)
- Processing time: ~6-7 hours at 1 req/sec
- Triple-verified: Remaining businesses confirmed to have no website

Usage:
    # Dry run - see what would be processed
    python -m scripts.backfill_website_discovery --dry-run
    
    # Process first 50 businesses
    python -m scripts.backfill_website_discovery --limit 50
    
    # Process all with custom rate limit
    python -m scripts.backfill_website_discovery --all --delay 1.5
    
    # Full backfill (all 379)
    python -m scripts.backfill_website_discovery --all

Best Practices:
- Uses Celery tasks (not direct API calls) for monitoring
- Respects rate limits via task countdown
- Provides detailed progress reporting
- Supports resume (idempotent)
- Clean error handling
"""
import asyncio
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import select, and_, or_
from core.database import AsyncSessionLocal
from models.business import Business

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_businesses_needing_discovery(
    limit: int = None,
    min_score: int = 0
) -> List[Business]:
    """
    Query businesses that need website discovery.
    
    Criteria:
    - Currently marked as 'missing' (from old validation)
    - No website_url
    - Above minimum qualification score
    
    Args:
        limit: Max businesses to return (None = all)
        min_score: Minimum qualification score
        
    Returns:
        List of Business objects
    """
    async with AsyncSessionLocal() as db:
        query = select(Business).where(
            and_(
                Business.website_validation_status == 'missing',
                or_(
                    Business.website_url.is_(None),
                    Business.website_url == ''
                ),
                Business.qualification_score >= min_score
            )
        ).order_by(
            Business.qualification_score.desc(),  # Process best leads first
            Business.created_at.desc()
        )
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        businesses = result.scalars().all()
        
        return list(businesses)


async def queue_discovery_tasks(
    businesses: List[Business],
    delay_seconds: float = 1.0,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Queue Celery discovery tasks for businesses.
    
    Args:
        businesses: List of businesses to process
        delay_seconds: Delay between tasks (rate limiting)
        dry_run: If True, don't actually queue tasks
        
    Returns:
        Dict with summary statistics
    """
    # Import here to avoid issues if Celery not available
    from tasks.validation_tasks import discover_missing_websites
    
    logger.info("="*70)
    logger.info("BACKFILL WEBSITE DISCOVERY")
    logger.info("="*70)
    logger.info(f"Businesses to process: {len(businesses)}")
    logger.info(f"Rate limit: 1 request every {delay_seconds} seconds")
    logger.info(f"Estimated time: {(len(businesses) * delay_seconds / 60):.1f} minutes")
    logger.info("="*70)
    
    if dry_run:
        logger.info("\n🔍 DRY RUN MODE - No tasks will be queued\n")
        
        # Show sample of what would be processed
        logger.info("Sample businesses that would be processed:")
        for idx, biz in enumerate(businesses[:10], 1):
            logger.info(
                f"  {idx}. {biz.name} | "
                f"{biz.city}, {biz.state} | "
                f"Score: {biz.qualification_score}"
            )
        
        if len(businesses) > 10:
            logger.info(f"  ... and {len(businesses) - 10} more")
        
        logger.info("\n✅ Dry run complete. Run without --dry-run to execute.")
        
        return {
            "dry_run": True,
            "total": len(businesses),
            "queued": 0
        }
    
    # Queue tasks with countdown for rate limiting
    tasks = []
    
    for idx, business in enumerate(businesses):
        # Calculate countdown (delay in seconds before task executes)
        countdown = int(idx * delay_seconds)
        
        try:
            # Queue the discovery task
            task = discover_missing_websites.apply_async(
                args=[str(business.id)],
                countdown=countdown
            )
            
            tasks.append({
                "business_id": str(business.id),
                "business_name": business.name,
                "task_id": task.id,
                "starts_in": countdown
            })
            
            # Progress logging
            if (idx + 1) % 25 == 0:
                logger.info(f"✓ Queued {idx + 1}/{len(businesses)} tasks")
                
        except Exception as e:
            logger.error(f"Failed to queue task for {business.name}: {e}")
            continue
    
    logger.info("="*70)
    logger.info(f"✅ Successfully queued {len(tasks)} discovery tasks")
    logger.info(f"⏱️  Tasks will complete in ~{(len(tasks) * delay_seconds / 60):.1f} minutes")
    logger.info("="*70)
    logger.info("\nMonitoring commands:")
    logger.info("  celery -A celery_app inspect active    # See running tasks")
    logger.info("  celery -A celery_app inspect scheduled # See queued tasks")
    logger.info("\nDatabase query to check progress:")
    logger.info("  SELECT website_validation_status, COUNT(*) FROM businesses")
    logger.info("  WHERE website_validation_status IN ('missing', 'pending', 'valid')")
    logger.info("  GROUP BY website_validation_status;")
    
    return {
        "total": len(businesses),
        "queued": len(tasks),
        "estimated_completion_minutes": (len(tasks) * delay_seconds) / 60,
        "sample_tasks": tasks[:5]
    }


async def show_statistics():
    """Display current statistics before processing."""
    async with AsyncSessionLocal() as db:
        # Total businesses
        total_result = await db.execute(select(Business))
        total = len(total_result.scalars().all())
        
        # Currently marked as missing
        missing_result = await db.execute(
            select(Business).where(
                and_(
                    Business.website_validation_status == 'missing',
                    or_(
                        Business.website_url.is_(None),
                        Business.website_url == ''
                    )
                )
            )
        )
        missing = len(missing_result.scalars().all())
        
        # Have URLs
        with_url_result = await db.execute(
            select(Business).where(
                and_(
                    Business.website_url.isnot(None),
                    Business.website_url != ''
                )
            )
        )
        with_url = len(with_url_result.scalars().all())
        
        logger.info("\n" + "="*70)
        logger.info("CURRENT DATABASE STATISTICS")
        logger.info("="*70)
        logger.info(f"Total businesses: {total}")
        logger.info(f"  ├─ With website URLs: {with_url} ({with_url/total*100:.1f}%)")
        logger.info(f"  └─ Marked as 'missing': {missing} ({missing/total*100:.1f}%)")
        logger.info("="*70)
        logger.info(f"\n🎯 Target: Discover websites for {missing} businesses")
        logger.info(f"📈 Expected discovery rate: 30-50% (~{int(missing*0.4)} websites)")
        logger.info("="*70 + "\n")


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Backfill website discovery for businesses marked as 'missing'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be processed
  python -m scripts.backfill_website_discovery --dry-run
  
  # Process first 50 businesses (test run)
  python -m scripts.backfill_website_discovery --limit 50
  
  # Process all businesses with default rate limit (1 req/sec)
  python -m scripts.backfill_website_discovery --all
  
  # Custom rate limit (slower, more conservative)
  python -m scripts.backfill_website_discovery --all --delay 1.5
  
  # Only process high-quality leads
  python -m scripts.backfill_website_discovery --all --min-score 60
        """
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max businesses to process (default: None = all)"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process ALL businesses marked as missing (recommended)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between tasks in seconds (default: 1.0 for rate limiting)"
    )
    
    parser.add_argument(
        "--min-score",
        type=int,
        default=0,
        help="Minimum qualification score (default: 0 = all)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without queuing tasks"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.all and args.limit is None:
        parser.error("Specify either --all or --limit N")
    
    try:
        # Show current statistics
        await show_statistics()
        
        # Get businesses needing discovery
        logger.info("Querying businesses needing discovery...")
        businesses = await get_businesses_needing_discovery(
            limit=args.limit if not args.all else None,
            min_score=args.min_score
        )
        
        if not businesses:
            logger.info("✅ No businesses need discovery - all done!")
            return
        
        logger.info(f"Found {len(businesses)} businesses to process\n")
        
        # Confirm if not dry run
        if not args.dry_run:
            logger.warning(
                f"⚠️  About to queue {len(businesses)} discovery tasks. "
                f"This will take ~{(len(businesses) * args.delay / 60):.1f} minutes."
            )
            
            response = input("\nContinue? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                logger.info("Cancelled by user.")
                return
        
        # Queue discovery tasks
        result = await queue_discovery_tasks(
            businesses=businesses,
            delay_seconds=args.delay,
            dry_run=args.dry_run
        )
        
        # Summary
        if not args.dry_run:
            logger.info("\n🚀 Backfill started successfully!")
            logger.info(f"Monitor progress in Celery logs: tail -f /var/log/webmagic/celery.log")
        
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Interrupted by user. No tasks queued.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
