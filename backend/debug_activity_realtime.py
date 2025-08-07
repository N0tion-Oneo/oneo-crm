#!/usr/bin/env python3
"""
Debug script to test if activity tab real-time updates are working
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record
from django.contrib.auth import get_user_model

User = get_user_model()

def test_record_save_and_broadcast():
    """Test if saving a record triggers the audit log and WebSocket broadcast"""
    print("🔍 Testing Record Save → AuditLog → WebSocket Broadcasting")
    
    with schema_context('oneotalent'):
        # Get a record to test with
        test_record = Record.objects.first()
        if not test_record:
            print("❌ No test record found")
            return
            
        print(f"Testing with record ID: {test_record.id}")
        print(f"Record title: {test_record.title}")
        print(f"Pipeline: {test_record.pipeline.name}")
        
        # Store original data
        original_data = test_record.data.copy() if test_record.data else {}
        print(f"Original data keys: {list(original_data.keys())}")
        
        # Make a small change to trigger audit logging
        test_field = None
        if test_record.data:
            # Find a field we can modify
            for field_name, value in test_record.data.items():
                if isinstance(value, str) and value:
                    test_field = field_name
                    break
        
        if not test_field:
            # Add a test field
            test_field = 'debug_test_field'
            test_record.data = test_record.data or {}
            test_record.data[test_field] = 'Original Value'
        
        print(f"Will modify field: {test_field}")
        
        # Make the change
        import time
        test_record.data[test_field] = f'Updated Value {int(time.time())}'
        
        print("💾 Saving record to trigger signals...")
        
        # Save and see what happens
        try:
            test_record.save()
            print("✅ Record saved successfully")
            
            # Check if audit log was created
            from core.models import AuditLog
            latest_audit = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(test_record.id)
            ).order_by('-timestamp').first()
            
            if latest_audit:
                print(f"✅ AuditLog created: ID {latest_audit.id}")
                print(f"   Timestamp: {latest_audit.timestamp}")
                print(f"   Changes: {list(latest_audit.changes.keys())}")
            else:
                print("❌ No AuditLog found for this record")
                
        except Exception as e:
            print(f"❌ Error saving record: {e}")

if __name__ == "__main__":
    test_record_save_and_broadcast()