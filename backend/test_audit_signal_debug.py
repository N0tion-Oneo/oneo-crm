#!/usr/bin/env python
"""
Debug why the audit signal isn't firing when records are updated
"""

import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from pipelines.models import Record
from core.models import AuditLog
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

User = get_user_model()

def debug_audit_signal():
    """Debug why audit signal isn't firing"""
    print("🔍 AUDIT SIGNAL DEBUG")
    print("=" * 40)
    
    # Add debugging signal
    @receiver(post_save, sender=Record)
    def debug_post_save_signal(sender, instance, created, **kwargs):
        print(f"📡 POST_SAVE SIGNAL FIRED:")
        print(f"   Record ID: {instance.id}")
        print(f"   Created: {created}")
        print(f"   Has _original_data: {hasattr(instance, '_original_data')}")
        if hasattr(instance, '_original_data'):
            print(f"   Original data keys: {list(instance._original_data.keys()) if instance._original_data else 'Empty'}")
            print(f"   Current data keys: {list(instance.data.keys()) if instance.data else 'Empty'}")
            
            # Check for actual changes
            if instance._original_data != instance.data:
                print(f"   ✅ Data has changed - audit log should be created")
                changes = {}
                for key, new_value in instance.data.items():
                    old_value = instance._original_data.get(key)
                    if old_value != new_value:
                        changes[key] = {'old': old_value, 'new': new_value}
                print(f"   Changes detected: {list(changes.keys())}")
            else:
                print(f"   ❌ No data changes detected")
        else:
            print(f"   ❌ No _original_data attribute - signal condition not met")
        
        print(f"   Updated by: {instance.updated_by.email if instance.updated_by else 'None'}")
    
    # Add pre_save debugging
    @receiver(pre_save, sender=Record)
    def debug_pre_save_signal(sender, instance, **kwargs):
        print(f"📡 PRE_SAVE SIGNAL FIRED:")
        print(f"   Record ID: {instance.id}")
        if instance.pk:
            try:
                original = Record.objects.get(pk=instance.pk)
                print(f"   Original data retrieved: {len(original.data) if original.data else 0} fields")
                print(f"   Setting _original_data on instance")
                instance._original_data = original.data
            except Record.DoesNotExist:
                print(f"   ❌ Original record not found")
                instance._original_data = {}
        else:
            print(f"   New record - no original data")
            instance._original_data = {}
    
    with schema_context('oneotalent'):
        # Get test data
        user = User.objects.filter(is_active=True).first()
        record = Record.objects.filter(is_deleted=False).first()
        
        if not user or not record:
            print("❌ Missing test data")
            return
        
        print(f"👤 User: {user.email} (ID: {user.id})")
        print(f"📝 Record: {record.id}")
        
        # Clear existing audit logs
        AuditLog.objects.filter(model_name='Record', object_id=str(record.id)).delete()
        print("🧹 Cleared existing audit logs")
        
        # Test 1: Manual _original_data setting (what our test was doing)
        print(f"\n🧪 Test 1: Manual _original_data setting")
        original_data = record.data.copy()
        record._original_data = original_data
        record.data = record.data.copy()
        record.data['test_field'] = f'manual_test_{int(time.time())}'
        record.updated_by = user
        
        print(f"💾 Saving record...")
        record.save()
        
        # Check audit log creation
        audit_log = AuditLog.objects.filter(
            model_name='Record',
            object_id=str(record.id)
        ).order_by('-timestamp').first()
        
        if audit_log:
            print(f"✅ Audit log created with manual _original_data")
        else:
            print(f"❌ No audit log created with manual _original_data")
        
        # Test 2: Let pre_save signal set _original_data (proper way)
        print(f"\n🧪 Test 2: Pre_save signal sets _original_data")
        record.data = record.data.copy()
        record.data['test_field'] = f'presave_test_{int(time.time())}'
        record.updated_by = user
        
        # Don't manually set _original_data - let pre_save do it
        print(f"💾 Saving record (letting pre_save handle _original_data)...")
        record.save()
        
        # Check audit log creation
        audit_logs = AuditLog.objects.filter(
            model_name='Record',
            object_id=str(record.id)
        ).order_by('-timestamp')[:2]
        
        if len(audit_logs) > 1:
            print(f"✅ Audit log created with pre_save _original_data")
        else:
            print(f"❌ No new audit log created with pre_save _original_data")
        
        # Show all audit logs
        print(f"\n📊 All audit logs for record {record.id}:")
        for i, log in enumerate(audit_logs):
            print(f"   {i+1}. ID {log.id}: {log.user.email if log.user else 'None'} at {log.timestamp}")

if __name__ == '__main__':
    import time
    debug_audit_signal()