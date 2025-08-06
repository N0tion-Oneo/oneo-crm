#!/usr/bin/env python3
"""
Test script to verify real-time record updates are working
Run this while viewing the record list in the browser to see real-time updates
"""

import os
import sys
import django
import time
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.append('backend')
django.setup()

from pipelines.models import Pipeline, Record
from django.contrib.auth import get_user_model

User = get_user_model()

def test_realtime_updates():
    """Test real-time record updates"""
    
    print("🚀 Testing Real-Time Record Updates")
    print("=" * 50)
    
    try:
        # Get the first pipeline
        pipeline = Pipeline.objects.first()
        if not pipeline:
            print("❌ No pipelines found. Create a pipeline first.")
            return
            
        print(f"📋 Using Pipeline: {pipeline.name} (ID: {pipeline.id})")
        
        # Get a test user
        user = User.objects.first()
        if not user:
            print("❌ No users found. Create a user first.")
            return
            
        print(f"👤 Using User: {user.username}")
        
        # Get existing records count
        initial_count = Record.objects.filter(pipeline=pipeline, is_deleted=False).count()
        print(f"📊 Current record count: {initial_count}")
        
        print("\n🔄 Test 1: Creating a new record...")
        print("👀 Watch the browser - you should see a new record appear!")
        
        # Create a new record
        new_record = Record.objects.create(
            pipeline=pipeline,
            data={
                'test_field': f'Real-time test record created at {datetime.now().strftime("%H:%M:%S")}',
                'created_by_test': True,
                'timestamp': time.time()
            },
            created_by=user,
            updated_by=user
        )
        
        print(f"✅ Created Record ID: {new_record.id}")
        print(f"📦 Record Data: {json.dumps(new_record.data, indent=2)}")
        
        # Wait a moment
        time.sleep(2)
        
        print("\n🔄 Test 2: Updating the record...")
        print("👀 Watch the browser - you should see the record update!")
        
        # Update the record
        new_record.data.update({
            'test_field': f'Updated at {datetime.now().strftime("%H:%M:%S")}',
            'update_count': new_record.data.get('update_count', 0) + 1,
            'last_update': time.time()
        })
        new_record.save()
        
        print(f"✅ Updated Record ID: {new_record.id}")
        print(f"📦 Updated Data: {json.dumps(new_record.data, indent=2)}")
        
        # Wait a moment
        time.sleep(2)
        
        print("\n🔄 Test 3: Soft deleting the record...")
        print("👀 Watch the browser - you should see the record disappear!")
        
        # Soft delete the record
        new_record.is_deleted = True
        new_record.save()
        
        print(f"✅ Soft deleted Record ID: {new_record.id}")
        
        # Final count
        final_count = Record.objects.filter(pipeline=pipeline, is_deleted=False).count()
        print(f"📊 Final record count: {final_count}")
        
        print("\n" + "=" * 50)
        print("🎉 Real-time update tests completed!")
        print("\nCheck your browser console for WebSocket messages:")
        print("- Look for '📨 Record list received realtime message:'")
        print("- Look for '✅ Added new record to list:'")
        print("- Look for '✅ Updated record in list:'") 
        print("- Look for '✅ Removed record from list:'")
        print("\nAlso check the record list UI for:")
        print("- 🟢 Live status indicator")
        print("- Real-time record count updates")
        print("- Records appearing/updating/disappearing without page refresh")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_realtime_updates()