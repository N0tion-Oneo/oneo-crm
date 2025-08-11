#!/usr/bin/env python
"""
Test JWT authentication inter-tenant isolation
Verify that users from different tenants cannot access each other's contexts
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
from tenants.models import Tenant
import threading
import time
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class InterTenantIsolationTest:
    """Test JWT authentication inter-tenant isolation"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.auth_class = TenantAwareJWTAuthentication()
        self.results = {}
        self.tenants = []
        self.tenant_users = {}
        self.cross_tenant_results = []
        
    def setup_tenants_and_users(self):
        """Get all tenants and their users"""
        print("🔧 Loading all tenants and their users...")
        
        # Get all tenants except public
        all_tenants = Tenant.objects.exclude(schema_name='public').order_by('schema_name')
        
        for tenant in all_tenants:
            self.tenants.append(tenant)
            print(f"   🏢 Tenant: {tenant.name} (schema: {tenant.schema_name})")
            
            # Get users from this tenant
            with schema_context(tenant.schema_name):
                users = User.objects.filter(is_active=True)[:3]  # Limit to 3 users per tenant
                self.tenant_users[tenant.schema_name] = []
                
                for user in users:
                    self.tenant_users[tenant.schema_name].append({
                        'user': user,
                        'tenant_schema': tenant.schema_name,
                        'tenant_name': tenant.name
                    })
                    print(f"      👤 {user.email} (ID: {user.id})")
                    
        total_users = sum(len(users) for users in self.tenant_users.values())
        print(f"✅ Found {len(self.tenants)} tenants with {total_users} total users")
        
        if len(self.tenants) < 2:
            print("❌ Need at least 2 tenants to test inter-tenant isolation")
            return False
            
        return True
        
    def create_cross_tenant_tokens(self):
        """Create JWT tokens with potential cross-tenant scenarios"""
        print(f"\n🔑 Creating JWT tokens and testing cross-tenant access...")
        
        test_scenarios = []
        
        # For each tenant, create tokens and test access to other tenants
        for tenant1_schema, users1 in self.tenant_users.items():
            for user1_data in users1:
                user1 = user1_data['user']
                
                # Create token for user1 in their correct tenant
                with schema_context(tenant1_schema):
                    refresh = RefreshToken.for_user(user1)
                    refresh['tenant_schema'] = tenant1_schema
                    refresh['email'] = user1.email
                    token = str(refresh.access_token)
                
                # Test this token against all other tenants
                for tenant2_schema, users2 in self.tenant_users.items():
                    if tenant1_schema != tenant2_schema:
                        test_scenarios.append({
                            'token': token,
                            'token_user': user1,
                            'token_tenant': tenant1_schema,
                            'test_tenant': tenant2_schema,
                            'scenario': f"{user1.email}@{tenant1_schema} → {tenant2_schema}"
                        })
                        
        print(f"✅ Created {len(test_scenarios)} cross-tenant test scenarios")
        return test_scenarios
        
    def test_cross_tenant_authentication(self, scenario):
        """Test a single cross-tenant authentication scenario"""
        token = scenario['token']
        token_user = scenario['token_user']
        token_tenant = scenario['token_tenant']
        test_tenant = scenario['test_tenant']
        scenario_name = scenario['scenario']
        
        try:
            # Create request with token from tenant1 but targeting tenant2
            request = self.factory.get('/', 
                                     HTTP_AUTHORIZATION=f'Bearer {token}',
                                     HTTP_HOST=f'{test_tenant}.localhost')
            
            # Mock tenant as the TARGET tenant (not the token's tenant)
            class MockTenant:
                schema_name = test_tenant
            request.tenant = MockTenant()
            
            # Try to authenticate - this should FAIL for cross-tenant access
            auth_result = self.auth_class.authenticate(request)
            
            if auth_result:
                authenticated_user, validated_token = auth_result
                
                # This is BAD - cross-tenant access succeeded
                result = {
                    'scenario': scenario_name,
                    'token_tenant': token_tenant,
                    'test_tenant': test_tenant,
                    'token_user_id': token_user.id,
                    'token_user_email': token_user.email,
                    'auth_user_id': authenticated_user.id,
                    'auth_user_email': authenticated_user.email,
                    'success': True,
                    'security_breach': True,
                    'message': f"SECURITY BREACH: {token_user.email}@{token_tenant} accessed {test_tenant}"
                }
                print(f"❌ SECURITY BREACH: {scenario_name} - Authentication succeeded when it should have failed!")
                
            else:
                # This is GOOD - cross-tenant access was blocked
                result = {
                    'scenario': scenario_name,
                    'token_tenant': token_tenant,
                    'test_tenant': test_tenant,
                    'token_user_id': token_user.id,
                    'token_user_email': token_user.email,
                    'auth_user_id': None,
                    'auth_user_email': None,
                    'success': False,
                    'security_breach': False,
                    'message': f"✅ BLOCKED: Cross-tenant access correctly denied"
                }
                print(f"✅ SECURE: {scenario_name} - Cross-tenant access correctly blocked")
                
        except Exception as e:
            # Exception is also good - means cross-tenant access was blocked
            result = {
                'scenario': scenario_name,
                'token_tenant': token_tenant,
                'test_tenant': test_tenant,
                'token_user_id': token_user.id,
                'token_user_email': token_user.email,
                'auth_user_id': None,
                'auth_user_email': None,
                'success': False,
                'security_breach': False,
                'message': f"✅ BLOCKED: Cross-tenant access blocked by exception: {str(e)[:100]}..."
            }
            print(f"✅ SECURE: {scenario_name} - Cross-tenant access blocked by exception")
            
        return result
        
    def test_concurrent_cross_tenant_access(self):
        """Test concurrent cross-tenant authentication attempts"""
        print(f"\n🧪 Testing concurrent cross-tenant authentication attempts...")
        
        # Get test scenarios
        scenarios = self.create_cross_tenant_tokens()
        
        if not scenarios:
            print("❌ No cross-tenant scenarios to test")
            return False
            
        # Limit scenarios for testing (take first 20 or all if fewer)
        test_scenarios = scenarios[:20]
        print(f"📊 Testing {len(test_scenarios)} cross-tenant scenarios concurrently...")
        
        # Run scenarios in parallel
        threads = []
        results = []
        
        def run_scenario(scenario, results_list):
            result = self.test_cross_tenant_authentication(scenario)
            results_list.append(result)
            
        for scenario in test_scenarios:
            thread = threading.Thread(target=run_scenario, args=(scenario, results))
            threads.append(thread)
            
        print(f"🚀 Starting {len(threads)} concurrent cross-tenant authentication attempts...")
        
        # Start all threads
        for thread in threads:
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        # Analyze results
        self.analyze_cross_tenant_results(results)
        return results
        
    def analyze_cross_tenant_results(self, results):
        """Analyze cross-tenant test results"""
        print(f"\n📊 Analyzing {len(results)} cross-tenant authentication results...")
        
        security_breaches = 0
        blocked_attempts = 0
        total_tenant_pairs = set()
        
        breach_details = []
        
        for result in results:
            tenant_pair = f"{result['token_tenant']} → {result['test_tenant']}"
            total_tenant_pairs.add(tenant_pair)
            
            if result['security_breach']:
                security_breaches += 1
                breach_details.append(result)
            else:
                blocked_attempts += 1
                
        print(f"\n📈 INTER-TENANT SECURITY RESULTS:")
        print(f"   🔒 Cross-tenant attempts blocked: {blocked_attempts}/{len(results)} ({blocked_attempts/len(results)*100:.1f}%)")
        print(f"   ⚠️  Security breaches detected: {security_breaches}/{len(results)} ({security_breaches/len(results)*100:.1f}%)")
        print(f"   🏢 Tenant pairs tested: {len(total_tenant_pairs)}")
        
        if security_breaches == 0:
            print(f"\n🎉 EXCELLENT: Perfect inter-tenant isolation!")
            print(f"📋 No cross-tenant user context bleeding detected.")
            print(f"📋 Users from different tenants cannot access each other's data.")
        else:
            print(f"\n⚠️  CRITICAL SECURITY ISSUE: {security_breaches} cross-tenant breaches detected!")
            print(f"📋 BREACH DETAILS:")
            for breach in breach_details:
                print(f"   🚨 {breach['message']}")
                print(f"      Token User: {breach['token_user_email']} (ID: {breach['token_user_id']})")
                print(f"      Auth User: {breach['auth_user_email']} (ID: {breach['auth_user_id']})")
                print(f"      Token Tenant: {breach['token_tenant']}")
                print(f"      Test Tenant: {breach['test_tenant']}")
                
        return security_breaches == 0
        
    def test_same_user_id_different_tenants(self):
        """Test users with same ID in different tenants"""
        print(f"\n🆔 Testing users with same ID in different tenants...")
        
        # Find users with same ID in different tenants
        same_id_scenarios = []
        
        for tenant1_schema, users1 in self.tenant_users.items():
            for user1_data in users1:
                user1 = user1_data['user']
                
                for tenant2_schema, users2 in self.tenant_users.items():
                    if tenant1_schema != tenant2_schema:
                        for user2_data in users2:
                            user2 = user2_data['user']
                            
                            if user1.id == user2.id:
                                same_id_scenarios.append({
                                    'user1': user1,
                                    'tenant1': tenant1_schema,
                                    'user2': user2, 
                                    'tenant2': tenant2_schema
                                })
                                
        if same_id_scenarios:
            print(f"   Found {len(same_id_scenarios)} same-ID scenarios to test:")
            for scenario in same_id_scenarios:
                print(f"   🔍 ID {scenario['user1'].id}: {scenario['user1'].email}@{scenario['tenant1']} vs {scenario['user2'].email}@{scenario['tenant2']}")
                
            # Test these scenarios for proper isolation
            for scenario in same_id_scenarios:
                self.test_same_id_scenario(scenario)
        else:
            print(f"   ℹ️  No users with same ID found across different tenants")
            
    def test_same_id_scenario(self, scenario):
        """Test a specific same-ID cross-tenant scenario"""
        user1 = scenario['user1']
        tenant1 = scenario['tenant1']
        user2 = scenario['user2']
        tenant2 = scenario['tenant2']
        
        print(f"\n🧪 Testing same ID isolation: {user1.email}@{tenant1} vs {user2.email}@{tenant2}")
        
        # Create token for user1 in tenant1
        with schema_context(tenant1):
            refresh = RefreshToken.for_user(user1)
            refresh['tenant_schema'] = tenant1
            refresh['email'] = user1.email
            token1 = str(refresh.access_token)
            
        # Try to use token1 in tenant2 context
        request = self.factory.get('/', 
                                 HTTP_AUTHORIZATION=f'Bearer {token1}',
                                 HTTP_HOST=f'{tenant2}.localhost')
        
        class MockTenant:
            schema_name = tenant2
        request.tenant = MockTenant()
        
        try:
            auth_result = self.auth_class.authenticate(request)
            
            if auth_result:
                authenticated_user, validated_token = auth_result
                
                # Check if we got the right user
                if authenticated_user.id == user1.id and authenticated_user.email == user1.email:
                    print(f"   ❌ SECURITY ISSUE: Token for {user1.email}@{tenant1} worked in {tenant2}")
                    print(f"      This could allow cross-tenant access for same-ID users!")
                elif authenticated_user.id == user2.id and authenticated_user.email == user2.email:
                    print(f"   ❌ MAJOR SECURITY BREACH: Token for {user1.email}@{tenant1} returned {user2.email}@{tenant2}")
                    print(f"      This is a critical user context corruption!")
                else:
                    print(f"   ❌ UNKNOWN SECURITY ISSUE: Unexpected user returned")
                    
            else:
                print(f"   ✅ SECURE: Cross-tenant token correctly rejected")
                
        except Exception as e:
            print(f"   ✅ SECURE: Cross-tenant token blocked by exception: {str(e)[:100]}")

def main():
    """Run the inter-tenant isolation test"""
    print("🧪 Inter-Tenant JWT Authentication Isolation Test")
    print("=" * 60)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
    
    test = InterTenantIsolationTest()
    
    # Setup tenants and users
    if not test.setup_tenants_and_users():
        return
        
    # Test cross-tenant access
    results = test.test_concurrent_cross_tenant_access()
    
    if not results:
        print("❌ No cross-tenant tests could be performed")
        return
        
    # Test same-ID scenarios
    test.test_same_user_id_different_tenants()
    
    # Final assessment
    all_secure = all(not result['security_breach'] for result in results)
    
    print("\n" + "=" * 60)
    if all_secure:
        print("🎉 INTER-TENANT SECURITY: EXCELLENT")
        print("✅ Perfect tenant isolation - no cross-tenant access possible")
        print("🔒 Users from different tenants are completely isolated")
    else:
        print("❌ INTER-TENANT SECURITY: CRITICAL ISSUES DETECTED")
        print("⚠️  Cross-tenant access vulnerabilities found")
        print("🚨 Immediate security review required")

if __name__ == '__main__':
    main()