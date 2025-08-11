#!/usr/bin/env python
"""
Focused test of just the audit logging signal to identify user attribution issues
"""

import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import json
import time
import threading
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from pipelines.models import Record
from core.models import AuditLog
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

def test_audit_signal_user_attribution():
    """Test the audit signal user attribution directly"""
    print("🔍 AUDIT SIGNAL USER ATTRIBUTION TEST")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Get test users
        users = list(User.objects.filter(is_active=True).order_by('id'))
        if len(users) < 2:
            print("❌ Need at least 2 users")
            return
            
        josh = users[0]  # josh@oneodigital.com
        saul = users[2] if len(users) > 2 else users[1]  # saul@oneodigital.com
        
        print(f"👤 Josh: {josh.email} (ID: {josh.id})")
        print(f"👤 Saul: {saul.email} (ID: {saul.id})")
        
        # Get a test record
        record = Record.objects.filter(is_deleted=False).first()
        if not record:
            print("❌ No records found")
            return
            
        print(f"📝 Using record: {record.id}")
        
        # Clear any existing audit logs for this record to start fresh
        AuditLog.objects.filter(model_name='Record', object_id=str(record.id)).delete()
        print("🧹 Cleared existing audit logs")
        
        # Test 1: Update as Josh
        print(f"\n🧪 Test 1: Update as Josh")
        original_data = record.data.copy()
        record._original_data = original_data
        record.data = record.data.copy()
        record.data['test_field'] = f'josh_value_{int(time.time())}'
        record.updated_by = josh  # Critical: Set the user
        
        print(f"💾 Saving record with updated_by = {record.updated_by.email} (ID: {record.updated_by.id})")
        
        # Disable other signals temporarily to isolate the audit signal
        from django.db.models.signals import pre_save
        from duplicates.signals import check_duplicates_on_record_save
        
        # Temporarily disconnect the duplicate signal that's causing issues
        pre_save.disconnect(check_duplicates_on_record_save, sender=Record)
        
        try:
            record.save()
            time.sleep(0.1)  # Allow signal processing
            
            # Check audit log
            josh_audit = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(record.id),
                action='updated'
            ).order_by('-timestamp').first()
            
            if josh_audit:
                print(f"📝 Audit log created:")
                print(f"   ID: {josh_audit.id}")
                print(f"   User: {josh_audit.user.email if josh_audit.user else 'None'} (ID: {josh_audit.user.id if josh_audit.user else 'None'})")
                print(f"   Expected: {josh.email} (ID: {josh.id})")
                print(f"   Match: {'✅ YES' if josh_audit.user and josh_audit.user.id == josh.id else '❌ NO'}")
                
                josh_match = josh_audit.user and josh_audit.user.id == josh.id
            else:
                print("❌ No audit log created for Josh")
                josh_match = False
                
        finally:
            # Reconnect the signal
            pre_save.connect(check_duplicates_on_record_save, sender=Record)
        
        # Test 2: Update as Saul
        print(f"\n🧪 Test 2: Update as Saul")
        original_data = record.data.copy()
        record._original_data = original_data
        record.data = record.data.copy()
        record.data['test_field'] = f'saul_value_{int(time.time())}'
        record.updated_by = saul  # Critical: Set to different user
        
        print(f"💾 Saving record with updated_by = {record.updated_by.email} (ID: {record.updated_by.id})")
        
        # Disable problematic signal again
        pre_save.disconnect(check_duplicates_on_record_save, sender=Record)
        
        try:
            record.save()
            time.sleep(0.1)  # Allow signal processing
            
            # Check audit log
            saul_audit = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(record.id),
                action='updated'
            ).order_by('-timestamp').first()
            
            if saul_audit:
                print(f"📝 Audit log created:")
                print(f"   ID: {saul_audit.id}")
                print(f"   User: {saul_audit.user.email if saul_audit.user else 'None'} (ID: {saul_audit.user.id if saul_audit.user else 'None'})")
                print(f"   Expected: {saul.email} (ID: {saul.id})")
                print(f"   Match: {'✅ YES' if saul_audit.user and saul_audit.user.id == saul.id else '❌ NO'}")
                
                saul_match = saul_audit.user and saul_audit.user.id == saul.id
            else:
                print("❌ No audit log created for Saul")
                saul_match = False
                
        finally:
            # Reconnect the signal
            pre_save.connect(check_duplicates_on_record_save, sender=Record)
        
        # Test 3: Concurrent updates
        print(f"\n⚡ Test 3: Concurrent updates")
        
        results = {}
        
        def concurrent_update(test_user, test_id):
            with schema_context('oneotalent'):
                # Get a fresh record instance
                test_record = Record.objects.get(id=record.id)
                
                # Update as specific user
                original_data = test_record.data.copy()
                test_record._original_data = original_data
                test_record.data = test_record.data.copy()
                test_record.data['test_field'] = f'{test_user.email}_concurrent_{test_id}_{int(time.time())}'
                test_record.updated_by = test_user
                
                print(f"🧵 Thread {threading.get_ident()}: Saving as {test_user.email}")
                
                # Disable problematic signal
                pre_save.disconnect(check_duplicates_on_record_save, sender=Record)
                
                try:
                    test_record.save()
                    time.sleep(0.1)
                    
                    # Check the audit log
                    latest_audit = AuditLog.objects.filter(
                        model_name='Record',
                        object_id=str(test_record.id),
                        action='updated'
                    ).order_by('-timestamp').first()
                    
                    if latest_audit and latest_audit.user:
                        audit_user_email = latest_audit.user.email
                        expected_email = test_user.email
                        match = audit_user_email == expected_email
                        
                        results[test_id] = {
                            'expected': expected_email,
                            'actual': audit_user_email,
                            'match': match,
                            'audit_id': latest_audit.id
                        }
                        
                        print(f"🧵 Thread {threading.get_ident()}: Audit user = {audit_user_email}, Expected = {expected_email}, Match = {match}")
                    else:
                        results[test_id] = {
                            'expected': test_user.email,
                            'actual': 'None',
                            'match': False,
                            'audit_id': None
                        }
                        
                finally:
                    # Reconnect signal
                    pre_save.connect(check_duplicates_on_record_save, sender=Record)
        
        # Run concurrent updates
        threads = []
        for i in range(5):
            # Alternate between Josh and Saul
            test_user = josh if i % 2 == 0 else saul
            thread = threading.Thread(target=concurrent_update, args=(test_user, f"concurrent_{i}"))
            threads.append(thread)
        
        print(f"🚀 Starting {len(threads)} concurrent updates...")
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Analyze concurrent results
        print(f"\n📊 Concurrent test results:")
        matches = 0
        total = len(results)
        
        for test_id, result in results.items():
            status = "✅" if result['match'] else "❌"
            print(f"   {status} {test_id}: Expected {result['expected']}, Got {result['actual']}")
            if result['match']:
                matches += 1
        
        print(f"\n🏁 FINAL RESULTS:")
        print(f"   📊 Sequential Josh: {'✅ PASS' if josh_match else '❌ FAIL'}")
        print(f"   📊 Sequential Saul: {'✅ PASS' if saul_match else '❌ FAIL'}")
        print(f"   📊 Concurrent: {matches}/{total} ({matches/total*100:.1f}%) correct")
        
        if josh_match and saul_match and matches/total > 0.8:
            print(f"\n🎉 AUDIT SIGNAL WORKING CORRECTLY")
            print("✅ User attribution in audit logs is accurate")
        else:
            print(f"\n⚠️  AUDIT SIGNAL ISSUES DETECTED")
            if not josh_match:
                print("❌ Sequential Josh test failed")
            if not saul_match:
                print("❌ Sequential Saul test failed") 
            if matches/total <= 0.8:
                print(f"❌ Concurrent test failed ({matches/total*100:.1f}% success)")
            
            # Show recent audit logs for debugging
            print(f"\n🔍 Recent audit logs for debugging:")
            recent_audits = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(record.id)
            ).order_by('-timestamp')[:10]
            
            for audit in recent_audits:
                print(f"   📝 ID {audit.id}: {audit.user.email if audit.user else 'None'} at {audit.timestamp}")

if __name__ == '__main__':
    test_audit_signal_user_attribution()