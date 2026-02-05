"""
Quick validation for suspicious "invalid" websites

Targets high-confidence false positives:
- Businesses with high ratings (4.5+) and many reviews (100+)
- Known chains (Roto-Rooter, Village Plumbing, etc.)
- URLs that look legitimate

Much faster than full validation - just checks if URL responds with ANY success code.

Run with: python -m scripts.quick_validate_suspicious
"""
import asyncio
import sys
from pathlib import Path
from typing import List
import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from core.database import AsyncSessionLocal
from models.business import Business
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def quick_check_url(url: str) -> dict:
    """Quick check if URL is accessible."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=True,
                ssl=False
            ) as response:
                return {
                    'accessible': response.status in [200, 301, 302, 303, 307, 308, 403, 429],
                    'status': response.status,
                    'protected': response.status in [403, 429]
                }
    except Exception as e:
        return {'accessible': False, 'error': str(e)[:100]}


async def quick_validate_suspicious():
    """Quickly validate businesses likely to be false positives."""
    
    logger.info("="*80)
    logger.info("QUICK VALIDATION: High-Risk False Positives")
    logger.info("="*80)
    
    async with AsyncSessionLocal() as db:
        # Get suspicious businesses (invalid with high ratings/reviews)
        result = await db.execute(
            select(Business).where(
                Business.website_status == 'queued',
                Business.website_validation_status == 'invalid',
                Business.website_url.is_not(None),
                Business.rating >= 4.5,
                Business.review_count >= 100
            ).order_by(Business.review_count.desc())
        )
        suspicious = result.scalars().all()
        
        # Also get known chains
        result2 = await db.execute(
            select(Business).where(
                Business.website_status == 'queued',
                Business.website_validation_status == 'invalid',
                Business.name.ilike('%roto-rooter%')
            )
        )
        chains = result2.scalars().all()
        
        businesses = list(set(suspicious + chains))  # Remove duplicates
        
        if not businesses:
            logger.info("✅ No suspicious businesses found")
            return
        
        logger.info(f"\nFound {len(businesses)} suspicious 'invalid' businesses")
        logger.info("(High ratings + many reviews = likely have websites)\n")
        
        stats = {'checked': 0, 'valid': 0, 'invalid': 0, 'removed_from_queue': 0}
        
        for business in businesses:
            logger.info(f"Checking: {business.name} ({business.city}, {business.state})")
            logger.info(f"  Rating: {business.rating}/5.0, Reviews: {business.review_count}")
            logger.info(f"  URL: {business.website_url}")
            
            result = await quick_check_url(business.website_url)
            stats['checked'] += 1
            
            if result.get('accessible'):
                status = result.get('status', 'unknown')
                protected = result.get('protected', False)
                
                logger.info(f"  ✅ VALID - HTTP {status} {'(protected)' if protected else ''}")
                
                # Update database
                business.website_validation_status = 'valid'
                business.website_validated_at = datetime.utcnow()
                business.website_status = 'none'
                business.generation_queued_at = None
                business.generation_attempts = 0
                
                stats['valid'] += 1
                stats['removed_from_queue'] += 1
            else:
                error = result.get('error', 'unknown')
                logger.info(f"  ❌ Still invalid - {error}")
                stats['invalid'] += 1
            
            # Commit every 5
            if stats['checked'] % 5 == 0:
                await db.commit()
                logger.info(f"\n💾 Progress saved ({stats['checked']}/{len(businesses)})\n")
        
        # Final commit
        await db.commit()
        
        logger.info("\n" + "="*80)
        logger.info("QUICK VALIDATION COMPLETE")
        logger.info("="*80)
        logger.info(f"Checked: {stats['checked']}")
        logger.info(f"  ✅ Now Valid: {stats['valid']}")
        logger.info(f"  ❌ Still Invalid: {stats['invalid']}")
        logger.info(f"  🚫 Removed from Queue: {stats['removed_from_queue']}")
        logger.info("="*80)
        
        return stats


if __name__ == "__main__":
    asyncio.run(quick_validate_suspicious())

