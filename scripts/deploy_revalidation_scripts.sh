#!/bin/bash
# Deploy revalidation scripts to server - run from project root
# Usage: ./scripts/deploy_revalidation_scripts.sh [user@server]
# Or copy manually: scp backend/scripts/revalidate_standalone.py backend/scripts/queue_missing_websites.py backend/scripts/run_full_verification.py user@server:/var/www/webmagic/backend/scripts/

set -e
SERVER="${1:-root@104.251.211.183}"
REMOTE="/var/www/webmagic/backend/scripts"

echo "Deploying revalidation scripts to $SERVER"
scp backend/scripts/revalidate_standalone.py "$SERVER:$REMOTE/"
scp backend/scripts/queue_missing_websites.py "$SERVER:$REMOTE/" 2>/dev/null || true
scp backend/scripts/run_full_verification.py "$SERVER:$REMOTE/" 2>/dev/null || true
echo "Done. Run on server:"
echo "  cd /var/www/webmagic/backend"
echo "  .venv/bin/python -m scripts.revalidate_standalone --scrapingdog --limit 50 --country US"
echo "  .venv/bin/python -m scripts.revalidate_standalone --playwright --limit 50"
