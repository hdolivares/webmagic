#!/usr/bin/env python3
"""
Reset failed generation tasks so they can be retried.
"""
import sys
sys.path.insert(0, '/var/www/webmagic/backend')

from core.database import get_db_session_sync
from models.business import Business

def main():
    with get_db_session_sync() as db:
        # Reset businesses that were queued but failed
        businesses = db.query(Business).filter(
            Business.website_validation_status == 'triple_verified',
            Business.website_url.is_(None),
            Business.website_status == 'queued'
        ).all()
        
        print(f"Found {len(businesses)} businesses to reset")
        
        for business in businesses:
            business.website_status = 'none'
            business.generation_queued_at = None
            business.generation_started_at = None
        
        db.commit()
        print(f"✅ Reset {len(businesses)} businesses - ready to re-queue")

if __name__ == '__main__':
    main()
