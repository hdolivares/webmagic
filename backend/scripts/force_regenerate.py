"""Force regenerate a site that shows 'ready' but has no HTML."""
import sys
sys.path.insert(0, '/var/www/webmagic/backend')

from celery_app import celery_app
from tasks.generation_sync import generate_site_for_business

# Get a business ID for one of the "ready" sites  
# We'll need to look it up from the subdomain

from sqlalchemy import create_engine, text
from core.config import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))

subdomain = 'citywide-plumbers-1770254202750-4a65af24'

print(f"\n🔍 Looking up business ID for {subdomain}...")

with engine.connect() as conn:
    result = conn.execute(text(f"""
        SELECT business_id, status, 
               CASE WHEN html_content IS NULL THEN 'NULL' ELSE 'Present' END as has_html
        FROM generated_sites 
        WHERE subdomain = '{subdomain}'
    """))
    row = result.fetchone()
    
    if not row:
        print(f"❌ Site not found: {subdomain}")
        sys.exit(1)
    
    business_id = str(row[0])
    status = row[1]
    has_html = row[2]
    
    print(f"✅ Found site:")
    print(f"   Business ID: {business_id}")
    print(f"   Status: {status}")
    print(f"   HTML: {has_html}\n")
    
    # Update status to pending to allow regeneration
    print(f"📝 Resetting site status to 'pending'...")
    conn.execute(text(f"""
        UPDATE generated_sites 
        SET status = 'pending',
            html_content = NULL,
            css_content = NULL,
            js_content = NULL
        WHERE subdomain = '{subdomain}'
    """))
    conn.commit()
    print(f"✅ Status reset\n")

# Trigger generation task
print(f"🚀 Triggering generation task...")
result = generate_site_for_business.apply_async(args=[business_id], queue='generation')
print(f"✅ Task queued: {result.id}")
print(f"\n💡 Check task status with:")
print(f"   celery -A celery_app inspect active")
print(f"\n🌐 Site will be available at:")
print(f"   https://sites.lavish.solutions/{subdomain}")

