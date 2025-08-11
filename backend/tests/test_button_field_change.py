#!/usr/bin/env python3

import os
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from pipelines.models import Record, Pipeline
from django.contrib.auth import get_user_model
User = get_user_model()
from tenants.models import Tenant

# Enable debug logging
logging.basicConfig(level=logging.INFO)

def test_button_field_change():
    """Test button field change detection"""
    
    print("🧪 TESTING: Button Field Change Detection")
    print("=" * 60)
    
    try:
        # Switch to oneotalent tenant
        tenant = Tenant.objects.get(schema_name='oneotalent')
        print(f"✅ Found tenant: {tenant.name}")
        
        with schema_context(tenant.schema_name):
            # Get the sales pipeline
            try:
                pipeline = Pipeline.objects.get(name='Sales Pipeline')
                print(f"✅ Found pipeline: {pipeline.name}")
            except Pipeline.DoesNotExist:
                print("❌ Sales Pipeline not found")
                return
            
            # Get a test record
            record = Record.objects.filter(pipeline=pipeline).first()
            if not record:
                print("❌ No records found in Sales Pipeline")
                return
            
            print(f"✅ Found test record: {record.id}")
            print(f"   📊 Current data: {record.data}")
            
            # Get a user for the operation
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                print("❌ No superuser found")
                return
            
            print(f"✅ Found user: {user.email}")
            
            # Find the button field in the record data
            button_field_slug = None
            for field_slug, field_data in record.data.items():
                if isinstance(field_data, dict) and field_data.get('type') == 'button':
                    button_field_slug = field_slug
                    break
            
            if not button_field_slug:
                print("❌ No button field found in record data")
                print(f"   📊 Available fields: {list(record.data.keys())}")
                return
            
            print(f"✅ Found button field: '{button_field_slug}'")
            print(f"   📊 Current value: {record.data[button_field_slug]}")
            
            # Store original data for comparison
            original_data = record.data.copy()
            
            # Modify the button field (simulate button click)
            button_data = record.data[button_field_slug].copy()
            button_data['triggered'] = not button_data.get('triggered', False)
            button_data['last_triggered'] = '2025-08-09T15:50:00Z'
            
            record.data[button_field_slug] = button_data
            
            print(f"🔄 SIMULATING BUTTON CLICK:")
            print(f"   📜 Original: {original_data[button_field_slug]}")
            print(f"   📄 Modified: {record.data[button_field_slug]}")
            
            # Set user context for AI processing
            record._current_user = user
            
            print(f"\n🔍 CHANGE DETECTION TEST:")
            print(f"   👤 User set: {record._current_user}")
            print(f"   📊 Has _skip_ai_processing: {getattr(record, '_skip_ai_processing', False)}")
            
            # Test the change detection method directly
            changed_fields = record._get_changed_fields(original_data, record.data)
            print(f"   🔄 Changed fields result: {changed_fields}")
            
            # Now save the record to trigger the full pipeline
            print(f"\n💾 SAVING RECORD...")
            record.save()
            print(f"✅ Record saved successfully")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_button_field_change()