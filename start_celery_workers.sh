#!/bin/bash
#
# Start dedicated Celery workers for WebMagic
#
# Usage: ./start_celery_workers.sh
#

set -e

BACKEND_DIR="/var/www/webmagic/backend"
PYTHONPATH="$BACKEND_DIR"

echo "========================================="
echo "Starting WebMagic Celery Workers"
echo "========================================="

# Stop existing workers
echo "Stopping existing workers..."
pkill -9 -f "celery.*worker" 2>/dev/null || true
pkill -9 -f "celery.*beat" 2>/dev/null || true
sleep 2

# Start Beat scheduler
echo "Starting Beat scheduler..."
cd "$BACKEND_DIR"
PYTHONPATH="$PYTHONPATH" nohup .venv/bin/celery -A celery_app beat \
    --loglevel=info \
    > /tmp/celery_beat.log 2>&1 &

echo "Beat scheduler started (PID: $!)"
sleep 2

# Start Generation Worker (dedicated, high priority)
echo "Starting Generation worker (dedicated)..."
PYTHONPATH="$PYTHONPATH" nohup .venv/bin/celery -A celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    -Q generation \
    -n generation_worker@%h \
    > /tmp/celery_generation.log 2>&1 &

echo "Generation worker started (PID: $!)"

# Start General Worker (for other tasks)
echo "Starting General worker (campaigns, monitoring, scraping)..."
PYTHONPATH="$PYTHONPATH" nohup .venv/bin/celery -A celery_app worker \
    --loglevel=info \
    --concurrency=1 \
    -Q celery,campaigns,monitoring,scraping \
    -n general_worker@%h \
    > /tmp/celery_general.log 2>&1 &

echo "General worker started (PID: $!)"

sleep 3

# Check status
echo ""
echo "========================================="
echo "Worker Status:"
echo "========================================="
ps aux | grep celery | grep -v grep | awk '{print $2, $11, $12, $13, $14, $15}'

echo ""
echo "========================================="
echo "Celery workers started successfully!"
echo "========================================="
echo ""
echo "Logs:"
echo "  Beat:       tail -f /tmp/celery_beat.log"
echo "  Generation: tail -f /tmp/celery_generation.log"
echo "  General:    tail -f /tmp/celery_general.log"
echo ""
echo "Monitor:"
echo "  Active:     celery -A celery_app inspect active"
echo "  Registered: celery -A celery_app inspect registered"
echo ""


