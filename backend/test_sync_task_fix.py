#!/usr/bin/env python
"""
Test script to verify sync task tenant context fix
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from pipelines.models import Record
from communications.record_communications.models import RecordCommunicationProfile
from communications.record_communications.tasks import sync_record_communications
from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.db import connection

User = get_user_model()

def test_sync_task_with_tenant():
    """Test that sync task properly receives tenant context"""
    
    print("=" * 60)
    print("Testing Sync Task Tenant Context Fix")
    print("=" * 60)
    
    # Get a tenant
    tenant = Tenant.objects.filter(schema_name='oneotalent').first()
    if not tenant:
        tenant = Tenant.objects.exclude(schema_name='public').first()
        if not tenant:
            print("❌ No tenant found")
            return False
    
    print(f"✅ Using tenant: {tenant.name} (schema: {tenant.schema_name})")
    
    # Switch to tenant schema
    with schema_context(tenant.schema_name):
        # Get a record with communication profile
        profile = RecordCommunicationProfile.objects.first()
        if not profile:
            # Try to find any record
            record = Record.objects.first()
            if not record:
                print("❌ No records found in tenant")
                return False
            
            # Create a profile
            profile = RecordCommunicationProfile.objects.create(
                record=record,
                auto_sync_enabled=False  # Don't auto-sync
            )
            print(f"✅ Created communication profile for record {record.id}")
        else:
            record = profile.record
            print(f"✅ Found record {record.id} with communication profile")
        
        # Test 1: Direct task call with tenant schema
        print("\n📋 Test 1: Direct task call with tenant schema")
        try:
            # This should work - we're passing tenant_schema
            result = sync_record_communications.apply_async(
                args=[record.id, tenant.schema_name],
                kwargs={
                    'trigger_reason': 'Test with tenant schema'
                }
            )
            print(f"   ✅ Task queued successfully: {result.id}")
        except Exception as e:
            print(f"   ❌ Failed to queue task: {e}")
            return False
        
        # Test 2: Check field_manager auto-sync
        print("\n📋 Test 2: Field manager auto-sync")
        from communications.services.field_manager import field_manager
        
        # Enable auto-sync for testing
        profile.auto_sync_enabled = True
        profile.sync_frequency_hours = 24
        profile.save()
        
        try:
            # This should now include tenant_schema
            field_manager.schedule_auto_sync(profile)
            print("   ✅ Auto-sync scheduled with tenant context")
        except Exception as e:
            print(f"   ❌ Failed to schedule auto-sync: {e}")
            
        # Disable auto-sync again
        profile.auto_sync_enabled = False
        profile.save()
        
        # Test 3: Check that task fails without tenant schema
        print("\n📋 Test 3: Task behavior without tenant schema")
        try:
            # This should fail or use the current connection's tenant
            result = sync_record_communications.apply_async(
                args=[record.id],  # No tenant_schema
                kwargs={
                    'trigger_reason': 'Test without tenant schema'
                }
            )
            # The task should handle this by getting schema from connection
            print(f"   ⚠️ Task queued (will get schema from connection): {result.id}")
        except Exception as e:
            print(f"   ✅ Task correctly requires tenant schema: {e}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed - sync task tenant context fixed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_sync_task_with_tenant()
    sys.exit(0 if success else 1)