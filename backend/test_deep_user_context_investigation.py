#!/usr/bin/env python
"""
Deep investigation of user context persistence throughout the entire request lifecycle
This test simulates the exact frontend workflow to identify where user context might be corrupted
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
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.jwt_authentication import TenantAwareJWTAuthentication
from django_tenants.utils import schema_context, get_tenant_model
from pipelines.models import Pipeline, Record
from core.models import AuditLog
from api.views.records import RecordViewSet
from api.serializers import DynamicRecordSerializer
from channels.layers import get_channel_layer
from unittest.mock import patch, MagicMock
import logging

User = get_user_model()
Tenant = get_tenant_model()
logger = logging.getLogger(__name__)

class DeepUserContextInvestigation:
    """Comprehensive user context investigation throughout request lifecycle"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.auth_class = TenantAwareJWTAuthentication()
        self.investigation_results = []
        
    def log_investigation_point(self, point_name, user_id, user_email, additional_context=None):
        """Log user context at each investigation point"""
        result = {
            'timestamp': time.time(),
            'point': point_name,
            'user_id': user_id,
            'user_email': user_email,
            'thread_id': threading.get_ident(),
            'additional_context': additional_context or {}
        }
        self.investigation_results.append(result)
        print(f"🔍 {point_name}: User {user_id} ({user_email}) - Thread {threading.get_ident()}")
        if additional_context:
            for key, value in additional_context.items():
                print(f"    {key}: {value}")
    
    def setup_test_environment(self):
        """Setup test with real tenant and users"""
        print("🔧 Setting up deep investigation test environment...")
        
        with schema_context('oneotalent'):
            # Get real users
            users = list(User.objects.filter(is_active=True).order_by('id'))
            if len(users) < 3:
                print("❌ Need at least 3 users for comprehensive testing")
                return False
                
            self.josh = users[0]  # josh@oneodigital.com 
            self.admin = users[1]  # admin@oneo.com
            self.saul = users[2] if len(users) > 2 else users[1]  # saul@oneodigital.com
            
            print(f"👤 Josh: {self.josh.email} (ID: {self.josh.id})")
            print(f"👤 Admin: {self.admin.email} (ID: {self.admin.id})")
            print(f"👤 Saul: {self.saul.email} (ID: {self.saul.id})")
            
            # Get test record
            pipeline = Pipeline.objects.filter(is_active=True).first()
            if not pipeline:
                print("❌ No active pipelines found")
                return False
                
            record = Record.objects.filter(pipeline=pipeline, is_deleted=False).first()
            if not record:
                # Try any pipeline
                record = Record.objects.filter(is_deleted=False).first()
                if record:
                    pipeline = record.pipeline
                    
            if not record:
                print("❌ No records found for testing")
                return False
                
            self.pipeline = pipeline
            self.record = record
            
            print(f"📋 Pipeline: {pipeline.name} (ID: {pipeline.id})")
            print(f"📝 Record: {record.id}")
            
        return True
    
    def create_instrumented_jwt_token(self, user):
        """Create JWT token with logging"""
        with schema_context('oneotalent'):
            refresh = RefreshToken.for_user(user)
            refresh['tenant_schema'] = 'oneotalent'
            refresh['email'] = user.email
            token = str(refresh.access_token)
            
            self.log_investigation_point(
                "JWT_TOKEN_CREATED",
                user.id,
                user.email,
                {'token_preview': token[:20] + '...'}
            )
            
            return token
    
    def simulate_complete_record_update_flow(self, user, field_name, new_value):
        """Simulate the complete record update flow with instrumentation"""
        print(f"\n🧪 DEEP INVESTIGATION: Complete record update flow for {user.email}")
        print("=" * 80)
        
        # Step 1: Create JWT token
        token = self.create_instrumented_jwt_token(user)
        
        # Step 2: Create authenticated request (like frontend would)
        request_data = {
            'data': {field_name: new_value}
        }
        
        request = self.factory.patch(
            f'/api/pipelines/{self.pipeline.id}/records/{self.record.id}/',
            data=json.dumps(request_data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_HOST='oneotalent.localhost'
        )
        
        # Mock tenant
        class MockTenant:
            schema_name = 'oneotalent'
        request.tenant = MockTenant()
        
        self.log_investigation_point(
            "REQUEST_CREATED",
            user.id,
            user.email,
            {
                'endpoint': f'/api/pipelines/{self.pipeline.id}/records/{self.record.id}/',
                'field': field_name,
                'value': new_value
            }
        )
        
        # Step 3: JWT Authentication
        auth_result = self.auth_class.authenticate(request)
        if not auth_result:
            self.log_investigation_point("JWT_AUTH_FAILED", user.id, user.email)
            return False
            
        authenticated_user, validated_token = auth_result
        
        self.log_investigation_point(
            "JWT_AUTH_SUCCESS",
            authenticated_user.id,
            authenticated_user.email,
            {
                'expected_user': user.id,
                'auth_match': authenticated_user.id == user.id,
                'token_user_id': validated_token.get('user_id')
            }
        )
        
        if authenticated_user.id != user.id:
            print(f"❌ JWT AUTH MISMATCH: Expected {user.id}, got {authenticated_user.id}")
            return False
        
        request.user = authenticated_user
        
        # Step 4: ViewSet Processing (within tenant schema)
        with schema_context('oneotalent'):
            view = RecordViewSet()
            view.request = request
            view.kwargs = {'pipeline_pk': self.pipeline.id, 'pk': self.record.id}
            
            # Mock get_object to return our record
            view.get_object = lambda: self.record
            
            # Step 5: Get serializer with user context
            serializer_class = view.get_serializer_class()
            context = view.get_serializer_context()
        
            self.log_investigation_point(
                "SERIALIZER_CONTEXT_CREATED",
                context['request'].user.id,
                context['request'].user.email,
                {
                    'serializer_class': serializer_class.__name__,
                    'context_user_match': context['request'].user.id == user.id
                }
            )
            
            # Step 6: Serializer Update (this is where user context gets set)
            serializer = serializer_class(instance=self.record, data=request_data, context=context)
            
            if not serializer.is_valid():
                self.log_investigation_point("SERIALIZER_VALIDATION_FAILED", user.id, user.email, 
                                           {'errors': serializer.errors})
                return False
            
            # Capture original data before update for signal
            original_data = self.record.data.copy()
            
            self.log_investigation_point(
                "SERIALIZER_VALIDATION_SUCCESS",
                serializer.context['request'].user.id,
                serializer.context['request'].user.email,
                {'validated_data': serializer.validated_data}
            )
            
            # Step 7: Perform serializer update (this triggers updated_by assignment)
            # Set original data for signal detection
            self.record._original_data = original_data
            
            # This is the critical moment - serializer.save() sets updated_by
            updated_record = serializer.save()
            
            self.log_investigation_point(
                "RECORD_UPDATED_BY_SERIALIZER",
                updated_record.updated_by.id if updated_record.updated_by else None,
                updated_record.updated_by.email if updated_record.updated_by else None,
                {
                    'record_id': updated_record.id,
                    'expected_user': user.id,
                    'updated_by_match': updated_record.updated_by.id == user.id if updated_record.updated_by else False
                }
            )
            
        # Step 8: Check audit log creation (signals should have fired)
        time.sleep(0.1)  # Small delay for signal processing
        
        with schema_context('oneotalent'):
            latest_audit = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(self.record.id),
                action='updated'
            ).order_by('-timestamp').first()
            
            if latest_audit:
                self.log_investigation_point(
                    "AUDIT_LOG_CREATED",
                    latest_audit.user.id if latest_audit.user else None,
                    latest_audit.user.email if latest_audit.user else None,
                    {
                        'audit_log_id': latest_audit.id,
                        'expected_user': user.id,
                        'audit_user_match': latest_audit.user.id == user.id if latest_audit.user else False,
                        'changes_summary': latest_audit.changes.get('changes_summary', [])[:2]  # First 2 changes
                    }
                )
            else:
                self.log_investigation_point("AUDIT_LOG_NOT_FOUND", user.id, user.email)
                
        # Step 9: Test Activity API call (what frontend does to get activity)
        activity_request = self.factory.get(
            f'/api/pipelines/{self.pipeline.id}/records/{self.record.id}/history/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_HOST='oneotalent.localhost'
        )
        activity_request.tenant = MockTenant()
        activity_request.user = authenticated_user
        
        with schema_context('oneotalent'):
            activity_view = RecordViewSet()
            activity_view.request = activity_request
            activity_view.kwargs = {'pipeline_pk': self.pipeline.id, 'pk': self.record.id}
            activity_view.get_object = lambda: self.record
            
            activity_response = activity_view.history(activity_request, pk=self.record.id, pipeline_pk=self.pipeline.id)
        
        if activity_response.status_code == 200:
            activities = activity_response.data.get('activities', [])
            if activities:
                recent_activity = activities[0]
                activity_user = recent_activity.get('user', {})
                
                self.log_investigation_point(
                    "ACTIVITY_API_RESPONSE",
                    None,  # No direct user ID in API context
                    activity_user.get('email'),
                    {
                        'activity_count': len(activities),
                        'recent_activity_type': recent_activity.get('type'),
                        'recent_activity_user': activity_user.get('email'),
                        'expected_user': user.email,
                        'activity_user_match': activity_user.get('email') == user.email,
                        'api_requester': authenticated_user.email
                    }
                )
                
                return activity_user.get('email') == user.email
        
        return False
    
    def test_concurrent_users_with_deep_instrumentation(self):
        """Test concurrent users with comprehensive instrumentation"""
        print("\n🔬 DEEP CONCURRENT USER INVESTIGATION")
        print("=" * 80)
        
        # Test sequential updates first to establish baseline
        print("\n📋 SEQUENTIAL TESTING (Baseline):")
        josh_sequential = self.simulate_complete_record_update_flow(
            self.josh, 'test_field', f'sequential_josh_{int(time.time())}'
        )
        
        saul_sequential = self.simulate_complete_record_update_flow(
            self.saul, 'test_field', f'sequential_saul_{int(time.time())}'
        )
        
        admin_sequential = self.simulate_complete_record_update_flow(
            self.admin, 'test_field', f'sequential_admin_{int(time.time())}'
        )
        
        # Test concurrent updates
        print("\n⚡ CONCURRENT TESTING (Race Condition Detection):")
        results = {}
        
        def concurrent_update(user, field_value, results_dict):
            result = self.simulate_complete_record_update_flow(user, 'test_field', field_value)
            results_dict[user.email] = result
        
        # Create threads for concurrent execution
        threads = []
        
        for i in range(3):  # Multiple rounds
            josh_thread = threading.Thread(
                target=concurrent_update,
                args=(self.josh, f'concurrent_josh_{i}_{int(time.time())}', results)
            )
            
            saul_thread = threading.Thread(
                target=concurrent_update,
                args=(self.saul, f'concurrent_saul_{i}_{int(time.time())}', results)
            )
            
            admin_thread = threading.Thread(
                target=concurrent_update,
                args=(self.admin, f'concurrent_admin_{i}_{int(time.time())}', results)
            )
            
            threads.extend([josh_thread, saul_thread, admin_thread])
        
        # Start all threads simultaneously
        print(f"🚀 Starting {len(threads)} concurrent operations...")
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        return {
            'sequential': {
                'josh': josh_sequential,
                'saul': saul_sequential, 
                'admin': admin_sequential
            },
            'concurrent': results
        }
    
    def analyze_investigation_results(self):
        """Analyze all investigation points for anomalies"""
        print("\n📊 DEEP INVESTIGATION ANALYSIS")
        print("=" * 80)
        
        # Group by user and analyze patterns
        user_patterns = {}
        
        for result in self.investigation_results:
            user_email = result['user_email']
            if user_email not in user_patterns:
                user_patterns[user_email] = []
            user_patterns[user_email].append(result)
        
        # Analyze each user's context flow
        for user_email, user_results in user_patterns.items():
            print(f"\n👤 USER CONTEXT FLOW: {user_email}")
            print("-" * 60)
            
            context_anomalies = []
            expected_user_id = None
            
            for i, result in enumerate(user_results):
                if expected_user_id is None and result['user_id']:
                    expected_user_id = result['user_id']
                
                # Check for user ID consistency
                if result['user_id'] and result['user_id'] != expected_user_id:
                    context_anomalies.append({
                        'point': result['point'],
                        'expected': expected_user_id,
                        'actual': result['user_id'],
                        'step': i
                    })
                
                status = "✅" if result['user_id'] == expected_user_id or result['user_id'] is None else "❌"
                print(f"  {status} {result['point']}: User {result['user_id']} - Thread {result['thread_id']}")
                
                # Show additional context for key points
                if result['additional_context']:
                    for key, value in result['additional_context'].items():
                        if 'match' in key.lower():
                            match_status = "✅" if value else "❌"
                            print(f"      {match_status} {key}: {value}")
            
            if context_anomalies:
                print(f"\n⚠️  USER CONTEXT ANOMALIES DETECTED FOR {user_email}:")
                for anomaly in context_anomalies:
                    print(f"    Step {anomaly['step']}: {anomaly['point']} - Expected {anomaly['expected']}, got {anomaly['actual']}")
            else:
                print(f"✅ No user context anomalies detected for {user_email}")
        
        # Check for cross-user contamination
        print(f"\n🔍 CROSS-USER CONTAMINATION ANALYSIS:")
        
        # Group by thread to see if multiple users appeared in same thread
        thread_users = {}
        for result in self.investigation_results:
            thread_id = result['thread_id']
            if thread_id not in thread_users:
                thread_users[thread_id] = set()
            if result['user_email']:
                thread_users[thread_id].add(result['user_email'])
        
        contaminated_threads = {tid: users for tid, users in thread_users.items() if len(users) > 1}
        
        if contaminated_threads:
            print("⚠️  THREAD CONTAMINATION DETECTED:")
            for thread_id, users in contaminated_threads.items():
                print(f"    Thread {thread_id}: {', '.join(users)}")
        else:
            print("✅ No thread contamination detected")
        
        return {
            'user_patterns': user_patterns,
            'context_anomalies': sum(len(user_results) for user_results in user_patterns.values()),
            'contaminated_threads': contaminated_threads
        }

