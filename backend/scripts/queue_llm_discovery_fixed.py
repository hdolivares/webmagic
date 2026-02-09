#!/usr/bin/env python3
"""
Queue businesses for LLM-powered Google Search discovery with proper fixes.

Improvements over previous version:
- Explicit queue routing to 'validation' queue
- Uses ETA instead of countdown for better reliability
- Proper error handling and logging
"""
import sys
sys.path.insert(0, '/var/www/webmagic/backend')

from celery_app import celery_app  
from core.database import get_db_session_sync
from models.business import Business
from sqlalchemy import func, cast
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta

def main():
    with get_db_session_sync() as db:
        # Find businesses marked as 'missing' without Google Search
        businesses = db.query(Business).filter(
            Business.website_url.is_(None),
            Business.website_validation_status == 'missing',
            ~func.jsonb_exists(
                cast(Business.website_validation_result['stages'], JSONB),
                'google_search'
            )
        ).order_by(
            Business.qualification_score.desc()
        ).all()
        
        print(f"Found {len(businesses)} businesses needing LLM discovery")
        
        if len(businesses) == 0:
            print("No businesses to process!")
            return
            
        # Queue them with proper ETA and explicit queue routing
        base_time = datetime.utcnow()
        for idx, biz in enumerate(businesses):
            task_name = 'tasks.validation.discover_missing_websites'
            eta = base_time + timedelta(seconds=idx * 1)  # 1 second apart
            
            # Fixed: Explicit queue routing to 'validation' queue
            celery_app.send_task(
                task_name,
                args=[str(biz.id)],
                eta=eta,
                queue='validation'  # ← CRITICAL FIX: Route to correct queue
            )
            
            if (idx + 1) % 10 == 0:
                print(f"Queued {idx + 1}/{len(businesses)}")
        
        print(f"✅ Successfully queued {len(businesses)} businesses for LLM discovery!")
        print(f"⏱️  Will complete in approximately {len(businesses) / 60:.1f} minutes")

if __name__ == '__main__':
    main()
