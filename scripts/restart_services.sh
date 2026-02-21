#!/bin/bash
#
# Restart All WebMagic Services
#
# Usage: sudo ./scripts/restart_services.sh
#

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Error: This script must be run as root or with sudo${NC}"
    echo "   Usage: sudo ./scripts/restart_services.sh"
    exit 1
fi

echo ""
echo -e "${BLUE}♻️  Restarting WebMagic Services${NC}"
echo "=================================="
echo ""

supervisorctl restart all
sleep 3

echo ""
echo "=================================="
echo "📊 Final Status:"
echo "=================================="
supervisorctl status | grep webmagic

echo ""
echo -e "${GREEN}✅ Restart complete!${NC}"
echo ""
echo -e "${YELLOW}💡 Check logs with:${NC}"
echo "   supervisorctl tail -f webmagic-api stderr"
echo "   supervisorctl tail -f webmagic-celery stderr"
echo "   supervisorctl tail -f webmagic-celery-beat stderr"
