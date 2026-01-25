#!/bin/bash
#
# Quick Fix Script for Coverage Page Errors
#
# This script:
# 1. Checks if required tables exist
# 2. Applies missing migrations
# 3. Restarts services
# 4. Verifies the fix
#
# Usage: ./quick_fix_coverage.sh
#

set -e  # Exit on error

echo "========================================"
echo "Coverage Page Quick Fix Script"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ DATABASE_URL not set${NC}"
    echo "Please set DATABASE_URL environment variable"
    echo "Example: export DATABASE_URL='postgresql://...'"
    exit 1
fi

echo -e "${GREEN}✅ DATABASE_URL is set${NC}"
echo ""

# Function to check if table exists
table_exists() {
    local table_name=$1
    psql "$DATABASE_URL" -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name='$table_name');"
}

# Check geo_strategies table
echo "Checking geo_strategies table..."
if [ "$(table_exists 'geo_strategies')" = "t" ]; then
    echo -e "${GREEN}✅ geo_strategies table exists${NC}"
else
    echo -e "${YELLOW}⚠️  geo_strategies table missing - applying migration...${NC}"
    psql "$DATABASE_URL" -f /root/webmagic/backend/migrations/004_add_geo_strategies.sql
    echo -e "${GREEN}✅ Migration 004 applied${NC}"
fi
echo ""

# Check draft_campaigns table
echo "Checking draft_campaigns table..."
if [ "$(table_exists 'draft_campaigns')" = "t" ]; then
    echo -e "${GREEN}✅ draft_campaigns table exists${NC}"
else
    echo -e "${YELLOW}⚠️  draft_campaigns table missing - applying migration...${NC}"
    psql "$DATABASE_URL" -f /root/webmagic/backend/migrations/005_add_draft_campaigns.sql
    echo -e "${GREEN}✅ Migration 005 applied${NC}"
fi
echo ""

# Restart services
echo "Restarting services..."
pm2 restart webmagic-api
echo -e "${GREEN}✅ API restarted${NC}"
echo ""

# Wait for API to start
echo "Waiting for API to start..."
sleep 3

# Test health endpoint
echo "Testing API health..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    echo "Check logs: pm2 logs webmagic-api"
    exit 1
fi
echo ""

# Run diagnostic script
echo "Running diagnostic checks..."
cd /root/webmagic/backend
python3 scripts/diagnose_coverage_errors.py
echo ""

echo "========================================"
echo -e "${GREEN}✅ Quick fix complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Clear your browser cache"
echo "2. Reload the Coverage page"
echo "3. Test creating an intelligent strategy"
echo ""
echo "If you still see errors:"
echo "  pm2 logs webmagic-api --lines 100"
echo ""

