"""
Simple script to queue validation tasks - no hanging!
Uses subprocess to call celery send-task directly.
"""
import os
import sys
import subprocess
import json
sys.path.insert(0, '/var/www/webmagic/backend')

import psycopg2
from urllib.parse import urlparse

# Setup
os.chdir('/var/www/webmagic/backend')
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found")
    sys.exit(1)

# Parse URL
parsed = urlparse(DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))

# Connect
print("Connecting to database...")
conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port,
    user=parsed.username,
    password=parsed.password,
    dbname=parsed.path.lstrip('/')
)
cur = conn.cursor()

# Get businesses
print("Fetching businesses...")
cur.execute("""
    SELECT id 
    FROM businesses 
    WHERE website_validation_status = 'pending'
      AND website_url IS NOT NULL 
      AND website_url != ''
    ORDER BY website_validated_at ASC NULLS FIRST
    LIMIT 500
""")
business_ids = [str(row[0]) for row in cur.fetchall()]
cur.close()
conn.close()

print(f"Found {len(business_ids)} businesses to validate")

if not business_ids:
    print("No businesses to validate!")
    sys.exit(0)

# Queue using celery CLI (no Python import needed!)
batch_size = 10
venv_python = '/var/www/webmagic/backend/.venv/bin/python'
celery_bin = '/var/www/webmagic/backend/.venv/bin/celery'

print(f"Queuing {len(business_ids)} businesses in batches of {batch_size}...")
tasks_queued = 0

for i in range(0, len(business_ids), batch_size):
    batch = business_ids[i:i + batch_size]
    
    # Use celery send-task command (doesn't require importing the task!)
    # Format: celery -A app call task.name --args='[["list", "of", "args"]]'
    args_json = json.dumps([batch])  # Wrap batch in another list (positional args)
    cmd = [
        celery_bin,
        '-A', 'celery_app',
        'call',
        'tasks.validation_tasks.batch_validate_websites',
        '--args', args_json
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, cwd='/var/www/webmagic/backend')
        if result.returncode == 0:
            tasks_queued += 1
            if tasks_queued % 10 == 0:
                print(f"  Queued {tasks_queued} batches...")
        else:
            print(f"  Error queuing batch: {result.stderr}")
    except subprocess.TimeoutExpired:
        print(f"  Timeout queuing batch {i//batch_size + 1}")
    except Exception as e:
        print(f"  Exception: {e}")

print(f"\n✓ Queued {tasks_queued} batches")
print(f"✓ Total businesses: {len(business_ids)}")
print("\nMonitor progress:")
print("  tail -f /var/log/webmagic/celery.log")
