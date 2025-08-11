#!/usr/bin/env python
"""
Test individual user tokens to isolate the User 2 issue
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

User = get_user_model()

def test_user_tokens():
    """Test both users' tokens individually"""
    
    print("🧪 Individual User Token Test")
    print("=" * 40)
    
    # Get users
    with schema_context('oneotalent'):
        user1 = User.objects.get(id=5)  # testuser1@oneotalent.com
        user2 = User.objects.get(id=6)  # testuser2@oneotalent.com
        
        print(f"👤 User 1: {user1.email} (ID: {user1.id}, Active: {user1.is_active})")
        print(f"👤 User 2: {user2.email} (ID: {user2.id}, Active: {user2.is_active})")
    
    # Test User 1 token
    print(f"\n🔑 Testing User 1 Token...")
    with schema_context('oneotalent'):
        refresh1 = RefreshToken.for_user(user1)
        refresh1['tenant_schema'] = 'oneotalent'
        refresh1['email'] = user1.email
        token1 = str(refresh1.access_token)
        
    success1, result1 = test_token_auth(token1, user1.id, user1.email)
    print(f"   Result: {'✅ SUCCESS' if success1 else '❌ FAILED'} - {result1}")
    
    # Test User 2 token  
    print(f"\n🔑 Testing User 2 Token...")
    with schema_context('oneotalent'):
        refresh2 = RefreshToken.for_user(user2)
        refresh2['tenant_schema'] = 'oneotalent'
        refresh2['email'] = user2.email
        token2 = str(refresh2.access_token)
        
    success2, result2 = test_token_auth(token2, user2.id, user2.email)
    print(f"   Result: {'✅ SUCCESS' if success2 else '❌ FAILED'} - {result2}")
    
    # Test both tokens multiple times to check consistency
    print(f"\n🔄 Testing User 2 Token Consistency (10 attempts)...")
    failures = 0
    for i in range(10):
        success, result = test_token_auth(token2, user2.id, user2.email)
        if not success:
            failures += 1
            print(f"   Attempt {i+1}: ❌ FAILED - {result}")
        else:
            print(f"   Attempt {i+1}: ✅ SUCCESS")
    
    print(f"\n📊 User 2 Consistency Results:")
    print(f"   Success: {10-failures}/10 ({(10-failures)/10*100:.0f}%)")
    print(f"   Failures: {failures}/10 ({failures/10*100:.0f}%)")
    
    if failures == 0:
        print("🎉 User 2 token is working consistently!")
    else:
        print("⚠️  User 2 token has consistency issues")

def test_token_auth(token, expected_user_id, expected_email):
    """Test token authentication"""
    try:
        factory = RequestFactory()
        auth_class = TenantAwareJWTAuthentication()
        
        # Create request
        request = factory.get('/', 
                             HTTP_AUTHORIZATION=f'Bearer {token}',
                             HTTP_HOST='oneotalent.localhost')
        
        # Mock tenant
        class MockTenant:
            schema_name = 'oneotalent'
        request.tenant = MockTenant()
        
        # Authenticate
        result = auth_class.authenticate(request)
        
        if result:
            user, validated_token = result
            if user.id == expected_user_id:
                return True, f"Authenticated as {user.email} (ID: {user.id})"
            else:
                return False, f"Wrong user: expected {expected_user_id}, got {user.id}"
        else:
            return False, "Authentication returned None"
            
    except Exception as e:
        return False, f"Exception: {e}"

if __name__ == '__main__':
    test_user_tokens()