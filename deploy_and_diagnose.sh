#!/bin/bash
# Comprehensive Deployment and Diagnostic Script for WebMagic

set -e

echo "=================================="
echo "🚀 WebMagic Deployment & Diagnosis"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to backend directory
cd /var/www/webmagic/backend

echo "📥 Step 1: Pulling latest code..."
git fetch origin
git reset --hard origin/main
echo "${GREEN}✅ Code updated${NC}"
echo ""

echo "🧪 Step 2: Testing imports..."
source .venv/bin/activate
if python test_imports.py; then
    echo "${GREEN}✅ All imports valid${NC}"
else
    echo "${RED}❌ Import test failed - check errors above${NC}"
    exit 1
fi
echo ""

echo "🔄 Step 3: Restarting services..."
sudo supervisorctl restart all
sleep 3
echo "${GREEN}✅ Services restarted${NC}"
echo ""

echo "📊 Step 4: Checking service status..."
sudo supervisorctl status
echo ""

echo "📝 Step 5: Checking API logs (last 30 lines)..."
echo "${YELLOW}--- API Error Log ---${NC}"
tail -n 30 /var/log/webmagic/api_error.log | grep -v "INFO" || echo "No recent errors"
echo ""

echo "🔍 Step 6: Testing API endpoint..."
sleep 2
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/docs)
if [ "$response" == "200" ]; then
    echo "${GREEN}✅ API responding correctly (HTTP $response)${NC}"
else
    echo "${RED}❌ API not responding correctly (HTTP $response)${NC}"
fi
echo ""

echo "🔍 Step 7: Testing auth endpoint..."
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/auth/unified-login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"test","password":"test"}')
if [ "$response" == "401" ] || [ "$response" == "422" ] || [ "$response" == "200" ]; then
    echo "${GREEN}✅ Auth endpoint responding (HTTP $response - expected)${NC}"
else
    echo "${RED}❌ Auth endpoint error (HTTP $response)${NC}"
fi
echo ""

echo "🌐 Step 8: Checking Nginx status..."
sudo systemctl status nginx | head -n 5
echo ""

echo "✅ Step 9: Checking Redis..."
redis-cli ping
echo ""

echo "=================================="
echo "✅ Deployment Complete!"
echo "=================================="
echo ""

