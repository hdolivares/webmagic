#!/bin/bash
#
# Stop All WebMagic Services
# 
# This script gracefully stops all WebMagic backend services in the correct order
# to ensure no data loss or service interruption.
#
# Usage: ./scripts/stop_services.sh
#

set -e

echo "🛑 Stopping WebMagic Services..."
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Error: This script must be run as root or with sudo${NC}"
    echo "   Usage: sudo ./scripts/stop_services.sh"
    exit 1
fi

# Function to stop a service safely
stop_service() {
    local service_name=$1
    echo -n "Stopping ${service_name}... "
    
    if supervisorctl status "$service_name" | grep -q "RUNNING"; then
        supervisorctl stop "$service_name" > /dev/null 2>&1
        
        # Wait up to 10 seconds for graceful shutdown
        for i in {1..10}; do
            if ! supervisorctl status "$service_name" | grep -q "RUNNING"; then
                echo -e "${GREEN}✓ Stopped${NC}"
                return 0
            fi
            sleep 1
        done
        
        echo -e "${YELLOW}⚠ Timeout (may still be stopping)${NC}"
        return 1
    else
        echo -e "${YELLOW}⚠ Not running${NC}"
        return 0
    fi
}

# Stop services in reverse dependency order
# 1. Celery Beat (scheduler) - depends on worker
# 2. Celery Worker - depends on API/Redis
# 3. API - depends on database

echo "1️⃣  Stopping Celery Beat (task scheduler)..."
stop_service "webmagic-celery-beat"
echo ""

echo "2️⃣  Stopping Celery Worker (async tasks)..."
stop_service "webmagic-celery"
echo ""

echo "3️⃣  Stopping FastAPI (web server)..."
stop_service "webmagic-api"
echo ""

# Final status check
echo "=================================="
echo "📊 Final Status:"
echo "=================================="
supervisorctl status | grep webmagic

echo ""
echo -e "${GREEN}✅ All WebMagic services stopped successfully!${NC}"
echo ""
echo "Note: Redis and PostgreSQL are not managed by this script."
echo "      They are system services and should remain running."

