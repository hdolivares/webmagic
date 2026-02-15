#!/usr/bin/env python3
"""
Migration script to move businesses from old validation system to V2.

This script:
1. Identifies businesses with old validation statuses
2. Migrates their metadata to the new system
3. Queues appropriate businesses for re-validation or ScrapingDog discovery
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from sqlalchemy import select, func

from core.database import get_db_session_sync
from models.business import Business
from core.validation_enums import ValidationState, URLSource
from services.validation.validation_metadata_service import ValidationMetadataService
from tasks.validation_tasks_enhanced import validate_business_website_v2
from tasks.discovery_tasks import discover_missing_websites_v2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_missing_businesses(dry_run: bool = True, limit: int = None):
    """
    Migrate "missing" businesses to new validation system.
    
    These businesses:
    - Had no URL from Outscraper
    - Were marked "missing" by old system
    - Should be queued for ScrapingDog discovery
    """
    with get_db_session_sync() as db:
        metadata_service = ValidationMetadataService()
        
        # Get all "missing" businesses
        query = select(Business).where(Business.website_validation_status == "missing")
        if limit:
            query = query.limit(limit)
        
        businesses = db.execute(query).scalars().all()
        
        logger.info(f"Found {len(businesses)} businesses with 'missing' status")
        
        if dry_run:
            logger.info("DRY RUN - No changes will be made")
        
        migrated_count = 0
        queued_for_discovery = 0
        
        for business in businesses:
            logger.info(f"\n{'='*60}")
            logger.info(f"Business: {business.name}")
            logger.info(f"  City/State: {business.city}, {business.state}")
            logger.info(f"  Current Status: {business.website_validation_status}")
            outscraper_url = (business.raw_data or {}).get('outscraper', {}).get('website', 'None')
            logger.info(f"  Outscraper URL: {outscraper_url}")
            
            if dry_run:
                logger.info(f"  → Would migrate to: {ValidationState.NEEDS_DISCOVERY.value}")
                logger.info(f"  → Would queue for ScrapingDog discovery")
                migrated_count += 1
                queued_for_discovery += 1
                continue
            
            # Initialize metadata if needed
            if not business.website_metadata:
                business.website_metadata = {}
            
            # Update to new system
            business.website_metadata = metadata_service.update_url_source(
                business.website_metadata,
                source=URLSource.NONE.value,
                url=None
            )
            
            # Record that we checked Outscraper and found nothing
            business.website_metadata = metadata_service.record_discovery_attempt(
                business.website_metadata,
                method="outscraper",
                found_url=False,
                url_found=None,
                valid=False,
                notes="Outscraper provided no URL - migrated from old 'missing' status"
            )
            
            # Update status to needs_discovery
            business.website_validation_status = ValidationState.NEEDS_DISCOVERY.value
            
            db.commit()
            
            # Queue for ScrapingDog discovery
            try:
                task = discover_missing_websites_v2.delay(str(business.id))
                logger.info(f"  ✅ Queued for discovery: {task.id}")
                queued_for_discovery += 1
            except Exception as e:
                logger.error(f"  ❌ Failed to queue: {e}")
            
            migrated_count += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Migration Summary:")
        logger.info(f"  Total processed: {len(businesses)}")
        logger.info(f"  Migrated: {migrated_count}")
        logger.info(f"  Queued for discovery: {queued_for_discovery}")
        
        return {
            "total": len(businesses),
            "migrated": migrated_count,
            "queued": queued_for_discovery
        }


def migrate_pending_businesses(dry_run: bool = True, limit: int = None):
    """
    Re-validate "pending" businesses with new V2 system.
    
    These have URLs from Outscraper that need validation.
    """
    with get_db_session_sync() as db:
        query = select(Business).where(
            Business.website_validation_status == "pending",
            Business.website_url != None
        )
        if limit:
            query = query.limit(limit)
        
        businesses = db.execute(query).scalars().all()
        
        logger.info(f"Found {len(businesses)} pending businesses")
        
        if dry_run:
            logger.info("DRY RUN - No changes will be made")
        
        queued_count = 0
        
        for business in businesses:
            logger.info(f"\nBusiness: {business.name} - URL: {business.website_url}")
            
            if dry_run:
                logger.info(f"  → Would queue for V2 validation")
                queued_count += 1
                continue
            
            try:
                task = validate_business_website_v2.delay(str(business.id))
                logger.info(f"  ✅ Queued for validation: {task.id}")
                queued_count += 1
            except Exception as e:
                logger.error(f"  ❌ Failed to queue: {e}")
        
        logger.info(f"\nQueued {queued_count} businesses for validation")
        
        return {
            "total": len(businesses),
            "queued": queued_count
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate businesses to Validation V2")
    parser.add_argument(
        "--mode",
        choices=["missing", "pending", "all"],
        default="missing",
        help="Which businesses to migrate"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform migration (default is dry-run)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of businesses to process"
    )
    
    args = parser.parse_args()
    dry_run = not args.execute
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    else:
        logger.info("⚠️  EXECUTE MODE - Changes WILL be made")
    
    if args.mode in ["missing", "all"]:
        logger.info("\n" + "="*60)
        logger.info("MIGRATING 'MISSING' BUSINESSES")
        logger.info("="*60)
        migrate_missing_businesses(dry_run=dry_run, limit=args.limit)
    
    if args.mode in ["pending", "all"]:
        logger.info("\n" + "="*60)
        logger.info("RE-VALIDATING 'PENDING' BUSINESSES")
        logger.info("="*60)
        migrate_pending_businesses(dry_run=dry_run, limit=args.limit)
    
    if dry_run:
        logger.info("\n✅ Dry run complete. Use --execute to actually perform migration.")
    else:
        logger.info("\n✅ Migration complete!")
