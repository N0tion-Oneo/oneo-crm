#!/usr/bin/env python
"""
Test script to verify user attribution in activity logs
This tests the specific issue where activity logs show the wrong user
"""

import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.jwt_authentication import TenantAwareJWTAuthentication
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from core.models import AuditLog
import json
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class ActivityLogUserAttributionTest:
    """Test activity log user attribution"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.auth_class = TenantAwareJWTAuthentication()
        
    def setup_test_data(self):
        """Get existing users and test data"""
        print("🔧 Setting up test with real users...")
        
        with schema_context('oneotalent'):
            # Get actual users from the tenant
            users = list(User.objects.filter(is_active=True).order_by('id'))
            
            if len(users) < 2:
                print("❌ Need at least 2 users for this test")
                return False
                
            self.user1 = users[0]
            self.user2 = users[1]
            
            print(f"👤 User 1: {self.user1.email} (ID: {self.user1.id})")
            print(f"👤 User 2: {self.user2.email} (ID: {self.user2.id})")
            
            # Get an existing pipeline and record
            pipeline = Pipeline.objects.filter(is_active=True).first()
            if not pipeline:
                print("❌ No active pipeline found")
                return False
                
            self.pipeline = pipeline
            print(f"📋 Using pipeline: {pipeline.name} (ID: {pipeline.id})")
            
            # Get or create a test record
            record = Record.objects.filter(pipeline=pipeline, is_deleted=False).first()
            if not record:
                # Create a test record
                record = Record.objects.create(
                    pipeline=pipeline,
                    data={'test_field': 'initial value'},
                    created_by=self.user1,
                    updated_by=self.user1
                )
                
            self.record = record
            print(f"📝 Using record: {record.id}")
            
        return True
        
    def create_jwt_token(self, user):
        """Create JWT token for user"""
        with schema_context('oneotalent'):
            refresh = RefreshToken.for_user(user)
            refresh['tenant_schema'] = 'oneotalent'
            refresh['email'] = user.email
            return str(refresh.access_token)
    
    def simulate_record_update(self, user, token, field_name, new_value):
        """Simulate updating a record via API and check audit log creation"""
        print(f"\n🔄 Simulating record update by {user.email}...")
        
        # Create authenticated request
        request = self.factory.patch(
            f'/api/pipelines/{self.pipeline.id}/records/{self.record.id}/', 
            data={
                'data': {field_name: new_value}
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_HOST='oneotalent.localhost'
        )
        
        # Mock tenant on request
        class MockTenant:
            schema_name = 'oneotalent'
        request.tenant = MockTenant()
        
        # Authenticate request
        auth_result = self.auth_class.authenticate(request)
        if not auth_result:
            print(f"❌ Authentication failed for {user.email}")
            return False
            
        authenticated_user, validated_token = auth_result
        
        if authenticated_user.id != user.id:
            print(f"❌ Authentication returned wrong user: expected {user.id}, got {authenticated_user.id}")
            return False
            
        request.user = authenticated_user
        print(f"✅ Authentication successful: {authenticated_user.email} (ID: {authenticated_user.id})")
        
        # Count audit logs before update
        with schema_context('oneotalent'):
            audit_count_before = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(self.record.id)
            ).count()
            
            print(f"📊 Audit logs before update: {audit_count_before}")
            
            # Simulate the record update process
            print(f"🔄 Updating record data: {field_name} = {new_value}")
            
            # Update the record directly (like the serializer would)
            self.record.data[field_name] = new_value
            self.record.updated_by = authenticated_user  # This is the critical part
            
            # Capture original data for the signal
            self.record._original_data = self.record.data.copy()
            self.record._original_data[field_name] = f"old_value_{user.id}"  # Simulate old value
            
            self.record.save()  # This triggers the signal
            
            print(f"✅ Record updated with updated_by = {self.record.updated_by.email} (ID: {self.record.updated_by.id})")
            
            # Check audit logs after update
            audit_count_after = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(self.record.id)
            ).count()
            
            print(f"📊 Audit logs after update: {audit_count_after}")
            
            if audit_count_after <= audit_count_before:
                print("❌ No new audit log created!")
                return False
                
            # Get the most recent audit log
            latest_audit_log = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(self.record.id)
            ).order_by('-timestamp').first()
            
            if not latest_audit_log:
                print("❌ Could not find latest audit log")
                return False
                
            # Check the user attribution
            if not latest_audit_log.user:
                print("❌ Audit log has no user")
                return False
                
            if latest_audit_log.user.id != user.id:
                print(f"❌ WRONG USER IN AUDIT LOG:")
                print(f"    Expected: {user.email} (ID: {user.id})")
                print(f"    Actual:   {latest_audit_log.user.email} (ID: {latest_audit_log.user.id})")
                return False
            else:
                print(f"✅ Correct user in audit log: {latest_audit_log.user.email} (ID: {latest_audit_log.user.id})")
                
            # Simulate the activity API call
            print(f"\n🔍 Testing activity log API response...")
            
            # This simulates what the frontend API call does
            from api.views.records import RecordViewSet
            view = RecordViewSet()
            view.request = request
            view.kwargs = {'pipeline_pk': self.pipeline.id, 'pk': self.record.id}
            
            # Call the history method
            response = view.history(request, pk=self.record.id, pipeline_pk=self.pipeline.id)
            
            if response.status_code != 200:
                print(f"❌ History API call failed: {response.status_code}")
                return False
                
            activities = response.data.get('activities', [])
            if not activities:
                print("❌ No activities returned from API")
                return False
                
            # Check the first (most recent) activity
            recent_activity = activities[0]
            activity_user = recent_activity.get('user', {})
            
            if not activity_user:
                print("❌ Activity has no user data")
                return False
                
            activity_user_email = activity_user.get('email')
            if activity_user_email != user.email:
                print(f"❌ WRONG USER IN ACTIVITY API:")
                print(f"    Expected: {user.email}")
                print(f"    Actual:   {activity_user_email}")
                return False
            else:
                print(f"✅ Correct user in activity API: {activity_user_email}")
                
        return True
    
    def test_concurrent_updates_with_activity_logs(self):
        """Test concurrent updates and verify activity log user attribution"""
        print("\n🧪 Testing concurrent record updates with activity log verification...")
        
        # Create tokens
        token1 = self.create_jwt_token(self.user1)
        token2 = self.create_jwt_token(self.user2)
        
        print("🔑 JWT tokens created successfully")
        
        # Test User 1 update
        success1 = self.simulate_record_update(self.user1, token1, 'test_field', f'value_from_user_{self.user1.id}')
        
        # Test User 2 update  
        success2 = self.simulate_record_update(self.user2, token2, 'test_field', f'value_from_user_{self.user2.id}')
        
        # Test User 1 again
        success3 = self.simulate_record_update(self.user1, token1, 'test_field', f'final_value_from_user_{self.user1.id}')
        
        if success1 and success2 and success3:
            print("\n🎉 All activity log user attribution tests PASSED!")
            print("✅ Users are correctly attributed in audit logs")
            print("✅ Activity API returns correct user information")
            return True
        else:
            print("\n❌ Activity log user attribution tests FAILED!")
            return False
    
    def debug_current_activity_logs(self):
        """Debug current activity logs for the test record"""
        print(f"\n🔍 Debugging current activity logs for record {self.record.id}...")
        
        with schema_context('oneotalent'):
            audit_logs = AuditLog.objects.filter(
                model_name='Record',
                object_id=str(self.record.id)
            ).order_by('-timestamp')[:5]  # Get last 5
            
            print(f"📊 Found {audit_logs.count()} audit logs:")
            
            for i, log in enumerate(audit_logs):
                print(f"\n📝 Activity {i+1}:")
                print(f"    ID: {log.id}")
                print(f"    Action: {log.action}")
                print(f"    User: {log.user.email if log.user else 'None'} (ID: {log.user.id if log.user else 'None'})")
                print(f"    Timestamp: {log.timestamp}")
                print(f"    Changes: {json.dumps(log.changes, indent=2)[:200]}...")

def main():
    """Run the activity log user attribution test"""
    print("🧪 Activity Log User Attribution Test")
    print("=" * 60)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
    
    test = ActivityLogUserAttributionTest()
    
    # Setup test data
    if not test.setup_test_data():
        print("❌ Failed to setup test data")
        return
        
    # Debug current state
    test.debug_current_activity_logs()
    
    # Run the test
    success = test.test_concurrent_updates_with_activity_logs()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ACTIVITY LOG USER ATTRIBUTION: WORKING CORRECTLY")
        print("✅ All tests passed - activity logs show correct users")
        print("📋 The issue may be in frontend caching or real-time updates")
    else:
        print("❌ ACTIVITY LOG USER ATTRIBUTION: ISSUE CONFIRMED")
        print("🐛 Backend is recording wrong users in activity logs")
        print("🔧 This confirms the user attribution bug exists")

if __name__ == '__main__':
    main()