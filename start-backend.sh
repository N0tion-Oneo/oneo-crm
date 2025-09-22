#!/bin/bash

# Oneo CRM Backend Startup Script
# This script starts the Django backend server with all necessary setup

set -e  # Exit on any error

# Fix macOS fork() safety issue that causes crashes
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

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
    
    # Stop all tenant workers
    echo "🧹 Stopping all tenant workers..."
    python manage.py manage_tenant_workers stop-all 2>/dev/null || true
    
    # Also kill any remaining Celery processes (failsafe)
    pkill -f "celery.*worker" 2>/dev/null || true
    
    echo "✅ Backend services stopped."
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start tenant-specific Celery workers
echo "🤖 Starting tenant-specific Celery workers..."

# Get list of active tenants (excluding public schema)
echo "  • Detecting active tenants..."
TENANTS=$(python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
import django
django.setup()
from django_tenants.utils import get_tenant_model
Tenant = get_tenant_model()
for tenant in Tenant.objects.exclude(schema_name='public'):
    print(tenant.schema_name)
" 2>/dev/null)

if [ -z "$TENANTS" ]; then
    echo "  ⚠️  No tenants found. Workers will be started when tenants are created."
else
    # Start all worker types for each tenant
    for TENANT in $TENANTS; do
        echo "  • Starting workers for tenant: $TENANT"
        echo "    - sync worker (data synchronization)"
        echo "    - workflows worker (workflow execution)"
        echo "    - ai worker (AI processing)"
        echo "    - communications worker (messaging)"
        echo "    - analytics worker (reports & statistics)"
        echo "    - operations worker (general tasks)"
        python manage.py manage_tenant_workers start --tenant $TENANT
        sleep 2
    done
fi

# Give workers a moment to start
echo "  • Waiting for workers to initialize..."
sleep 3

# Verify workers are running
echo "🔍 Verifying tenant workers..."
python manage.py manage_tenant_workers status

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
echo "   ✅ Tenant-specific Celery workers (6 specialized workers per tenant):"
echo "      • sync - Data synchronization tasks"
echo "      • workflows - Workflow execution and triggers"
echo "      • ai - AI processing and field computation"
echo "      • communications - Messaging and notifications"
echo "      • analytics - Reports and statistics"
echo "      • operations - General tasks and maintenance"
echo "   ✅ Complete isolation between tenants"
echo "   ✅ Dynamic worker management based on active tenants"
echo ""
echo "📋 Useful commands:"
echo "   • View tenant workers: python manage.py manage_tenant_workers status"
echo "   • Start tenant worker: python manage.py manage_tenant_workers start --tenant <schema>"
echo "   • Stop tenant worker: python manage.py manage_tenant_workers stop --tenant <schema>"
echo "   • Monitor Celery: celery -A oneo_crm inspect active"
echo "   • View Celery events: celery -A oneo_crm events"
echo "   • Stop everything: Press Ctrl+C"
echo ""
echo "✨ Backend ready with real-time messaging and AI processing! Press Ctrl+C to stop."
echo ""

python manage.py runserver 0.0.0.0:8000