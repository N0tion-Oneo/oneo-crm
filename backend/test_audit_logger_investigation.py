#!/usr/bin/env python
"""
Deep investigation of the audit logging system for user attribution issues
This focuses specifically on how audit logs are created and what user context they capture
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
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class AuditLoggerInvestigation:
    """Deep investigation of audit logging user attribution"""
    
    def __init__(self):
        self.investigation_results = []
        self.signal_captures = []
        
    def log_investigation(self, point, user_id, user_email, context=None):
        """Log investigation points"""
        result = {
            'timestamp': time.time(),
            'point': point,
            'user_id': user_id,
            'user_email': user_email,
            'thread_id': threading.get_ident(),
            'context': context or {}
        }
        self.investigation_results.append(result)
        print(f"🔍 {point}: User {user_id} ({user_email}) - Thread {threading.get_ident()}")
        if context:
            for key, value in context.items():
                print(f"    {key}: {value}")
    
    def setup_signal_monitoring(self):
        """Set up signal monitoring to capture what happens during record updates"""
        
        @receiver(post_save, sender=Record)
        def monitor_record_save_signal(sender, instance, created, **kwargs):
            """Monitor the record save signal to see user attribution"""
            if not created:  # Only monitor updates
                signal_info = {
                    'timestamp': time.time(),
                    'record_id': instance.id,
                    'instance_updated_by_id': instance.updated_by.id if instance.updated_by else None,
                    'instance_updated_by_email': instance.updated_by.email if instance.updated_by else None,
                    'thread_id': threading.get_ident(),
                    'has_original_data': hasattr(instance, '_original_data'),
                    'original_data_keys': list(instance._original_data.keys()) if hasattr(instance, '_original_data') else None,
                    'current_data_keys': list(instance.data.keys()) if instance.data else None
                }
                
                self.signal_captures.append(signal_info)
                print(f"📡 SIGNAL CAPTURED: Record {instance.id} updated by {signal_info['instance_updated_by_email']} (ID: {signal_info['instance_updated_by_id']})")
                
                # Check what the signal handler is about to do
                if hasattr(instance, '_original_data') and instance._original_data != instance.data:
                    print(f"    📋 Signal will create audit log with user: {instance.updated_by.email if instance.updated_by else 'None'}")
        
        print("✅ Signal monitoring activated")
    
    def test_direct_record_update_with_user(self, user, field_name, new_value):
        """Test direct record update to see user attribution in audit logs"""
        print(f"\n🧪 DIRECT RECORD UPDATE TEST: {user.email}")
        print("-" * 60)
        
        with schema_context('oneotalent'):
            # Get a test record
            record = Record.objects.filter(is_deleted=False).first()
            if not record:
                print("❌ No record found")
                return False
                
            self.log_investigation(
                "RECORD_UPDATE_START",
                user.id,
                user.email,
                {
                    'record_id': record.id,
                    'field_to_update': field_name,
                    'new_value': new_value
                }
            )
            
            # Count audit logs before
            audit_count_before = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(record.id)
            ).count()
            
            self.log_investigation(
                "AUDIT_COUNT_BEFORE",
                user.id,
                user.email,
                {'count': audit_count_before}
            )
            
            # Prepare the record update exactly like the serializer would
            original_data = record.data.copy()
            record._original_data = original_data  # This is what the signal uses
            
            # Update the record data
            record.data = record.data.copy()  # Ensure we have a new dict
            record.data[field_name] = new_value
            record.updated_by = user  # This is the critical assignment
            
            self.log_investigation(
                "RECORD_PREPARED_FOR_SAVE",
                user.id,
                user.email,
                {
                    'record_updated_by_id': record.updated_by.id,
                    'record_updated_by_email': record.updated_by.email,
                    'original_value': original_data.get(field_name),
                    'new_value': record.data.get(field_name)
                }
            )
            
            # Save the record (this triggers the signal)
            print(f"💾 Saving record with updated_by = {record.updated_by.email}")
            record.save()
            
            self.log_investigation(
                "RECORD_SAVED",
                record.updated_by.id if record.updated_by else None,
                record.updated_by.email if record.updated_by else None,
                {'record_id': record.id}
            )
            
            # Small delay for signal processing
            time.sleep(0.1)
            
            # Check audit logs after
            audit_count_after = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(record.id)
            ).count()
            
            new_audits = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(record.id)
            ).order_by('-timestamp')[:audit_count_after - audit_count_before]
            
            self.log_investigation(
                "AUDIT_COUNT_AFTER",
                user.id,
                user.email,
                {'count': audit_count_after, 'new_audits': audit_count_after - audit_count_before}
            )
            
            # Examine the new audit logs
            for i, audit_log in enumerate(new_audits):
                self.log_investigation(
                    f"AUDIT_LOG_{i+1}_CREATED",
                    audit_log.user.id if audit_log.user else None,
                    audit_log.user.email if audit_log.user else None,
                    {
                        'audit_log_id': audit_log.id,
                        'action': audit_log.action,
                        'expected_user': user.id,
                        'user_match': audit_log.user.id == user.id if audit_log.user else False,
                        'changes_keys': list(audit_log.changes.keys()) if audit_log.changes else None
                    }
                )
                
                # Check if the user in the audit log matches expected
                if audit_log.user and audit_log.user.id == user.id:
                    print(f"    ✅ Audit log user matches expected: {user.email}")
                    return True
                else:
                    print(f"    ❌ AUDIT LOG USER MISMATCH:")
                    print(f"        Expected: {user.email} (ID: {user.id})")
                    print(f"        Actual: {audit_log.user.email if audit_log.user else 'None'} (ID: {audit_log.user.id if audit_log.user else 'None'})")
                    return False
                    
        return False
    
    def test_concurrent_record_updates(self):
        """Test concurrent record updates to see if there's user context bleeding"""
        print("\n⚡ CONCURRENT AUDIT LOGGING TEST")
        print("=" * 60)
        
        with schema_context('oneotalent'):
            users = list(User.objects.filter(is_active=True).order_by('id'))[:3]
            
            if len(users) < 3:
                print("❌ Need at least 3 users")
                return False
                
            print(f"👥 Testing with {len(users)} users:")
            for user in users:
                print(f"   👤 {user.email} (ID: {user.id})")
        
        # Sequential baseline
        print(f"\n📋 Sequential baseline testing:")
        sequential_results = {}
        for i, user in enumerate(users):
            result = self.test_direct_record_update_with_user(
                user, 
                'test_field', 
                f'sequential_{user.id}_{int(time.time())}'
            )
            sequential_results[user.email] = result
        
        # Concurrent testing
        print(f"\n⚡ Concurrent testing:")
        concurrent_results = {}
        
        def concurrent_update_test(user, results_dict):
            result = self.test_direct_record_update_with_user(
                user,
                'test_field',
                f'concurrent_{user.id}_{int(time.time())}_{threading.get_ident()}'
            )
            results_dict[user.email] = result
        
        # Run 3 rounds of concurrent updates
        for round_num in range(3):
            print(f"\n🔄 Concurrent round {round_num + 1}:")
            
            round_results = {}
            threads = []
            
            for user in users:
                thread = threading.Thread(
                    target=concurrent_update_test,
                    args=(user, round_results)
                )
                threads.append(thread)
            
            # Start all threads simultaneously
            for thread in threads:
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Merge results
            for email, result in round_results.items():
                if email not in concurrent_results:
                    concurrent_results[email] = []
                concurrent_results[email].append(result)
        
        return {
            'sequential': sequential_results,
            'concurrent': concurrent_results
        }
    
    def analyze_signal_captures(self):
        """Analyze captured signal data"""
        print(f"\n📡 SIGNAL CAPTURE ANALYSIS")
        print("=" * 60)
        
        print(f"📊 Captured {len(self.signal_captures)} signal events")
        
        # Group by thread to see if there's thread contamination
        thread_users = {}
        for capture in self.signal_captures:
            thread_id = capture['thread_id']
            user_email = capture['instance_updated_by_email']
            
            if thread_id not in thread_users:
                thread_users[thread_id] = set()
            thread_users[thread_id].add(user_email)
        
        # Check for thread contamination
        contaminated_threads = {tid: users for tid, users in thread_users.items() if len(users) > 1}
        
        if contaminated_threads:
            print("⚠️  THREAD CONTAMINATION IN SIGNALS:")
            for thread_id, users in contaminated_threads.items():
                print(f"   Thread {thread_id}: {', '.join(users)}")
        else:
            print("✅ No thread contamination in signals")
        
        # Check for user consistency within signals
        user_consistency = {}
        for capture in self.signal_captures:
            record_id = capture['record_id']
            user_email = capture['instance_updated_by_email']
            
            if record_id not in user_consistency:
                user_consistency[record_id] = set()
            user_consistency[record_id].add(user_email)
        
        inconsistent_records = {rid: users for rid, users in user_consistency.items() if len(users) > 1}
        
        if inconsistent_records:
            print("⚠️  USER INCONSISTENCY IN RECORD UPDATES:")
            for record_id, users in inconsistent_records.items():
                print(f"   Record {record_id}: {', '.join(users)}")
        else:
            print("✅ User consistency maintained across record updates")
        
        return {
            'thread_contamination': contaminated_threads,
            'user_inconsistency': inconsistent_records
        }
    
    def final_audit_log_verification(self):
        """Final verification of recent audit logs"""
        print(f"\n🔍 FINAL AUDIT LOG VERIFICATION")
        print("=" * 60)
        
        with schema_context('oneotalent'):
            # Get recent audit logs
            recent_audits = AuditLog.objects.filter(
                model_name='Record',
                action='updated'
            ).order_by('-timestamp')[:10]
            
            print(f"📊 Recent {len(recent_audits)} audit log entries:")
            
            user_attribution = {}
            for audit in recent_audits:
                user_email = audit.user.email if audit.user else 'None'
                if user_email not in user_attribution:
                    user_attribution[user_email] = 0
                user_attribution[user_email] += 1
                
                print(f"   📝 ID {audit.id}: Record {audit.object_id} by {user_email} at {audit.timestamp}")
            
            print(f"\n📈 User attribution distribution:")
            for user_email, count in user_attribution.items():
                print(f"   👤 {user_email}: {count} audit logs")
            
            # Check if one user dominates (indicating potential issue)
            total_audits = sum(user_attribution.values())
            dominant_user = max(user_attribution.items(), key=lambda x: x[1]) if user_attribution else (None, 0)
            
            if dominant_user[1] > total_audits * 0.8:  # If one user has >80% of audit logs
                print(f"⚠️  POTENTIAL ISSUE: {dominant_user[0]} dominates with {dominant_user[1]}/{total_audits} ({dominant_user[1]/total_audits:.1%}) of audit logs")
                return False
            else:
                print(f"✅ Reasonable distribution of audit logs across users")
                return True

