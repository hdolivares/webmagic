"""
Handle businesses marked as 'invalid' that likely have websites but are bot-protected.

These businesses have:
- website_validation_status = 'invalid'
- website_url IS NOT NULL (they have URLs!)
- High ratings and review counts (avg 947 reviews!)

Strategy:
1. Try browser-based validation (Selenium/Playwright) for accurate results
2. For now, let user decide: keep for manual review OR try generation anyway

Usage: 
  python -m scripts.handle_invalid_websites --action review
  python -m scripts.handle_invalid_websites --action mark-needs-review
  python -m scripts.handle_invalid_websites --action try-generation --limit 3
"""
import asyncio
import sys
from pathlib import Path
from typing import List
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from core.database import AsyncSessionLocal
from models.business import Business
from tasks.generation_sync import generate_site_for_business
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def review_invalid_websites():
    """Review all businesses marked as 'invalid' with URLs."""
    
    logger.info("="*80)
    logger.info("INVALID WEBSITES REVIEW")
    logger.info("="*80)
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Business).where(
                Business.website_status == 'queued',
                Business.website_validation_status == 'invalid',
                Business.website_url.is_not(None)
            ).order_by(Business.review_count.desc())
        )
        businesses = result.scalars().all()
        
        if not businesses:
            logger.info("✅ No invalid businesses with URLs found")
            return
        
        logger.info(f"\nFound {len(businesses)} businesses with 'invalid' status but have URLs\n")
        
        # Group by domain patterns
        high_value = []  # 500+ reviews
        medium_value = []  # 100-499 reviews
        low_value = []  # <100 reviews
        
        for business in businesses:
            if business.review_count >= 500:
                high_value.append(business)
            elif business.review_count >= 100:
                medium_value.append(business)
            else:
                low_value.append(business)
        
        logger.info(f"📊 BREAKDOWN:")
        logger.info(f"  🔥 High Value (500+ reviews): {len(high_value)}")
        logger.info(f"  ⭐ Medium Value (100-499 reviews): {len(medium_value)}")
        logger.info(f"  📝 Low Value (<100 reviews): {len(low_value)}\n")
        
        # Show top 10
        logger.info("="*80)
        logger.info("TOP 10 HIGH-VALUE BUSINESSES (by reviews)")
        logger.info("="*80)
        
        for idx, business in enumerate(businesses[:10], 1):
            logger.info(f"\n{idx}. {business.name}")
            logger.info(f"   Location: {business.city}, {business.state}")
            logger.info(f"   Rating: {business.rating}/5.0 ({business.review_count} reviews)")
            logger.info(f"   URL: {business.website_url}")
            logger.info(f"   Phone: {business.phone or 'N/A'}")
        
        logger.info("\n" + "="*80)
        logger.info("RECOMMENDATIONS")
        logger.info("="*80)
        logger.info("These businesses likely HAVE websites but validation failed due to:")
        logger.info("  • Anti-bot protection (403/429 errors)")
        logger.info("  • Aggressive firewalls")
        logger.info("  • Geolocation blocks")
        logger.info("  • CAPTCHA requirements")
        logger.info("\nOptions:")
        logger.info("  1. Manual review - Visit URLs manually to verify")
        logger.info("  2. Browser-based validation - Use Selenium/Playwright")
        logger.info("  3. Mark as 'needs_review' - Flag for human verification")
        logger.info("  4. Skip generation - Don't waste tokens on these")
        logger.info("="*80)
        
        return businesses


async def mark_needs_review(dry_run: bool = True):
    """Mark invalid businesses as 'needs_review' to prevent auto-generation."""
    
    logger.info("="*80)
    logger.info(f"MARK AS NEEDS REVIEW - {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("="*80)
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Business).where(
                Business.website_status == 'queued',
                Business.website_validation_status == 'invalid',
                Business.website_url.is_not(None)
            )
        )
        businesses = result.scalars().all()
        
        logger.info(f"\nFound {len(businesses)} businesses to mark\n")
        
        if dry_run:
            logger.info("🔵 DRY RUN: Would mark these businesses as 'needs_review'")
            for business in businesses[:5]:
                logger.info(f"  - {business.name} ({business.review_count} reviews)")
            if len(businesses) > 5:
                logger.info(f"  ... and {len(businesses) - 5} more")
        else:
            # Update to needs_review status
            for business in businesses:
                business.website_validation_status = 'needs_review'
                business.website_status = 'none'  # Remove from auto-generation queue
                business.generation_queued_at = None
            
            await db.commit()
            logger.info(f"✅ Marked {len(businesses)} businesses as 'needs_review'")
            logger.info("   - Removed from auto-generation queue")
            logger.info("   - Can be manually reviewed and queued later")
        
        return businesses


async def try_generation(business_ids: List[str], dry_run: bool = True):
    """
    Try generation for specific invalid businesses (risky - use with caution).
    Only use for businesses you've manually verified have no usable website.
    """
    
    logger.info("="*80)
    logger.info(f"TRY GENERATION FOR INVALID - {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("="*80)
    logger.info("⚠️  WARNING: These businesses have URLs marked as 'invalid'")
    logger.info("⚠️  Only proceed if manually verified they need new websites\n")
    
    async with AsyncSessionLocal() as db:
        for business_id in business_ids:
            result = await db.execute(
                select(Business).where(Business.id == business_id)
            )
            business = result.scalar_one_or_none()
            
            if not business:
                logger.error(f"❌ Business not found: {business_id}")
                continue
            
            logger.info(f"📋 {business.name}")
            logger.info(f"   URL: {business.website_url}")
            logger.info(f"   Status: {business.website_validation_status}")
            
            if dry_run:
                logger.info(f"   🔵 DRY RUN: Would trigger generation")
            else:
                task = generate_site_for_business.apply_async(
                    args=[str(business_id)],
                    priority=5
                )
                logger.info(f"   ✅ Task queued: {task.id}")
            
            logger.info("")


async def main():
    parser = argparse.ArgumentParser(description='Handle invalid websites')
    parser.add_argument('--action', required=True, 
                       choices=['review', 'mark-needs-review', 'try-generation'],
                       help='Action to perform')
    parser.add_argument('--business-ids', nargs='*', 
                       help='Business IDs (for try-generation)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Dry run mode (no database changes)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of businesses to process')
    
    args = parser.parse_args()
    
    if args.action == 'review':
        await review_invalid_websites()
    
    elif args.action == 'mark-needs-review':
        await mark_needs_review(dry_run=args.dry_run)
    
    elif args.action == 'try-generation':
        if not args.business_ids:
            logger.error("❌ --business-ids required for try-generation")
            return
        await try_generation(args.business_ids, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())

