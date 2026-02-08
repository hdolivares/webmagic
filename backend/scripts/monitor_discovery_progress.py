"""
Monitor website discovery progress in real-time.

Provides live statistics and insights during the backfill process.

Usage:
    # Basic monitoring
    python -m scripts.monitor_discovery_progress
    
    # Continuous monitoring (refresh every 30 seconds)
    python -m scripts.monitor_discovery_progress --watch 30
    
    # Show detailed breakdown
    python -m scripts.monitor_discovery_progress --detailed

Best Practices:
- Non-invasive read-only queries
- Clear, actionable metrics
- Easy to understand progress indicators
"""
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy import select, func, and_, or_
from core.database import AsyncSessionLocal
from models.business import Business

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def get_discovery_statistics() -> Dict[str, Any]:
    """
    Get comprehensive discovery statistics.
    
    Returns:
        Dict with various metrics and breakdowns
    """
    async with AsyncSessionLocal() as db:
        # Total businesses
        total_result = await db.execute(select(func.count(Business.id)))
        total = total_result.scalar()
        
        # By validation status
        status_result = await db.execute(
            select(
                Business.website_validation_status,
                func.count(Business.id)
            ).group_by(Business.website_validation_status)
        )
        status_counts = {row[0] or 'null': row[1] for row in status_result.all()}
        
        # Businesses with URLs
        with_url_result = await db.execute(
            select(func.count(Business.id)).where(
                and_(
                    Business.website_url.isnot(None),
                    Business.website_url != ''
                )
            )
        )
        with_url = with_url_result.scalar()
        
        # Recently validated (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_result = await db.execute(
            select(func.count(Business.id)).where(
                Business.website_validated_at > one_hour_ago
            )
        )
        recently_validated = recent_result.scalar()
        
        # Google Search results (check validation_result JSON)
        google_found_result = await db.execute(
            select(func.count(Business.id)).where(
                and_(
                    Business.website_validation_result.isnot(None),
                    Business.website_validation_result['stages'].has_key('google_search')
                )
            )
        )
        google_searched = google_found_result.scalar()
        
        return {
            'total': total,
            'with_url': with_url,
            'without_url': total - with_url,
            'status_counts': status_counts,
            'recently_validated': recently_validated,
            'google_searched': google_searched,
            'timestamp': datetime.utcnow()
        }


def format_statistics(stats: Dict[str, Any], detailed: bool = False):
    """
    Format statistics for display.
    
    Args:
        stats: Statistics dictionary
        detailed: Show detailed breakdown
    """
    total = stats['total']
    with_url = stats['with_url']
    without_url = stats['without_url']
    status_counts = stats['status_counts']
    
    # Calculate percentages
    url_pct = (with_url / total * 100) if total > 0 else 0
    
    # Header
    logger.info("\n" + "="*80)
    logger.info(f"WEBSITE DISCOVERY PROGRESS - {stats['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    # Overall metrics
    logger.info(f"\n📊 OVERALL METRICS")
    logger.info(f"  Total Businesses: {total}")
    logger.info(f"  ├─ With Website URLs: {with_url} ({url_pct:.1f}%)")
    logger.info(f"  └─ Without URLs: {without_url} ({100-url_pct:.1f}%)")
    
    # Validation status breakdown
    logger.info(f"\n🔍 VALIDATION STATUS")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total * 100) if total > 0 else 0
        
        # Add emoji indicators
        emoji = {
            'valid': '✅',
            'invalid': '❌',
            'missing': '🚫',
            'pending': '⏳',
            'error': '⚠️',
            'null': '❓'
        }.get(status, '•')
        
        logger.info(f"  {emoji} {status or 'Not validated'}: {count} ({pct:.1f}%)")
    
    # Discovery metrics
    if stats['google_searched'] > 0:
        logger.info(f"\n🔎 GOOGLE SEARCH DISCOVERY")
        logger.info(f"  Businesses searched: {stats['google_searched']}")
        discovery_rate = ((with_url - status_counts.get('valid', 0)) / stats['google_searched'] * 100) if stats['google_searched'] > 0 else 0
        logger.info(f"  Discovery rate: ~{discovery_rate:.1f}%")
    
    # Recent activity
    if stats['recently_validated'] > 0:
        logger.info(f"\n⚡ RECENT ACTIVITY (last hour)")
        logger.info(f"  Validations completed: {stats['recently_validated']}")
        rate_per_minute = stats['recently_validated'] / 60
        logger.info(f"  Rate: ~{rate_per_minute:.1f} validations/minute")
    
    # Progress indicators
    missing_count = status_counts.get('missing', 0)
    pending_count = status_counts.get('pending', 0)
    
    if missing_count > 0 or pending_count > 0:
        logger.info(f"\n📈 PROGRESS")
        if pending_count > 0:
            logger.info(f"  ⏳ Pending: {pending_count} businesses awaiting validation")
        if missing_count > 0:
            logger.info(f"  🎯 Target: {missing_count} businesses need discovery")
            eta_minutes = missing_count * 1.0 / 60  # Assume 1 req/sec
            logger.info(f"  ⏱️  ETA: ~{eta_minutes:.0f} minutes at 1 req/sec")
    
    # Detailed breakdown
    if detailed:
        logger.info(f"\n📋 DETAILED BREAKDOWN")
        logger.info(f"  Valid websites: {status_counts.get('valid', 0)}")
        logger.info(f"  Invalid/Directories: {status_counts.get('invalid', 0)}")
        logger.info(f"  Triple-verified missing: {status_counts.get('missing', 0)}")
        logger.info(f"  Pending validation: {status_counts.get('pending', 0)}")
        logger.info(f"  Validation errors: {status_counts.get('error', 0)}")
    
    logger.info("\n" + "="*80 + "\n")


async def watch_progress(interval_seconds: int = 30):
    """
    Continuously monitor progress.
    
    Args:
        interval_seconds: Refresh interval in seconds
    """
    logger.info(f"📡 Watching progress (refresh every {interval_seconds}s)")
    logger.info("Press Ctrl+C to stop\n")
    
    try:
        while True:
            stats = await get_discovery_statistics()
            format_statistics(stats)
            
            logger.info(f"Refreshing in {interval_seconds} seconds...")
            await asyncio.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        logger.info("\n\n✋ Monitoring stopped by user.")


async def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Monitor website discovery progress",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--watch",
        type=int,
        metavar="SECONDS",
        help="Continuously monitor with refresh interval (seconds)"
    )
    
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed breakdown"
    )
    
    args = parser.parse_args()
    
    try:
        if args.watch:
            await watch_progress(interval_seconds=args.watch)
        else:
            stats = await get_discovery_statistics()
            format_statistics(stats, detailed=args.detailed)
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
