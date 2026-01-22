#!/bin/bash
#
# Restart All WebMagic Services
# 
# This script safely restarts all WebMagic backend services by:
# 1. Gracefully stopping all services in reverse dependency order
# 2. Waiting to ensure clean shutdown
# 3. Starting services in correct dependency order with health checks
#
# Usage: ./scripts/restart_services.sh
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}♻️  Restarting WebMagic Services${NC}"
echo "=================================="
echo ""

# Stop services
bash "$SCRIPT_DIR/stop_services.sh"

echo ""
echo "⏳ Waiting 3 seconds for clean shutdown..."
sleep 3
echo ""

# Start services
bash "$SCRIPT_DIR/start_services.sh"

echo ""
echo -e "${GREEN}✅ Restart complete!${NC}"

