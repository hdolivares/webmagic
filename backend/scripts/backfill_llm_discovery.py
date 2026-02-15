"""
Backfill script to run LLM discovery on existing businesses with missing websites.

This script processes all businesses that were scraped BEFORE LLM discovery was implemented,
or any businesses that failed to run through deep verification.

Usage:
    python scripts/backfill_llm_discovery.py --limit 50 --dry-run
    python scripts/backfill_llm_discovery.py --batch-size 10
"""
import asyncio
import argparse
import logging
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_db
from models.business import Business
from services.discovery.llm_discovery_service import LLMDiscoveryService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def backfill_missing_websites(
    limit: int = None,
    batch_size: int = 10,
    dry_run: bool = False,
    only_null_raw_data: bool = False
):
    """
    Backfill LLM discovery for businesses with missing websites.
    
    Args:
        limit: Maximum number of businesses to process
        batch_size: Number of businesses to process in parallel
        dry_run: If True, only show what would be processed
        only_null_raw_data: If True, only process businesses with NULL raw_data
    """
    logger.info("🚀 Starting LLM discovery backfill...")
    logger.info(f"   Limit: {limit or 'No limit'}")
    logger.info(f"   Batch size: {batch_size}")
    logger.info(f"   Dry run: {dry_run}")
    logger.info(f"   Only NULL raw_data: {only_null_raw_data}")
    
    async for db in get_async_db():
        try:
            # Build query for businesses needing discovery
            query = select(Business).where(
                and_(
                    Business.website_url.is_(None),
                    or_(
                        Business.website_validation_status == 'missing',
                        Business.website_validation_status == 'confirmed_missing',
                        Business.website_validation_status == 'pending'
                    )
                )
            )
            
            # Optional: Only businesses with NULL raw_data (old pipeline)
            if only_null_raw_data:
                query = query.where(Business.raw_data.is_(None))
            
            query = query.order_by(Business.created_at)
            
            if limit:
                query = query.limit(limit)
            
            result = await db.execute(query)
            businesses = result.scalars().all()
            
            if not businesses:
                logger.info("✅ No businesses need backfill!")
                return
            
            logger.info(f"📊 Found {len(businesses)} businesses needing LLM discovery")
            
            if dry_run:
                logger.info("\n🔍 DRY RUN - Would process these businesses:")
                for i, biz in enumerate(businesses[:20], 1):
                    logger.info(
                        f"   {i}. {biz.name} | {biz.city}, {biz.state} | "
                        f"Phone: {biz.phone or 'N/A'} | "
                        f"Status: {biz.website_validation_status} | "
                        f"Created: {biz.created_at}"
                    )
                if len(businesses) > 20:
                    logger.info(f"   ... and {len(businesses) - 20} more")
                return
            
            # Initialize LLM discovery service
            llm_discovery = LLMDiscoveryService()
            
            # Process in batches to respect rate limits
            total_processed = 0
            total_found = 0
            total_not_found = 0
            total_errors = 0
            
            for i in range(0, len(businesses), batch_size):
                batch = businesses[i:i+batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(businesses) + batch_size - 1) // batch_size
                
                logger.info(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} businesses)...")
                
                # Process batch in parallel (with rate limiting handled by service)
                tasks = []
                for biz in batch:
                    tasks.append(process_business(db, llm_discovery, biz))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count results
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"❌ Batch error: {result}")
                        total_errors += 1
                    elif result == "found":
                        total_found += 1
                    elif result == "not_found":
                        total_not_found += 1
                    elif result == "error":
                        total_errors += 1
                
                total_processed += len(batch)
                
                logger.info(
                    f"   ✅ Batch complete: {total_processed}/{len(businesses)} processed | "
                    f"Found: {total_found} | Not found: {total_not_found} | Errors: {total_errors}"
                )
                
                # Rate limiting between batches (1 second per business)
                if i + batch_size < len(businesses):
                    wait_time = batch_size * 1.0
                    logger.info(f"   ⏱️  Waiting {wait_time}s before next batch (rate limiting)...")
                    await asyncio.sleep(wait_time)
            
            # Final summary
            logger.info("\n" + "="*80)
            logger.info("🎉 BACKFILL COMPLETE!")
            logger.info(f"   Total processed: {total_processed}")
            logger.info(f"   ✅ Websites found: {total_found} ({total_found/total_processed*100:.1f}%)")
            logger.info(f"   ❌ Not found: {total_not_found} ({total_not_found/total_processed*100:.1f}%)")
            logger.info(f"   💥 Errors: {total_errors}")
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"Fatal error during backfill: {e}", exc_info=True)
        finally:
            await db.close()


