#!/usr/bin/env python3
"""
Queue qualified businesses without websites for AI generation.

This script finds businesses that are:
- Triple-verified (no existing website)
- Qualified (score >= 70)
- Not already generated or in progress

And queues them for AI website generation.
"""
import sys
sys.path.insert(0, '/var/www/webmagic/backend')

from celery_app import celery_app
from core.database import get_db_session_sync
from models.business import Business
from datetime import datetime, timedelta

def main():
    print("🚀 QUEUE QUALIFIED BUSINESSES FOR GENERATION")
    print("="*70)
    
    with get_db_session_sync() as db:
        # Find US businesses ready for generation (SMS only works for US)
        businesses = db.query(Business).filter(
            Business.country == 'US',
            Business.website_url.is_(None),
            Business.website_validation_status == 'triple_verified',
            Business.qualification_score >= 70,
            Business.website_status.in_(['none', 'pending', None])
        ).order_by(
            Business.qualification_score.desc()
        ).all()
        
        if not businesses:
            print("❌ No businesses found ready for generation")
            return
        
        print(f"\n✅ Found {len(businesses)} businesses ready for generation:")
        print()
        for idx, biz in enumerate(businesses[:10], 1):
            print(f"   {idx}. {biz.name} ({biz.city}, {biz.state}) - Score: {biz.qualification_score}")
        
        if len(businesses) > 10:
            print(f"   ... and {len(businesses) - 10} more")
        
        print("\n" + "="*70)
        response = input(f"\n⚠️  Queue {len(businesses)} businesses for generation? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("❌ Cancelled by user")
            return
        
        # Queue generation tasks
        print(f"\n🔄 Queueing {len(businesses)} businesses...")
        
        for idx, business in enumerate(businesses):
            # Queue generation task
            task_name = 'tasks.generation_sync.generate_site_for_business'
            
            celery_app.send_task(
                task_name,
                args=[str(business.id)],
                queue='generation'
            )
            
            # Update status
            business.website_status = 'queued'
            business.generation_queued_at = datetime.utcnow()
            
            if (idx + 1) % 5 == 0:
                print(f"   Queued {idx + 1}/{len(businesses)}...")
        
        # Commit status updates
        db.commit()
        
        print(f"\n✅ Successfully queued {len(businesses)} businesses for generation!")
        print("="*70)
        
        print("\n📊 GENERATION QUEUE:")
        print(f"   • Businesses queued: {len(businesses)}")
        print(f"   • Estimated completion time: {len(businesses) * 3} minutes")
        print(f"   • Queue: generation")
        print("="*70)

if __name__ == '__main__':
    main()
