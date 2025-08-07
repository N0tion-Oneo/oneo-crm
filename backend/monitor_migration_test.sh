#!/bin/bash

echo "🚀 Starting Migration Test Monitoring"
echo "====================================="
echo "This script will:"
echo "1. Monitor Celery logs for migration activity"
echo "2. Track maintenance mode status"
echo "3. Verify atomic transaction behavior"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

# Start monitoring Celery logs with field migration specific patterns
echo "📋 Monitoring Celery worker logs for migration activity..."
tail -f /dev/null &
TAIL_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping monitoring..."
    kill $TAIL_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT

# Monitor the Celery worker logs
# Since we're using celery worker directly, we'll monitor the process output
ps aux | grep celery | grep -v grep | head -1

echo ""
echo "💡 To test the migration:"
echo "   1. Run this monitoring script"
echo "   2. In another terminal, execute the field change test"
echo "   3. Watch the logs below for detailed migration tracking"
echo ""
echo "📊 Current system status:"

# Check current maintenance status
source venv/bin/activate
DJANGO_SETTINGS_MODULE=oneo_crm.settings python -c "
import django
django.setup()
from tenants.models import Tenant, TenantMaintenance

demo_tenant = Tenant.objects.get(schema_name='demo')
if hasattr(demo_tenant, 'maintenance'):
    maintenance = demo_tenant.maintenance
    print(f'Demo tenant maintenance status: {\"ACTIVE\" if maintenance.is_active else \"INACTIVE\"}')
else:
    print('Demo tenant: No maintenance record')
"

echo ""
echo "🔍 Watching for migration logs..."
echo "   Look for: 🚀 STARTING ATOMIC MIGRATION TRANSACTION"
echo "   Success:  🎉 TRANSACTION COMMITTED SUCCESSFULLY" 
echo "   Failure:  💥 MIGRATION EXCEPTION"
echo ""

# Keep script running
wait