def main():
    """Run the audit logger investigation"""
    print("🔍 AUDIT LOGGER INVESTIGATION")
    print("=" * 80)
    print("Deep dive into audit logging user attribution issues")
    print()
    
    investigation = AuditLoggerInvestigation()
    
    # Set up signal monitoring
    investigation.setup_signal_monitoring()
    
    # Run concurrent audit logging tests
    results = investigation.test_concurrent_record_updates()
    
    # Analyze signal captures
    signal_analysis = investigation.analyze_signal_captures()
    
    # Final verification
    final_verification = investigation.final_audit_log_verification()
    
    # Summary
    print(f"\n" + "=" * 80)
    print("🏁 AUDIT LOGGER INVESTIGATION SUMMARY")
    print("=" * 80)
    
    sequential_success = all(results['sequential'].values())
    concurrent_success_rates = []
    for user_results in results['concurrent'].values():
        if user_results:
            success_rate = sum(user_results) / len(user_results)
            concurrent_success_rates.append(success_rate)
    
    avg_concurrent_success = sum(concurrent_success_rates) / len(concurrent_success_rates) if concurrent_success_rates else 0
    
    print(f"📊 Sequential audit logging: {'✅ PASSED' if sequential_success else '❌ FAILED'}")
    print(f"📊 Concurrent audit logging: {avg_concurrent_success:.1%} success rate")
    print(f"📊 Thread contamination: {len(signal_analysis['thread_contamination'])} threads")
    print(f"📊 User inconsistency: {len(signal_analysis['user_inconsistency'])} records")
    print(f"📊 Final verification: {'✅ PASSED' if final_verification else '❌ FAILED'}")
    
    if (sequential_success and avg_concurrent_success > 0.9 and 
        len(signal_analysis['thread_contamination']) == 0 and
        len(signal_analysis['user_inconsistency']) == 0 and
        final_verification):
        print(f"\n🎉 AUDIT LOGGER WORKING CORRECTLY")
        print("✅ No user attribution issues detected in audit logging system")
        print("📋 The user attribution issue is likely elsewhere:")
        print("   • Frontend activity display logic")
        print("   • WebSocket real-time updates")
        print("   • API response caching")
    else:
        print(f"\n⚠️  AUDIT LOGGER ISSUES DETECTED")
        print("🐛 User attribution problems confirmed in audit logging system")
        print("🔧 Issues found in:")
        
        if not sequential_success:
            print("   • Sequential audit log creation")
        if avg_concurrent_success <= 0.9:
            print("   • Concurrent audit log user attribution")
        if signal_analysis['thread_contamination']:
            print("   • Thread-level user context isolation")
        if signal_analysis['user_inconsistency']:
            print("   • Cross-record user consistency")
        if not final_verification:
            print("   • Overall audit log user distribution")

if __name__ == '__main__':
    main()