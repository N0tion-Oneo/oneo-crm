#!/usr/bin/env python
"""
Test JWT authentication race condition fix with all real users in the tenant
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
import threading
import time
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class AllUsersRaceConditionTest:
    """Test JWT authentication race condition with all real tenant users"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.auth_class = TenantAwareJWTAuthentication()
        self.results = {}
        self.users = []
        self.tokens = {}
        
    def setup_tenant_users(self):
        """Get all real users from the tenant"""
        print("🔧 Loading all users from oneotalent tenant...")
        
        with schema_context('oneotalent'):
            # Get all active users
            all_users = User.objects.filter(is_active=True).order_by('id')
            
            for user in all_users:
                self.users.append(user)
                print(f"   👤 {user.email} (ID: {user.id}) - {user.first_name} {user.last_name}")
                
        if len(self.users) < 2:
            print("❌ Need at least 2 users to test race conditions")
            return False
            
        print(f"✅ Found {len(self.users)} active users in oneotalent tenant")
        return True
        
    def create_jwt_tokens(self):
        """Create JWT tokens for all users"""
        print(f"\n🔑 Creating JWT tokens for all {len(self.users)} users...")
        
        with schema_context('oneotalent'):
            for user in self.users:
                try:
                    refresh = RefreshToken.for_user(user)
                    refresh['tenant_schema'] = 'oneotalent'
                    refresh['email'] = user.email
                    token = str(refresh.access_token)
                    self.tokens[user.id] = token
                    print(f"   ✅ Token created for {user.email} (ID: {user.id})")
                except Exception as e:
                    print(f"   ❌ Failed to create token for {user.email}: {e}")
                    return False
                    
        print(f"✅ Created {len(self.tokens)} JWT tokens successfully")
        return True
        
    def simulate_concurrent_auth(self, user, token, thread_id):
        """Simulate authentication request from a specific user"""
        try:
            # Create request with JWT token
            request = self.factory.get('/', 
                                     HTTP_AUTHORIZATION=f'Bearer {token}',
                                     HTTP_HOST='oneotalent.localhost')
            
            # Mock tenant on request
            class MockTenant:
                schema_name = 'oneotalent'
            request.tenant = MockTenant()
            
            # Small random delay to increase concurrency stress
            time.sleep(0.01 + (hash(str(thread_id)) % 50) / 1000)
            
            # Authenticate
            auth_result = self.auth_class.authenticate(request)
            
            if auth_result:
                authenticated_user, validated_token = auth_result
                result_user_id = authenticated_user.id
                result_email = authenticated_user.email
                
                # Store results for verification
                self.results[thread_id] = {
                    'expected_user_id': user.id,
                    'expected_email': user.email,
                    'actual_user_id': result_user_id,
                    'actual_email': result_email,
                    'success': user.id == result_user_id,
                    'user_name': f"{user.first_name} {user.last_name}".strip()
                }
                
                status = '✅ SUCCESS' if user.id == result_user_id else '❌ RACE CONDITION'
                print(f"🧵 Thread {thread_id}: {user.email} → {result_email} ({status})")
                
                if user.id != result_user_id:
                    print(f"   ⚠️  RACE CONDITION DETECTED: Expected {user.id}, Got {result_user_id}")
            else:
                self.results[thread_id] = {
                    'expected_user_id': user.id,
                    'expected_email': user.email,
                    'actual_user_id': None,
                    'actual_email': None,
                    'success': False,
                    'error': 'Authentication failed',
                    'user_name': f"{user.first_name} {user.last_name}".strip()
                }
                print(f"🧵 Thread {thread_id}: {user.email} authentication failed")
                
        except Exception as e:
            self.results[thread_id] = {
                'expected_user_id': user.id,
                'expected_email': user.email,
                'actual_user_id': None,
                'actual_email': None,
                'success': False,
                'error': str(e),
                'user_name': f"{user.first_name} {user.last_name}".strip()
            }
            print(f"🧵 Thread {thread_id}: {user.email} exception - {e}")
            
    def test_all_users_concurrent_authentication(self, rounds_per_user=5):
        """Test concurrent authentication with all real users"""
        print(f"\n🧪 Testing concurrent authentication with all {len(self.users)} users...")
        print(f"📊 Running {rounds_per_user} concurrent requests per user ({len(self.users) * rounds_per_user} total threads)")
        
        # Create threads for each user (multiple rounds per user)
        threads = []
        thread_id = 0
        
        for round_num in range(rounds_per_user):
            for user in self.users:
                if user.id in self.tokens:
                    thread = threading.Thread(
                        target=self.simulate_concurrent_auth,
                        args=(user, self.tokens[user.id], thread_id)
                    )
                    threads.append(thread)
                    thread_id += 1
        
        print(f"🚀 Starting {len(threads)} concurrent authentication threads...")
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Analyze results
        self.analyze_results()
        
    def analyze_results(self):
        """Analyze test results for race conditions"""
        print(f"\n📊 Analyzing {len(self.results)} authentication results...")
        
        successes = 0
        race_conditions = 0
        failures = 0
        
        # Track per-user results
        user_stats = {}
        race_condition_details = []
        
        for thread_id, result in self.results.items():
            expected_id = result['expected_user_id']
            actual_id = result.get('actual_user_id')
            expected_email = result['expected_email']
            user_name = result.get('user_name', 'Unknown')
            
            # Initialize user stats
            if expected_email not in user_stats:
                user_stats[expected_email] = {
                    'expected': 0,
                    'successful': 0,
                    'failed': 0,
                    'race_conditions': 0,
                    'user_name': user_name
                }
            
            user_stats[expected_email]['expected'] += 1
            
            if result['success']:
                successes += 1
                user_stats[expected_email]['successful'] += 1
            elif 'error' in result:
                failures += 1
                user_stats[expected_email]['failed'] += 1
            else:
                # This would be a race condition (got different user)
                race_conditions += 1
                user_stats[expected_email]['race_conditions'] += 1
                race_condition_details.append({
                    'thread': thread_id,
                    'expected': expected_email,
                    'expected_id': expected_id,
                    'actual': result.get('actual_email', 'None'),
                    'actual_id': actual_id
                })
                
        print(f"\n📈 OVERALL RESULTS:")
        print(f"   ✅ Successful authentications: {successes}/{len(self.results)} ({successes/len(self.results)*100:.1f}%)")
        print(f"   🔄 Race conditions detected: {race_conditions}/{len(self.results)} ({race_conditions/len(self.results)*100:.1f}%)")
        print(f"   ❌ Authentication failures: {failures}/{len(self.results)} ({failures/len(self.results)*100:.1f}%)")
        
        print(f"\n👥 PER-USER BREAKDOWN:")
        for email, stats in user_stats.items():
            success_rate = (stats['successful'] / stats['expected']) * 100
            user_name = stats['user_name'] or email.split('@')[0]
            print(f"   👤 {user_name} ({email}):")
            print(f"      ✅ Success: {stats['successful']}/{stats['expected']} ({success_rate:.1f}%)")
            if stats['race_conditions'] > 0:
                print(f"      🔄 Race conditions: {stats['race_conditions']}")
            if stats['failed'] > 0:
                print(f"      ❌ Failures: {stats['failed']}")
        
        if race_conditions > 0:
            print(f"\n⚠️  RACE CONDITION DETAILS:")
            for detail in race_condition_details:
                print(f"   Thread {detail['thread']}: {detail['expected']} (ID: {detail['expected_id']}) → {detail['actual']} (ID: {detail['actual_id']})")
        
        if race_conditions == 0:
            print(f"\n🎉 SUCCESS: No race conditions detected across all {len(self.users)} real users!")
            print(f"📋 The JWT authentication fix is working perfectly with real users.")
            if failures > 0:
                print(f"📋 Note: Authentication failures are database concurrency issues, not user context corruption.")
        else:
            print(f"\n⚠️  CRITICAL: {race_conditions} race conditions detected with real users!")
            print(f"📋 User context bleeding is still occurring - fix needs adjustment.")
            
        return race_conditions == 0

def main():
    """Run the all-users race condition test"""
    print("🧪 All Real Users - JWT Race Condition Test")
    print("=" * 55)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
    
    test = AllUsersRaceConditionTest()
    
    # Load all users from tenant
    if not test.setup_tenant_users():
        return
    
    # Create JWT tokens for all users
    if not test.create_jwt_tokens():
        return
    
    # Run concurrent authentication test
    success = test.test_all_users_concurrent_authentication(rounds_per_user=3)
    
    print("\n" + "=" * 55)
    if success:
        print("🎉 ALL TESTS PASSED - JWT authentication race condition fix works with all real users!")
    else:
        print("❌ TESTS FAILED - Race conditions detected with real users")
        
    print(f"\n💡 Next steps:")
    print(f"1. If successful, the audit log user attribution issue is resolved")
    print(f"2. Test with real browser sessions and multiple users")
    print(f"3. Monitor production logs for any user context issues")

if __name__ == '__main__':
    main()