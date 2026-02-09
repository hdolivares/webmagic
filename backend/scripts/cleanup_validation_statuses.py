#!/usr/bin/env python3
"""
Pragmatic cleanup script for validation statuses.

After multiple failed discovery attempts, this script:
1. Marks confirmed missing websites as triple_verified (ready for generation)
2. Marks uncertain businesses as having valid websites (to avoid wasting tokens)
"""
import sys
sys.path.insert(0, '/var/www/webmagic/backend')

import asyncio
from core.database import get_db_session_sync
from models.business import Business
from sqlalchemy import func, cast
from sqlalchemy.dialects.postgresql import JSONB

def main():
    print("🔧 PRAGMATIC VALIDATION CLEANUP")
    print("="*70)
    
    with get_db_session_sync() as db:
        # Step 1: Find businesses with confirmed NO website (Google searched, not found)
        confirmed_missing = db.query(Business).filter(
            Business.website_url.is_(None),
            Business.website_validation_status == 'missing',
            func.jsonb_exists(
                cast(Business.website_validation_result['stages'], JSONB),
                'google_search'
            )
        ).all()
        
        print(f"\n1️⃣  Found {len(confirmed_missing)} businesses with CONFIRMED NO WEBSITE")
        print("   → Will mark as 'triple_verified' and queue for generation")
        
        # Step 2: Find businesses never searched (uncertain)
        uncertain = db.query(Business).filter(
            Business.website_url.is_(None),
            Business.website_validation_status == 'missing',
            ~func.jsonb_exists(
                cast(Business.website_validation_result['stages'], JSONB),
                'google_search'
            )
        ).all()
        
        print(f"\n2️⃣  Found {len(uncertain)} businesses NEVER SEARCHED (uncertain)")
        print("   → Will mark as having valid website to avoid wasting tokens")
        
        # Confirm action
        print("\n" + "="*70)
        response = input("\n⚠️  Proceed with cleanup? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("❌ Cancelled by user")
            return
        
        # Execute Step 1: Mark confirmed missing as triple_verified
        print(f"\n✅ Marking {len(confirmed_missing)} confirmed_missing as triple_verified...")
        for business in confirmed_missing:
            business.website_validation_status = 'triple_verified'
            business.validation_stage = 'verified'
            # Keep website_url as None - they genuinely have no website
        
        # Execute Step 2: Mark uncertain as having valid website
        print(f"✅ Marking {len(uncertain)} uncertain businesses as having valid website...")
        for business in uncertain:
            # Set a placeholder URL to prevent generation
            business.website_url = "https://placeholder-valid-website.com"
            business.website_validation_status = 'valid'
            business.validation_stage = 'complete'
            business.website_validation_result = {
                "status": "marked_as_valid_to_skip_generation",
                "reason": "Discovery process failed multiple times - marked as valid to avoid token waste",
                "stages": {
                    "cleanup": {
                        "action": "marked_valid",
                        "date": "2026-02-09"
                    }
                }
            }
        
        # Commit changes
        db.commit()
        
        print("\n" + "="*70)
        print(f"✅ CLEANUP COMPLETE!")
        print(f"   • {len(confirmed_missing)} businesses ready for generation")
        print(f"   • {len(uncertain)} businesses marked as valid (skipped)")
        print("="*70)
        
        # Show final stats
        total_qualified = db.query(Business).filter(
            Business.qualification_score >= 70
        ).count()
        
        ready_for_generation = db.query(Business).filter(
            Business.website_url.is_(None),
            Business.website_validation_status == 'triple_verified',
            Business.qualification_score >= 70
        ).count()
        
        print(f"\n📊 FINAL STATISTICS:")
        print(f"   • Total qualified businesses (score ≥70): {total_qualified}")
        print(f"   • Ready for website generation: {ready_for_generation}")
        print("="*70)

if __name__ == '__main__':
    main()
