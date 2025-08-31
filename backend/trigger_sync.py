#!/usr/bin/env python
"""
Script to trigger a fresh communication sync
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.record_communications.tasks import sync_record_communications
from pipelines.models import Record

def trigger_sync():
    """Trigger a fresh sync for record 66"""
    
    print("🔄 Starting fresh communication sync...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Get record 66
        record = Record.objects.get(id=66)
        print(f"   📋 Found record: {record.data.get('full_name', 'Unknown')}")
        
        # Trigger sync using the task directly
        print("   🚀 Triggering sync...")
        try:
            # Call the task synchronously for immediate execution
            result = sync_record_communications(
                record_id=66,
                tenant_schema=tenant.schema_name,
                trigger_reason='Manual sync for HTML email fix'
            )
            print(f"   ✅ Sync completed: {result}")
        except Exception as e:
            print(f"   ❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n✨ Sync process completed!")
        print("   Check the frontend to see if HTML emails are now displaying properly.")

if __name__ == "__main__":
    trigger_sync()
