#!/usr/bin/env python3
"""
Queue remaining businesses stuck in needs_discovery state.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from sqlalchemy import select

from core.database import get_db_session_sync
from models.business import Business
from tasks.discovery_tasks import discover_missing_websites_v2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    with get_db_session_sync() as db:
        # Get all businesses stuck in needs_discovery
        query = select(Business).where(
            Business.website_validation_status == "needs_discovery"
        )
        businesses = db.execute(query).scalars().all()
        
        logger.info(f"Found {len(businesses)} businesses in needs_discovery state")
        
        queued = 0
        failed = 0
        
        for business in businesses:
            try:
                task = discover_missing_websites_v2.delay(str(business.id))
                logger.info(f"✅ Queued: {business.name} (Task: {task.id})")
                queued += 1
            except Exception as e:
                logger.error(f"❌ Failed to queue {business.name}: {e}")
                failed += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Summary:")
        logger.info(f"  Total: {len(businesses)}")
        logger.info(f"  Queued: {queued}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"{'='*60}")
