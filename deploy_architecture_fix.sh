#!/bin/bash
# Deployment script for Short Link Architecture Fix
# Creates short links at site generation (not preview) to prevent race conditions

set -e

echo "=========================================="
echo "Short Link Architecture Fix Deployment"
echo "=========================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DB_NAME="webmagic"
DB_USER="webmagic_user"
BACKEND_DIR="/var/www/webmagic/backend"

echo -e "${BLUE}Step 1: Pull latest code${NC}"
echo "------------------------"
cd /var/www/webmagic
git pull origin main
echo -e "${GREEN}✓${NC} Code updated"
echo ""

echo -e "${BLUE}Step 2: Run database migration${NC}"
echo "-------------------------------"
psql -U "$DB_USER" -d "$DB_NAME" -f "$BACKEND_DIR/migrations/017_add_short_url_to_sites.sql"
echo -e "${GREEN}✓${NC} Migration completed"
echo ""

echo -e "${BLUE}Step 3: Verify migration${NC}"
echo "-----------------------"

# Check if column exists
COLUMN_EXISTS=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_name = 'generated_sites' 
      AND column_name = 'short_url';
" | tr -d ' ')

if [ "$COLUMN_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✓${NC} Column 'short_url' added"
else
    echo -e "${RED}ERROR: Column 'short_url' not found${NC}"
    exit 1
fi

# Check if index exists
INDEX_EXISTS=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) 
    FROM pg_indexes 
    WHERE indexname = 'idx_generated_sites_short_url';
" | tr -d ' ')

if [ "$INDEX_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✓${NC} Index created"
else
    echo -e "${RED}ERROR: Index not found${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Step 4: Check backfill status${NC}"
echo "------------------------------"

STATS=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT 
        COUNT(*) as total,
        COUNT(short_url) as with_url,
        COUNT(*) - COUNT(short_url) as without_url
    FROM generated_sites
    WHERE status = 'completed';
" | tr -s ' ')

echo "Completed sites status:"
echo "$STATS"

WITHOUT_URL=$(echo "$STATS" | awk '{print $3}')

if [ "$WITHOUT_URL" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC}  Found $WITHOUT_URL sites without short links"
    echo ""
    echo -e "${BLUE}Step 5: Running backfill script${NC}"
    echo "-------------------------------"
    
    cd "$BACKEND_DIR"
    source .venv/bin/activate
    python scripts/backfill_site_short_urls.py
    
    echo -e "${GREEN}✓${NC} Backfill completed"
else
    echo -e "${GREEN}✓${NC} All sites have short links!"
fi

echo ""
echo -e "${BLUE}Step 6: Restart services${NC}"
echo "------------------------"

supervisorctl restart all
sleep 3

ALL_RUNNING=$(supervisorctl status | grep -c RUNNING || echo "0")

if [ "$ALL_RUNNING" -ge 3 ]; then
    echo -e "${GREEN}✓${NC} All services restarted successfully"
else
    echo -e "${RED}ERROR: One or more services failed to start${NC}"
    supervisorctl status
    echo "Check logs: supervisorctl tail -100 webmagic-api stderr"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Migration: ✓ short_url column added"
echo "  - Backfill: ✓ Existing sites updated"
echo "  - Services: ✓ API restarted"
echo ""
echo "What changed:"
echo "  - Short links now created at site generation (not preview)"
echo "  - No more race conditions on rapid variant switching"
echo "  - Campaign preview is now instant (read-only)"
echo "  - 100% URL consistency across all variants"
echo ""
echo "Test it:"
echo "  1. Generate a new AI website"
echo "  2. Go to Campaigns → Ready for Outreach"
echo "  3. Rapidly switch between variants"
echo "  4. All variants should show THE SAME short URL"
echo ""
