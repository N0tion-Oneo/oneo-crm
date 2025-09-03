#!/bin/bash

# Oneo CRM Backend Startup Script
# This script starts the Django backend server with all necessary setup

set -e  # Exit on any error

echo "🚀 Starting Oneo CRM Backend..."

# Change to backend directory
cd "$(dirname "$0")/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if required services are running
echo "🔍 Checking required services..."

# Check PostgreSQL
if ! pg_isready -q; then
    echo "⚠️  PostgreSQL is not running. Starting PostgreSQL..."
    brew services start postgresql@14 || {
        echo "❌ Failed to start PostgreSQL. Please ensure it's installed: brew install postgresql@14"
        exit 1
    }
    sleep 2
fi

# Check Redis
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis is not running. Starting Redis..."
    brew services start redis || {
        echo "❌ Failed to start Redis. Please ensure it's installed: brew install redis"
        exit 1
    }
    sleep 2
fi

# Verify WebSocket dependencies
echo "🔌 Verifying WebSocket configuration..."
python -c "
import pkg_resources
try:
    pkg_resources.get_distribution('daphne')
    pkg_resources.get_distribution('channels')
    pkg_resources.get_distribution('channels-redis')
    print('✅ WebSocket dependencies installed (daphne, channels, channels-redis)')
except pkg_resources.DistributionNotFound as e:
    print(f'❌ Missing WebSocket dependency: {e}')
    exit(1)
"

# Kill any existing Django server on port 8000
echo "🧹 Cleaning up any existing Django processes..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true

# Run migrations  
echo "🗄️  Running database migrations..."
python manage.py migrate_schemas --shared --verbosity=1
echo "🏢 Running tenant migrations (this may take a moment)..."
python manage.py migrate_schemas --tenant --verbosity=1

# Collect static files (if needed)
if [ "$1" = "--production" ]; then
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput
fi

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down backend services..."
    
    # Kill Django server
    echo "🧹 Stopping Django server..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    
    # Kill Celery workers
    echo "🧹 Stopping Celery workers..."
    pkill -f "celery.*worker" 2>/dev/null || true
    
    echo "✅ Backend services stopped."
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start Celery workers in background
echo "🤖 Starting Celery workers..."

# AI Processing worker
echo "  • Starting AI processing worker..."
celery -A oneo_crm worker -n ai_worker@%h --loglevel=info --queues=ai_processing --concurrency=1 --pool=solo &
CELERY_AI_PID=$!

# Workflows worker (handles workflow execution and management)
echo "  • Starting workflows worker..."
celery -A oneo_crm worker -n workflows_worker@%h --loglevel=info --queues=workflows --concurrency=1 --pool=solo &
CELERY_WORKFLOWS_PID=$!

# Communications Maintenance worker (handles communication cleanup and maintenance)
echo "  • Starting communications maintenance worker..."
celery -A oneo_crm worker -n comm_maint_worker@%h --loglevel=info --queues=communications_maintenance --concurrency=1 --pool=solo &
CELERY_COMM_MAINT_PID=$!

# Background sync worker (handles record-level communication sync)
echo "  • Starting background sync worker (record communications)..."
celery -A oneo_crm worker -n sync_worker@%h --loglevel=info --queues=background_sync --concurrency=1 --pool=solo &
CELERY_SYNC_PID=$!

# Analytics worker (handles statistics and analytics tasks)
echo "  • Starting analytics worker (communication statistics)..."
celery -A oneo_crm worker -n analytics_worker@%h --loglevel=info --queues=analytics --concurrency=1 --pool=solo &
CELERY_ANALYTICS_PID=$!

# Give Celery workers a moment to start
echo "  • Waiting for workers to initialize..."
sleep 3

# Verify workers are running
echo "🔍 Verifying Celery workers..."
if ps -p $CELERY_AI_PID > /dev/null; then
    echo "  ✅ AI processing worker started (PID: $CELERY_AI_PID)"
else
    echo "  ❌ AI processing worker failed to start"
fi

if ps -p $CELERY_WORKFLOWS_PID > /dev/null; then
    echo "  ✅ Workflows worker started (PID: $CELERY_WORKFLOWS_PID) - handles workflow execution"
else
    echo "  ❌ Workflows worker failed to start"
fi

if ps -p $CELERY_COMM_MAINT_PID > /dev/null; then
    echo "  ✅ Communications maintenance worker started (PID: $CELERY_COMM_MAINT_PID)"
else
    echo "  ❌ Communications maintenance worker failed to start"
fi

if ps -p $CELERY_SYNC_PID > /dev/null; then
    echo "  ✅ Background sync worker started (PID: $CELERY_SYNC_PID) - handles record communications"
else
    echo "  ❌ Background sync worker failed to start"
fi

if ps -p $CELERY_ANALYTICS_PID > /dev/null; then
    echo "  ✅ Analytics worker started (PID: $CELERY_ANALYTICS_PID) - handles communication analytics"
else
    echo "  ❌ Analytics worker failed to start"
fi

# Start the Django development server with ASGI support
echo "🌟 Starting Django ASGI server (daphne) with WebSocket support..."
echo "📡 Backend will be available at:"
echo "   • Main: http://localhost:8000"
echo "   • Demo tenant: http://demo.localhost:8000"
echo "   • Test tenant: http://testorg.localhost:8000"
echo "   • API docs: http://localhost:8000/api/docs/"
echo ""
echo "🔌 WebSocket endpoints:"
echo "   • Real-time: ws://localhost:8000/ws/realtime/"
echo "   • Collaboration: ws://localhost:8000/ws/collaborate/"
echo "   • Workflows: ws://localhost:8000/ws/workflows/"
echo ""
echo "🤖 Background services:"
echo "   ✅ Django ASGI server (WebSocket + HTTP)"
echo "   ✅ Celery AI worker (AI processing)"
echo "   ✅ Celery workflows worker (workflow execution and management)"
echo "   ✅ Celery communications maintenance worker (cleanup and maintenance)"
echo "   ✅ Celery sync worker (background sync + record-level communications)"
echo "   ✅ Celery analytics worker (statistics + hot conversations)"
echo ""
echo "📋 Useful commands:"
echo "   • View Celery logs: celery -A oneo_crm events"
echo "   • Monitor Celery: celery -A oneo_crm inspect active"
echo "   • Stop everything: Press Ctrl+C"
echo ""
echo "✨ Backend ready with real-time messaging and AI processing! Press Ctrl+C to stop."
echo ""

python manage.py runserver 0.0.0.0:8000