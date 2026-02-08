"""
Queue all businesses with URLs for Celery validation (no async).
Avoids hanging issues by using synchronous psycopg2 instead of async.
"""
import os
import sys
sys.path.insert(0, '/var/www/webmagic/backend')

# Use synchronous psycopg2 directly
import psycopg2
from urllib.parse import urlparse

# Get database URL from environment
os.chdir('/var/www/webmagic/backend')
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment")
    sys.exit(1)

# Parse the async URL to sync format
parsed = urlparse(DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))

# Connect to database
print("Connecting to database...")
conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port,
    user=parsed.username,
    password=parsed.password,
    dbname=parsed.path.lstrip('/')
)
cur = conn.cursor()

# Reset all businesses with URLs to pending
print("Resetting businesses to pending status...")
cur.execute("""
    UPDATE businesses 
    SET 
        website_validation_status = 'pending',
        validation_notes = 'Reset for LLM revalidation - ' || CURRENT_TIMESTAMP
    WHERE website_url IS NOT NULL AND website_url != ''
""")
conn.commit()
reset_count = cur.rowcount
print(f"Reset {reset_count} businesses to pending")

# Get all business IDs that need validation
cur.execute("""
    SELECT id 
    FROM businesses 
    WHERE website_url IS NOT NULL 
      AND website_url != ''
    ORDER BY website_validated_at ASC NULLS FIRST
""")
business_ids = [str(row[0]) for row in cur.fetchall()]

cur.close()
conn.close()

print(f"Found {len(business_ids)} businesses to validate")

# Now queue them using Celery
print("Importing Celery tasks...")
from tasks.validation_tasks import batch_validate_websites

batch_size = 10
tasks_queued = 0

print(f"Queuing {len(business_ids)} businesses in batches of {batch_size}...")
for i in range(0, len(business_ids), batch_size):
    batch = business_ids[i:i + batch_size]
    batch_validate_websites.delay(batch)
    tasks_queued += 1
    if tasks_queued % 10 == 0:
        print(f"  Queued {tasks_queued} batches ({i + len(batch)} businesses)...")

print(f"\n✓ Successfully queued {tasks_queued} validation batches")
print(f"✓ Total businesses queued: {len(business_ids)}")
print("\nCheck Celery logs for validation progress:")
print("  tail -f /var/log/webmagic/celery.log")
