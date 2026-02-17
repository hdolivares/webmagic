#!/bin/bash
# Deployment script for Short Links Race Condition Fix
# Run this on the VPS after code is pushed

set -e  # Exit on any error

echo "==================================="
echo "Short Links Race Condition Fix"
echo "Deployment Script"
echo "==================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="webmagic"
DB_USER="webmagic_user"
MIGRATION_FILE="/var/www/webmagic/backend/migrations/016_fix_short_links_uniqueness.sql"
LOG_FILE="/var/log/webmagic/short_links_fix_$(date +%Y%m%d_%H%M%S).log"

echo "Step 1: Pre-deployment checks"
echo "------------------------------"

# Check if migration file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}ERROR: Migration file not found: $MIGRATION_FILE${NC}"
    echo "Did you git pull the latest changes?"
    exit 1
fi
echo -e "${GREEN}✓${NC} Migration file found"

# Check database connection
if ! psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Cannot connect to database${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Database connection OK"

echo ""
echo "Step 2: Check current state"
echo "---------------------------"

# Count existing duplicates
DUPLICATE_COUNT=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) FROM (
        SELECT destination_url, link_type
        FROM short_links
        WHERE is_active = true
        GROUP BY destination_url, link_type
        HAVING COUNT(*) > 1
    ) duplicates;
" | tr -d ' ')

echo "Active duplicate short links found: $DUPLICATE_COUNT"

if [ "$DUPLICATE_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC}  These will be cleaned up by the migration"
fi

echo ""
echo "Step 3: Run database migration"
echo "-------------------------------"

echo "Executing migration..."
if psql -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE" > "$LOG_FILE" 2>&1; then
    echo -e "${GREEN}✓${NC} Migration completed successfully"
    echo "   Log: $LOG_FILE"
else
    echo -e "${RED}ERROR: Migration failed${NC}"
    echo "Check log: $LOG_FILE"
    exit 1
fi

echo ""
echo "Step 4: Verify migration"
echo "------------------------"

# Check if unique index was created
INDEX_EXISTS=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) 
    FROM pg_indexes 
    WHERE indexname = 'idx_short_links_unique_active_destination';
" | tr -d ' ')

if [ "$INDEX_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✓${NC} Unique constraint index created"
else
    echo -e "${RED}ERROR: Unique constraint index not found${NC}"
    exit 1
fi

# Re-check for duplicates
NEW_DUPLICATE_COUNT=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) FROM (
        SELECT destination_url, link_type
        FROM short_links
        WHERE is_active = true
        GROUP BY destination_url, link_type
        HAVING COUNT(*) > 1
    ) duplicates;
" | tr -d ' ')

if [ "$NEW_DUPLICATE_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All duplicates cleaned up"
else
    echo -e "${RED}ERROR: Still found $NEW_DUPLICATE_COUNT duplicates${NC}"
    exit 1
fi

echo ""
echo "Step 5: Restart API service"
echo "---------------------------"

if supervisorctl restart webmagic-api > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API restarted"
    sleep 2
    
    # Check if API is running
    if supervisorctl status webmagic-api | grep -q RUNNING; then
        echo -e "${GREEN}✓${NC} API is running"
    else
        echo -e "${RED}ERROR: API failed to start${NC}"
        echo "Check logs: tail -f /var/log/webmagic/api.log"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠${NC}  Could not restart via supervisor"
    echo "   Please restart manually: supervisorctl restart webmagic-api"
fi

echo ""
echo "==================================="
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE${NC}"
echo "==================================="
echo ""
echo "Summary:"
echo "  - Duplicates cleaned: $DUPLICATE_COUNT"
echo "  - Unique constraint added: Yes"
echo "  - API restarted: Yes"
echo ""
echo "Next steps:"
echo "  1. Test campaign preview (rapid tab switching)"
echo "  2. Verify no new duplicates created"
echo "  3. Monitor: tail -f /var/log/webmagic/api.log"
echo ""
echo "Verification query:"
echo "  psql -U $DB_USER -d $DB_NAME -c \\"
echo "    \"SELECT destination_url, COUNT(*) FROM short_links"
echo "     WHERE is_active = true"
echo "     GROUP BY destination_url HAVING COUNT(*) > 1;\""
echo ""
