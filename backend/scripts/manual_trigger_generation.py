"""
Manual trigger for site generation.
Run this to manually generate HTML for a specific site.
"""
import asyncio
import sys
from sqlalchemy import select

# Add backend to path
sys.path.insert(0, '/var/www/webmagic/backend')

from core.database import AsyncSessionLocal
from models.site import GeneratedSite
from models.business import Business
from services.creative.orchestrator import CreativeOrchestrator

async def generate_site_manually(subdomain: str):
    """Manually generate HTML for a site."""
    print(f"\n🔧 Manual Site Generation")
    print(f"{'='*70}")
    print(f"Subdomain: {subdomain}\n")
    
    async with AsyncSessionLocal() as db:
        # Find the site
        result = await db.execute(
            select(GeneratedSite).where(GeneratedSite.subdomain == subdomain)
        )
        site = result.scalar_one_or_none()
        
        if not site:
            print(f"❌ Site not found: {subdomain}")
            return
        
        print(f"✅ Found site (ID: {site.id})")
        print(f"   Status: {site.status}")
        print(f"   Business ID: {site.business_id}")
        print(f"   HTML Content: {'Present' if site.html_content else 'NULL'}\n")
        
        # Get business
        if not site.business_id:
            print(f"❌ No business_id associated with this site")
            return
        
        result = await db.execute(
            select(Business).where(Business.id == site.business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business:
            print(f"❌ Business not found: {site.business_id}")
            return
        
        print(f"✅ Found business: {business.name}")
        print(f"   Category: {business.category}")
        print(f"   Location: {business.city}, {business.state}\n")
        
        # Update site status to generating
        site.status = 'generating'
        await db.commit()
        print(f"📝 Updated site status to 'generating'\n")
        
        try:
            # Initialize creative orchestrator
            print(f"🎨 Initializing Creative Orchestrator...")
            orchestrator = CreativeOrchestrator()
            
            # Generate website
            print(f"🚀 Generating website...")
            print(f"   This may take 30-60 seconds...\n")
            
            result = await orchestrator.generate_website(
                business_id=str(business.id),
                business_name=business.name,
                category=business.category or 'Business',
                location=f"{business.city}, {business.state}" if business.city else None,
                email=business.email,
                phone=business.phone
            )
            
            if result['status'] == 'success':
                # Update site with generated content
                site.html_content = result['html']
                site.css_content = result.get('css')
                site.js_content = result.get('js')
                site.status = 'completed'
                
                await db.commit()
                
                print(f"\n✅ GENERATION SUCCESSFUL!")
                print(f"   HTML Size: {len(result['html'])} bytes")
                print(f"   CSS Size: {len(result.get('css', ''))} bytes")
                print(f"   JS Size: {len(result.get('js', ''))} bytes")
                print(f"\n🌐 Site URL: https://sites.lavish.solutions/{subdomain}")
                
            else:
                site.status = 'failed'
                await db.commit()
                print(f"\n❌ GENERATION FAILED!")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            site.status = 'failed'
            await db.commit()
            print(f"\n❌ EXCEPTION DURING GENERATION!")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manual_trigger_generation.py <subdomain>")
        print("\nExample:")
        print("  python manual_trigger_generation.py mayfair-plumbers-1770254203251-83b6e7b8")
        sys.exit(1)
    
    subdomain = sys.argv[1]
    asyncio.run(generate_site_manually(subdomain))

