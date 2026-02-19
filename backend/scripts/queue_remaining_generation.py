#!/usr/bin/env python3
"""
Quick script to queue remaining businesses for generation.
Non-interactive, no confirmation prompts.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone
from core.database import get_db_session_sync
from models.business import Business
from celery_app import celery_app


def main():
    """Queue businesses that are marked 'queued' but never actually sent to Celery."""
    print("🔄 QUEUE REMAINING BUSINESSES FOR GENERATION")
    print("=" * 70)
    
    with get_db_session_sync() as db:
        # Find US businesses marked as queued but never started (SMS only works for US)
        businesses = db.query(Business).filter(
            Business.country == 'US',
            Business.website_validation_status == 'triple_verified',
            Business.website_url.is_(None),
            Business.qualification_score >= 70,
            Business.website_status == 'queued',
            Business.generation_started_at.is_(None)  # Never actually started
        ).all()
        
        if not businesses:
            print("✅ No businesses need queuing - all are either completed or actively processing!")
            return
        
        print(f"\n📋 Found {len(businesses)} businesses to queue:\n")
        for idx, biz in enumerate(businesses[:10], 1):
            print(f"   {idx}. {biz.name} ({biz.city}, {biz.state or 'N/A'})")
        if len(businesses) > 10:
            print(f"   ... and {len(businesses) - 10} more")
        
        print(f"\n🔄 Queuing {len(businesses)} businesses...")
        
        task_name = 'tasks.generation_sync.generate_site_for_business'
        queued_count = 0
        
        for idx, business in enumerate(businesses):
            try:
                # Send task to Celery queue
                celery_app.send_task(
                    task_name,
                    args=[str(business.id)],
                    queue='generation'
                )
                queued_count += 1
                
                if (idx + 1) % 5 == 0:
                    print(f"   Queued {idx + 1}/{len(businesses)}...")
                    
            except Exception as e:
                print(f"   ⚠️  Failed to queue {business.name}: {e}")
        
        print(f"\n✅ Successfully queued {queued_count}/{len(businesses)} businesses!")
        print("=" * 70)
        print(f"\n📊 QUEUE STATUS:")
        print(f"   • Tasks sent to Celery: {queued_count}")
        print(f"   • Estimated completion: {queued_count * 4} minutes (single worker)")
        print(f"   • Queue: generation")
        print("=" * 70)


if __name__ == '__main__':
    main()
