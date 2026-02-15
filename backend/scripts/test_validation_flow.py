#!/usr/bin/env python3
"""
Test the complete validation flow with the new system.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from tasks.validation_tasks_enhanced import validate_business_website_v2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("business_id", help="Business UUID to test")
    args = parser.parse_args()
    
    logger.info(f"Queuing validation for business: {args.business_id}")
    
    # Queue validation with NEW system
    task = validate_business_website_v2.delay(args.business_id)
    
    logger.info(f"✅ Task queued: {task.id}")
    logger.info(f"\nTo monitor:")
    logger.info(f"  - Check Celery logs: tail -f /var/log/webmagic/celery.log")
    logger.info(f"  - Check task status: celery -A celery_app result {task.id}")
    logger.info(f"  - Query database:")
    logger.info(f"    SELECT name, website_validation_status, website_metadata")
    logger.info(f"    FROM businesses WHERE id = '{args.business_id}';")
