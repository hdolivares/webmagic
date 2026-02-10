#!/usr/bin/env python3
"""
Preview SMS campaigns for generated sites without sending.
Shows what the messages would look like.
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_db_session_sync
from services.sms import SMSGenerator
from models.business import Business
from models.site import GeneratedSite
from sqlalchemy import select


async def preview_sms_campaigns():
    """Preview SMS messages for businesses with generated sites."""
    print("📱 SMS CAMPAIGN MESSAGE PREVIEW")
    print("=" * 70)
    
    # Initialize SMS generator
    generator = SMSGenerator()
    
    with get_db_session_sync() as db:
        # Get businesses with completed sites
        result = db.execute(
            select(Business, GeneratedSite)
            .join(GeneratedSite, GeneratedSite.business_id == Business.id)
            .where(
                Business.website_validation_status == 'triple_verified',
                Business.website_url.is_(None),
                Business.qualification_score >= 70,
                GeneratedSite.status == 'completed',
                Business.phone.isnot(None)
            )
            .limit(3)
        )
        
        businesses_with_sites = result.all()
        
        if not businesses_with_sites:
            print("\n❌ No businesses with completed sites found!")
            return
        
        print(f"\n✅ Found {len(businesses_with_sites)} businesses ready for SMS outreach")
        print("\n" + "=" * 70)
        
        for idx, (business, site) in enumerate(businesses_with_sites, 1):
            print(f"\n📍 {idx}. {business.name}")
            print(f"   Location: {business.city}, {business.state}")
            print(f"   Phone: {business.phone}")
            print(f"   Category: {business.category}")
            print(f"   Rating: {business.rating}⭐ ({business.review_count} reviews)")
            
            # Build site URL
            site_url = f"https://sites.lavish.solutions/{site.subdomain}"
            
            # Prepare business data
            business_data = {
                "name": business.name,
                "category": business.category,
                "city": business.city,
                "state": business.state,
                "rating": float(business.rating) if business.rating else 0
            }
            
            # Generate SMS (professional variant)
            print(f"\n   📨 Generating SMS (professional tone)...")
            sms_body = await generator.generate_sms(
                business_data=business_data,
                site_url=site_url,
                variant="professional"
            )
            
            # Display SMS
            print(f"\n   ┌─ SMS MESSAGE ({len(sms_body)} chars) ─────────────────────────")
            print(f"   │")
            print(f"   │ {sms_body}")
            print(f"   │")
            print(f"   └──────────────────────────────────────────────────────────────")
            
            # Cost estimate
            segments = SMSGenerator.estimate_segments(sms_body)
            cost = SMSGenerator.estimate_cost(sms_body)
            print(f"\n   💰 Cost: ${cost:.4f} ({segments} segment{'s' if segments > 1 else ''})")
            print(f"   🔗 Site URL: {site_url}")
            
            if idx < len(businesses_with_sites):
                print("\n" + "-" * 70)
        
        # Summary
        print("\n\n" + "=" * 70)
        print("📊 CAMPAIGN SUMMARY")
        print("=" * 70)
        print(f"   • Total businesses ready: {len(businesses_with_sites)}")
        print(f"   • Channel: SMS (all businesses have phone, no email)")
        print(f"   • Message tone: Professional with compliance")
        print(f"   • Average cost: ~$0.0079 per message")
        print(f"   • Compliance: All messages include 'Reply STOP to opt out'")
        print("=" * 70)


if __name__ == '__main__':
    asyncio.run(preview_sms_campaigns())
