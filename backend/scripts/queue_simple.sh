#!/bin/bash
# Simple shell script to queue validation batches without Python hanging

cd /var/www/webmagic/backend

# Use Python one-liner to get business IDs
IDS=$(/var/www/webmagic/backend/.venv/bin/python << 'PYEOF'
import sys
sys.path.insert(0, '/var/www/webmagic/backend')
from core.database import get_db_session_sync
from models.business import Business

with get_db_session_sync() as db:
    businesses = db.query(Business.id).filter(
        Business.website_url.isnot(None),
        Business.website_validation_status == 'pending'
    ).limit(100).all()
    
    ids = [str(b.id) for b in businesses]
    print(','.join(ids))
PYEOF
)

echo "Found businesses to queue"
echo "$IDS" | tr ',' '\n' | wc -l

# Queue using celery call
COUNT=0
for id in $(echo "$IDS" | tr ',' ' '); do
    /var/www/webmagic/backend/.venv/bin/celery -A celery_app call tasks.validation_tasks.validate_business_website -a "['$id']" > /dev/null 2>&1 &
    COUNT=$((COUNT + 1))
    if [ $((COUNT % 10)) -eq 0 ]; then
        echo "Queued $COUNT tasks..."
        wait  # Wait for background processes
    fi
done

wait  # Wait for remaining processes
echo "✓ Queued $COUNT validation tasks"
echo "Monitor: tail -f /var/log/webmagic/celery.log"
