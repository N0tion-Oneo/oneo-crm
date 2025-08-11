#!/usr/bin/env python
"""
Deep investigation of user context corruption in the real API pipeline
This simulates the exact API calls the frontend makes to identify where user context gets corrupted
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
from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from core.models import AuditLog
from django.urls import reverse
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class RealAPIUserContextTest:
    """Test user context through the actual API pipeline"""
    
    def __init__(self):
        self.client = Client()
        self.investigation_log = []
        
    def log_context(self, point, user_context, additional_info=None):
        """Log user context at each point"""
        log_entry = {
            'timestamp': time.time(),
            'point': point,
            'thread_id': threading.get_ident(),
            'user_context': user_context,
            'additional_info': additional_info or {}
        }
        self.investigation_log.append(log_entry)
        
        if user_context:
            print(f"🔍 {point}: User {user_context.get('id')} ({user_context.get('email')}) - Thread {threading.get_ident()}")
        else:
            print(f"🔍 {point}: No user context - Thread {threading.get_ident()}")
            
        if additional_info:
            for key, value in additional_info.items():
                print(f"    {key}: {value}")
    
    def setup_test_environment(self):
        """Setup real API test environment"""
        print("🔧 Setting up real API test environment...")
        
        with schema_context('oneotalent'):
            # Get real users
            users = list(User.objects.filter(is_active=True).order_by('id'))
            if len(users) < 2:
                print("❌ Need at least 2 users")
                return False
                
            self.josh = users[0]  # josh@oneodigital.com 
            self.saul = users[2] if len(users) > 2 else users[1]  # saul@oneodigital.com
            
            print(f"👤 Josh: {self.josh.email} (ID: {self.josh.id})")
            print(f"👤 Saul: {self.saul.email} (ID: {self.saul.id})")
            
            # Get test data
            pipeline = Pipeline.objects.filter(is_active=True).first()
            if not pipeline:
                print("❌ No pipelines found")
                return False
                
            record = Record.objects.filter(pipeline=pipeline, is_deleted=False).first()
            if not record:
                # Try any record for any pipeline
                record = Record.objects.filter(is_deleted=False).first()
                if record:
                    pipeline = record.pipeline
                else:
                    print("❌ No records found")
                    return False
                
            self.pipeline = pipeline
            self.record = record
            
            print(f"📋 Pipeline: {pipeline.name} (ID: {pipeline.id})")
            print(f"📝 Record: {record.id}")
            
        return True
    
    def create_user_token(self, user):
        """Create JWT token for user"""
        with schema_context('oneotalent'):
            refresh = RefreshToken.for_user(user)
            refresh['tenant_schema'] = 'oneotalent'
            refresh['email'] = user.email
            token = str(refresh.access_token)
            
            self.log_context(
                "JWT_TOKEN_CREATED",
                {'id': user.id, 'email': user.email},
                {'token_preview': token[:20] + '...'}
            )
            
            return token
    
    def test_real_api_update(self, user, new_value):
        """Test a real API update using Django's test client"""
        print(f"\n🧪 REAL API UPDATE TEST: {user.email}")
        print("=" * 70)
        
        # Clear existing audit logs to see new ones clearly
        with schema_context('oneotalent'):
            AuditLog.objects.filter(model_name='Record', object_id=str(self.record.id)).delete()
            print("🧹 Cleared existing audit logs")
        
        # Step 1: Create JWT token
        token = self.create_user_token(user)
        
        # Step 2: Prepare API request data
        update_data = {
            'data': {
                'test_field': new_value
            }
        }
        
        self.log_context(
            "API_REQUEST_PREPARED",
            {'id': user.id, 'email': user.email},
            {
                'endpoint': f'/api/v1/pipelines/{self.pipeline.id}/records/{self.record.id}/',
                'method': 'PATCH',
                'field_update': f'test_field -> {new_value}',
                'host_header': 'oneotalent.localhost'
            }
        )
        
        # Step 3: Make the actual API call (this is what frontend does)
        response = self.client.patch(
            f'/api/v1/pipelines/{self.pipeline.id}/records/{self.record.id}/',
            data=json.dumps(update_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_HOST='oneotalent.localhost'
        )
        
        self.log_context(
            "API_RESPONSE_RECEIVED",
            {'id': user.id, 'email': user.email},
            {
                'status_code': response.status_code,
                'response_preview': str(response.content[:200]) if hasattr(response, 'content') else 'No content'
            }
        )
        
        # Step 4: Check what happened in the database
        time.sleep(0.2)  # Allow for signal processing
        
        with schema_context('oneotalent'):
            # Check record update
            updated_record = Record.objects.get(id=self.record.id)
            
            self.log_context(
                "RECORD_STATE_AFTER_UPDATE",
                {
                    'id': updated_record.updated_by.id if updated_record.updated_by else None,
                    'email': updated_record.updated_by.email if updated_record.updated_by else None
                },
                {
                    'record_id': updated_record.id,
                    'expected_user': user.email,
                    'updated_by_match': updated_record.updated_by.email == user.email if updated_record.updated_by else False,
                    'test_field_value': updated_record.data.get('test_field', 'Not set')
                }
            )
            
            # Check audit log creation
            audit_logs = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(self.record.id)
            ).order_by('-timestamp')
            
            if audit_logs.exists():
                latest_audit = audit_logs.first()
                
                self.log_context(
                    "AUDIT_LOG_CREATED",
                    {
                        'id': latest_audit.user.id if latest_audit.user else None,
                        'email': latest_audit.user.email if latest_audit.user else None
                    },
                    {
                        'audit_id': latest_audit.id,
                        'expected_user': user.email,
                        'audit_user_match': latest_audit.user.email == user.email if latest_audit.user else False,
                        'action': latest_audit.action,
                        'changes_count': len(latest_audit.changes) if latest_audit.changes else 0
                    }
                )
                
                return {
                    'api_success': response.status_code == 200,
                    'record_user_correct': updated_record.updated_by.email == user.email if updated_record.updated_by else False,
                    'audit_user_correct': latest_audit.user.email == user.email if latest_audit.user else False,
                    'audit_log_created': True
                }
            else:
                self.log_context(
                    "NO_AUDIT_LOG_CREATED",
                    {'id': user.id, 'email': user.email},
                    {'expected_user': user.email}
                )
                
                return {
                    'api_success': response.status_code == 200,
                    'record_user_correct': updated_record.updated_by.email == user.email if updated_record.updated_by else False,
                    'audit_user_correct': False,
                    'audit_log_created': False
                }
    
    def test_activity_api_call(self, requesting_user):
        """Test the activity API call that the frontend uses"""
        print(f"\n🔍 ACTIVITY API TEST: {requesting_user.email}")
        print("=" * 50)
        
        # Create token for the requesting user
        token = self.create_user_token(requesting_user)
        
        # Make the activity API call (what frontend does for activity tab)
        response = self.client.get(
            f'/api/v1/pipelines/{self.pipeline.id}/records/{self.record.id}/history/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_HOST='oneotalent.localhost'
        )
        
        self.log_context(
            "ACTIVITY_API_CALL",
            {'id': requesting_user.id, 'email': requesting_user.email},
            {
                'status_code': response.status_code,
                'requesting_user': requesting_user.email
            }
        )
        
        if response.status_code == 200:
            try:
                activity_data = response.json()
                activities = activity_data.get('activities', [])
                
                self.log_context(
                    "ACTIVITY_API_RESPONSE",
                    {'id': requesting_user.id, 'email': requesting_user.email},
                    {
                        'activity_count': len(activities),
                        'requesting_user': requesting_user.email
                    }
                )
                
                # Analyze each activity
                for i, activity in enumerate(activities[:3]):  # Check first 3
                    activity_user = activity.get('user', {})
                    
                    self.log_context(
                        f"ACTIVITY_{i+1}_ANALYSIS",
                        {
                            'id': None,  # Activity doesn't have direct ID
                            'email': activity_user.get('email')
                        },
                        {
                            'activity_type': activity.get('type'),
                            'activity_user': activity_user.get('email'),
                            'requesting_user': requesting_user.email,
                            'message_preview': activity.get('message', '')[:50]
                        }
                    )
                
                return activities
                
            except Exception as e:
                self.log_context(
                    "ACTIVITY_API_ERROR",
                    {'id': requesting_user.id, 'email': requesting_user.email},
                    {'error': str(e)}
                )
                
        return []
    
    def test_concurrent_different_users(self):
        """Test concurrent updates by different users"""
        print(f"\n⚡ CONCURRENT DIFFERENT USERS TEST")
        print("=" * 70)
        
        results = {}
        
        def concurrent_api_update(user, test_id):
            result = self.test_real_api_update(
                user, 
                f'concurrent_{user.id}_{test_id}_{int(time.time())}'
            )
            results[f'{user.email}_{test_id}'] = result
        
        # Create threads for concurrent API calls
        threads = []
        for i in range(3):  # 3 rounds of concurrent calls
            # Josh update
            josh_thread = threading.Thread(
                target=concurrent_api_update,
                args=(self.josh, f'josh_{i}')
            )
            
            # Saul update
            saul_thread = threading.Thread(
                target=concurrent_api_update,
                args=(self.saul, f'saul_{i}')
            )
            
            threads.extend([josh_thread, saul_thread])
        
        print(f"🚀 Starting {len(threads)} concurrent API updates...")
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        return results
    
    def analyze_investigation_results(self):
        """Analyze all logged investigation points"""
        print(f"\n📊 INVESTIGATION ANALYSIS")
        print("=" * 70)
        
        # Group by user email to see consistency
        user_contexts = {}
        
        for log_entry in self.investigation_log:
            user_context = log_entry['user_context']
            if user_context and user_context.get('email'):
                email = user_context['email']
                if email not in user_contexts:
                    user_contexts[email] = []
                user_contexts[email].append(log_entry)
        
        # Analyze user context consistency
        for user_email, entries in user_contexts.items():
            print(f"\n👤 USER CONTEXT FLOW: {user_email}")
            print("-" * 50)
            
            context_issues = []
            expected_user_id = None
            
            for entry in entries:
                point = entry['point']
                user_context = entry['user_context']
                thread_id = entry['thread_id']
                
                if expected_user_id is None and user_context.get('id'):
                    expected_user_id = user_context['id']
                
                # Check for user ID consistency
                if user_context.get('id') and user_context['id'] != expected_user_id:
                    context_issues.append({
                        'point': point,
                        'expected_id': expected_user_id,
                        'actual_id': user_context['id'],
                        'thread': thread_id
                    })
                
                consistency = "✅" if user_context.get('id') == expected_user_id else "❌"
                print(f"  {consistency} {point}: ID {user_context.get('id')} - Thread {thread_id}")
            
            if context_issues:
                print(f"\n⚠️  USER CONTEXT CORRUPTION DETECTED FOR {user_email}:")
                for issue in context_issues:
                    print(f"    {issue['point']}: Expected ID {issue['expected_id']}, got {issue['actual_id']} (Thread {issue['thread']})")
            else:
                print(f"✅ No user context corruption detected for {user_email}")
        
        # Look for cross-user contamination
        print(f"\n🔍 CROSS-USER CONTAMINATION ANALYSIS:")
        
        thread_users = {}
        for entry in self.investigation_log:
            thread_id = entry['thread_id']
            user_context = entry['user_context']
            
            if user_context and user_context.get('email'):
                if thread_id not in thread_users:
                    thread_users[thread_id] = set()
                thread_users[thread_id].add(user_context['email'])
        
        contaminated_threads = {tid: users for tid, users in thread_users.items() if len(users) > 1}
        
        if contaminated_threads:
            print("⚠️  CROSS-USER CONTAMINATION DETECTED:")
            for thread_id, users in contaminated_threads.items():
                print(f"    Thread {thread_id}: {', '.join(users)}")
        else:
            print("✅ No cross-user contamination detected")
        
        return {
            'user_contexts': user_contexts,
            'context_issues': sum(len(entries) for entries in user_contexts.values()),
            'contaminated_threads': contaminated_threads
        }