def main():
    """Run the deep user context investigation"""
    print("🔬 DEEP USER CONTEXT INVESTIGATION")
    print("=" * 80)
    print("This test traces user context through the entire request lifecycle")
    print("to identify exactly where user attribution might be getting corrupted.")
    print()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
    
    investigation = DeepUserContextInvestigation()
    
    # Setup test environment
    if not investigation.setup_test_environment():
        print("❌ Failed to setup test environment")
        return
    
    # Run comprehensive investigation
    test_results = investigation.test_concurrent_users_with_deep_instrumentation()
    
    # Analyze results
    analysis = investigation.analyze_investigation_results()
    
    # Final assessment
    print("\n" + "=" * 80)
    print("🏁 DEEP INVESTIGATION SUMMARY")
    print("=" * 80)
    
    sequential_success = all(test_results['sequential'].values())
    concurrent_success_rate = sum(test_results['concurrent'].values()) / len(test_results['concurrent']) if test_results['concurrent'] else 0
    
    print(f"📊 Sequential Testing: {'✅ PASSED' if sequential_success else '❌ FAILED'}")
    print(f"📊 Concurrent Success Rate: {concurrent_success_rate:.1%}")
    print(f"📊 Investigation Points Analyzed: {len(investigation.investigation_results)}")
    print(f"📊 User Context Anomalies: {analysis['context_anomalies']}")
    print(f"📊 Thread Contamination: {len(analysis['contaminated_threads'])} threads")
    
    if sequential_success and concurrent_success_rate > 0.9 and len(analysis['contaminated_threads']) == 0:
        print("\n🎉 INVESTIGATION RESULT: USER CONTEXT SYSTEM IS WORKING CORRECTLY")
        print("📋 The user attribution issue is likely frontend-related:")
        print("   • Browser session conflicts")
        print("   • WebSocket message ordering")
        print("   • Frontend state management")
        print("   • Client-side caching")
    else:
        print("\n⚠️  INVESTIGATION RESULT: BACKEND USER CONTEXT ISSUES DETECTED")
        print("🐛 User attribution corruption confirmed in backend system")
        print("🔧 Further investigation needed in:")
        if not sequential_success:
            print("   • Sequential request processing")
        if concurrent_success_rate <= 0.9:
            print("   • Concurrent request handling")
        if len(analysis['contaminated_threads']) > 0:
            print("   • Thread-level user context isolation")

if __name__ == '__main__':
    main()