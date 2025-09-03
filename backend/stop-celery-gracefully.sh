#!/bin/bash
# Gracefully stop Celery workers

echo "🛑 Stopping Celery workers gracefully..."

# Send SIGTERM to allow workers to finish current tasks
pkill -TERM -f 'celery.*worker'

echo "⏳ Waiting for workers to finish current tasks (max 30 seconds)..."
timeout=30
elapsed=0

while pgrep -f 'celery.*worker' > /dev/null && [ $elapsed -lt $timeout ]; do
    sleep 1
    elapsed=$((elapsed + 1))
    echo -n "."
done

echo ""

if pgrep -f 'celery.*worker' > /dev/null; then
    echo "⚠️  Some workers still running after ${timeout}s, forcing shutdown..."
    pkill -KILL -f 'celery.*worker'
else
    echo "✅ All Celery workers stopped gracefully"
fi

# Also stop Celery beat if running
if pgrep -f 'celery.*beat' > /dev/null; then
    echo "🛑 Stopping Celery beat..."
    pkill -TERM -f 'celery.*beat'
fi

echo "✅ Celery shutdown complete"