async def process_business(
    db: AsyncSession,
    llm_discovery: LLMDiscoveryService,
    business: Business
) -> str:
    """
    Process a single business through LLM discovery.
    
    Returns:
        "found", "not_found", or "error"
    """
    try:
        logger.info(f"  🔍 Processing: {business.name} ({business.city}, {business.state})")
        
        # Run LLM discovery
        discovery_result = await llm_discovery.discover_website(
            business_name=business.name,
            phone=business.phone,
            address=business.address,
            city=business.city,
            state=business.state,
            country=business.country or "US"
        )
        
        if discovery_result.get("found") and discovery_result.get("url"):
            verified_url = discovery_result["url"]
            confidence = discovery_result.get("confidence", 0)
            
            logger.info(
                f"     ✅ FOUND: {verified_url} "
                f"(confidence: {confidence:.0%})"
            )
            
            # Update business
            business.website_url = verified_url
            business.website_validation_status = "pending"  # Queue for Playwright
            business.verified = True
            business.discovered_urls = [verified_url]
            
            # Store discovery data
            if not business.raw_data:
                business.raw_data = {}
            business.raw_data["llm_discovery"] = {
                "url": verified_url,
                "confidence": confidence,
                "reasoning": discovery_result.get("reasoning"),
                "verified_at": datetime.utcnow().isoformat(),
                "method": "backfill_scrapingdog_llm",
                "query": discovery_result.get("query"),
                "llm_model": discovery_result.get("llm_model"),
                "scrapingdog_results": discovery_result.get("search_results"),
                "llm_analysis": discovery_result.get("llm_analysis")
            }
            
            await db.commit()
            return "found"
        else:
            logger.info(
                f"     ❌ NOT FOUND: {discovery_result.get('reasoning', 'Unknown')}"
            )
            
            # Update business
            business.website_validation_status = "confirmed_missing"
            business.verified = True
            
            # Store discovery data
            if not business.raw_data:
                business.raw_data = {}
            business.raw_data["llm_discovery"] = {
                "url": None,
                "confidence": discovery_result.get("confidence", 0.95),
                "reasoning": discovery_result.get("reasoning"),
                "verified_at": datetime.utcnow().isoformat(),
                "method": "backfill_scrapingdog_llm",
                "query": discovery_result.get("query"),
                "llm_model": discovery_result.get("llm_model"),
                "scrapingdog_results": discovery_result.get("search_results"),
                "llm_analysis": discovery_result.get("llm_analysis")
            }
            
            await db.commit()
            return "not_found"
            
    except Exception as e:
        logger.error(f"     💥 ERROR processing {business.name}: {e}", exc_info=True)
        await db.rollback()
        return "error"


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill LLM discovery for businesses with missing websites"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of businesses to process"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of businesses to process in parallel (default: 10)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes"
    )
    parser.add_argument(
        "--only-null-raw-data",
        action="store_true",
        help="Only process businesses with NULL raw_data (old pipeline)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(backfill_missing_websites(
        limit=args.limit,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        only_null_raw_data=args.only_null_raw_data
    ))


if __name__ == "__main__":
    main()
