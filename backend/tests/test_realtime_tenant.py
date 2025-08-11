#!/usr/bin/env python3
"""
Test script to verify real-time record updates with proper tenant context
Run this while viewing the record list in the browser to see real-time updates
"""

import time
import json
from datetime import datetime
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model, schema_context
from pipelines.models import Pipeline, Record

User = get_user_model()
Tenant = get_tenant_model()

def test_realtime_updates_with_tenant():
    """Test real-time record updates with proper tenant context"""
    
    print("🚀 Testing Real-Time Record Updates with Tenant Context")
    print("=" * 60)
    
    try:
        # Get the Oneo Talent tenant (the one we're using in frontend)
        tenant = Tenant.objects.get(schema_name='oneotalent')
        print(f"🏢 Using Tenant: {tenant.name} (schema: {tenant.schema_name})")
        print(f"🌐 Tenant Domain: {tenant.get_primary_domain()}")
        
        # Switch to tenant schema context
        with schema_context(tenant.schema_name):
            print(f"✅ Switched to schema: {tenant.schema_name}")
            
            # Get the first pipeline
            pipeline = Pipeline.objects.first()
            if not pipeline:
                print("❌ No pipelines found in tenant schema. Create a pipeline first.")
                return
                
            print(f"📋 Using Pipeline: {pipeline.name} (ID: {pipeline.id})")
            
            # Get a test user
            user = User.objects.first()
            if not user:
                print("❌ No users found in tenant schema. Create a user first.")
                return
                
            print(f"👤 Using User: {user.username}")
            
            # Get existing records count
            initial_count = Record.objects.filter(pipeline=pipeline, is_deleted=False).count()
            print(f"📊 Current record count: {initial_count}")
            
            print("\n🔄 Test 1: Creating a new record...")
            print("👀 Watch the browser at oneotalent.localhost:3000 - you should see a new record appear!")
            
            # Create a new record
            new_record = Record.objects.create(
                pipeline=pipeline,
                data={
                    'test_field': f'Real-time test record created at {datetime.now().strftime("%H:%M:%S")}',
                    'created_by_test': True,
                    'timestamp': time.time(),
                    'tenant': tenant.schema_name
                },
                created_by=user,
                updated_by=user
            )
            
            print(f"✅ Created Record ID: {new_record.id}")
            print(f"📦 Record Data: {json.dumps(new_record.data, indent=2)}")
            
            # Wait a moment for WebSocket propagation
            print("⏱️  Waiting 3 seconds for WebSocket message...")
            time.sleep(3)
            
            print("\n🔄 Test 2: Updating the record...")
            print("👀 Watch the browser - you should see the record update in real-time!")
            
            # Update the record
            new_record.data.update({
                'test_field': f'Updated at {datetime.now().strftime("%H:%M:%S")}',
                'update_count': new_record.data.get('update_count', 0) + 1,
                'last_update': time.time(),
                'status': 'updated'
            })
            new_record.save()
            
            print(f"✅ Updated Record ID: {new_record.id}")
            print(f"📦 Updated Data: {json.dumps(new_record.data, indent=2)}")
            
            # Wait for WebSocket propagation
            print("⏱️  Waiting 3 seconds for WebSocket message...")
            time.sleep(3)
            
            print("\n🔄 Test 3: Soft deleting the record...")
            print("👀 Watch the browser - you should see the record disappear!")
            
            # Soft delete the record
            new_record.is_deleted = True
            new_record.save()
            
            print(f"✅ Soft deleted Record ID: {new_record.id}")
            
            # Final count
            final_count = Record.objects.filter(pipeline=pipeline, is_deleted=False).count()
            print(f"📊 Final record count: {final_count}")
            
            print("\n" + "=" * 60)
            print("🎉 Tenant-aware real-time update tests completed!")
            print(f"\nTenant Context: {tenant.name} ({tenant.schema_name})")
            print("Frontend URL: http://oneotalent.localhost:3000/pipelines/1")
            print("\nCheck your browser console for WebSocket messages:")
            print("- Look for '📨 Record list received realtime message:'")
            print("- Look for '✅ Added new record to list:'")
            print("- Look for '✅ Updated record in list:'") 
            print("- Look for '✅ Removed record from list:'")
            print("\nAlso check the record list UI for:")
            print("- 🟢 Live status indicator (should show 'Live')")
            print("- Real-time record count updates")
            print("- Records appearing/updating/disappearing without page refresh")
            print("\nWebSocket channel being tested:")
            print(f"- Channel: pipeline_records_{pipeline.id}")
            print(f"- Backend signals should broadcast to this channel")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_realtime_updates_with_tenant()