def main():
    """Run the comprehensive real API user context test"""
    print("🔍 REAL API USER CONTEXT INVESTIGATION")
    print("=" * 80)
    print("Testing user context through the actual API pipeline that the frontend uses")
    print()
    
    test = RealAPIUserContextTest()
    
    # Setup environment
    if not test.setup_test_environment():
        print("❌ Failed to setup test environment")
        return
    
    # Test 1: Sequential API updates
    print("\n📋 SEQUENTIAL API UPDATES")
    josh_result = test.test_real_api_update(test.josh, f'josh_sequential_{int(time.time())}')
    saul_result = test.test_real_api_update(test.saul, f'saul_sequential_{int(time.time())}')
    
    # Test 2: Activity API calls
    print("\n📋 ACTIVITY API CALLS")
    josh_activities = test.test_activity_api_call(test.josh)
    saul_activities = test.test_activity_api_call(test.saul)
    
    # Test 3: Concurrent API updates
    concurrent_results = test.test_concurrent_different_users()
    
    # Analyze all results
    analysis = test.analyze_investigation_results()
    
    # Final summary
    print(f"\n" + "=" * 80)
    print("🏁 REAL API INVESTIGATION SUMMARY")
    print("=" * 80)
    
    sequential_success = josh_result.get('record_user_correct', False) and saul_result.get('record_user_correct', False)
    audit_success = josh_result.get('audit_user_correct', False) and saul_result.get('audit_user_correct', False)
    
    concurrent_success_rate = 0
    if concurrent_results:
        correct_results = sum(1 for result in concurrent_results.values() if result.get('record_user_correct', False))
        concurrent_success_rate = correct_results / len(concurrent_results)
    
    print(f"📊 Sequential record updates: {'✅ PASSED' if sequential_success else '❌ FAILED'}")
    print(f"📊 Sequential audit logs: {'✅ PASSED' if audit_success else '❌ FAILED'}")
    print(f"📊 Concurrent success rate: {concurrent_success_rate:.1%}")
    print(f"📊 Investigation points: {len(test.investigation_log)}")
    print(f"📊 Cross-user contamination: {len(analysis['contaminated_threads'])} threads")
    
    if sequential_success and audit_success and concurrent_success_rate > 0.8 and len(analysis['contaminated_threads']) == 0:
        print(f"\n🎉 REAL API USER CONTEXT: WORKING CORRECTLY")
        print("✅ User attribution is accurate through the entire API pipeline")
    else:
        print(f"\n⚠️  REAL API USER CONTEXT: ISSUES DETECTED")
        print("🐛 User context corruption confirmed in the API pipeline")
        
        if not sequential_success:
            print("   • Sequential record user attribution failed")
        if not audit_success:
            print("   • Sequential audit log user attribution failed")
        if concurrent_success_rate <= 0.8:
            print(f"   • Concurrent user attribution failed ({concurrent_success_rate:.1%} success)")
        if len(analysis['contaminated_threads']) > 0:
            print("   • Cross-user thread contamination detected")

if __name__ == '__main__':
    main()