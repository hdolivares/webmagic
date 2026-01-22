#!/bin/bash
#
# Start All WebMagic Services
# 
# This script starts all WebMagic backend services in the correct order
# with health checks to ensure each service is fully operational before
# starting dependent services.
#
# Usage: ./scripts/start_services.sh
#

set -e

echo "🚀 Starting WebMagic Services..."
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Error: This script must be run as root or with sudo${NC}"
    echo "   Usage: sudo ./scripts/start_services.sh"
    exit 1
fi

# Function to start a service and wait for it to be healthy
start_service() {
    local service_name=$1
    local wait_time=${2:-10}  # Default 10 seconds wait
    
    echo -n "Starting ${service_name}... "
    
    # Start the service
    supervisorctl start "$service_name" > /dev/null 2>&1
    
    # Wait for service to become RUNNING
    for i in $(seq 1 $wait_time); do
        if supervisorctl status "$service_name" | grep -q "RUNNING"; then
            echo -e "${GREEN}✓ Running${NC}"
            return 0
        fi
        sleep 1
    done
    
    # Check if it failed
    if supervisorctl status "$service_name" | grep -q "FATAL\|BACKOFF"; then
        echo -e "${RED}✗ Failed to start${NC}"
        echo ""
        echo -e "${YELLOW}Checking error logs...${NC}"
        supervisorctl tail "$service_name" stderr | tail -20
        return 1
    fi
    
    echo -e "${YELLOW}⚠ Timeout waiting for service${NC}"
    return 1
}

# Health check for API
check_api_health() {
    echo -n "Checking API health... "
    
    for i in {1..30}; do
        if curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
            echo -e "${GREEN}✓ API responding${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${YELLOW}⚠ API may not be fully ready${NC}"
    return 1
}

# Start services in dependency order
# 1. API - core service
# 2. Celery Worker - depends on API/Redis
# 3. Celery Beat - depends on worker

echo "1️⃣  Starting FastAPI (web server)..."
start_service "webmagic-api" 15
sleep 2
check_api_health
echo ""

echo "2️⃣  Starting Celery Worker (async tasks)..."
start_service "webmagic-celery" 15
sleep 2
echo ""

echo "3️⃣  Starting Celery Beat (task scheduler)..."
start_service "webmagic-celery-beat" 10
echo ""

# Final status check
echo "=================================="
echo "📊 Final Status:"
echo "=================================="
supervisorctl status | grep webmagic

echo ""
echo -e "${GREEN}✅ All WebMagic services started successfully!${NC}"
echo ""
echo -e "${BLUE}🌐 Access points:${NC}"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Admin UI: https://web.lavish.solutions"
echo "   - Customer Portal: https://web.lavish.solutions/customer/domains"
echo ""
echo -e "${YELLOW}💡 Tip: Check logs with:${NC}"
echo "   tail -f /var/log/webmagic/api.log"
echo "   tail -f /var/log/webmagic/celery.log"

