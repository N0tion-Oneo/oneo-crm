#!/usr/bin/env python
"""
Debug script to investigate User 2 token validation issue
"""

import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from authentication.jwt_authentication import TenantAwareJWTAuthentication
from django.test import RequestFactory
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

User = get_user_model()

def debug_user2_issue():
    """Debug User 2 token validation"""
    
    print("🔍 Debugging User 2 Token Validation Issue")
    print("=" * 50)
    
    # Get User 2 from oneotalent tenant
    with schema_context('oneotalent'):
        try:
            user2 = User.objects.get(id=6)
            print(f"✅ Found User 2: {user2.email} (ID: {user2.id}, Active: {user2.is_active})")
        except User.DoesNotExist:
            print("❌ User 2 not found in oneotalent tenant")
            return
    
    # Create JWT token for User 2
    print("\n🔑 Creating JWT Token for User 2...")
    try:
        with schema_context('oneotalent'):
            refresh = RefreshToken.for_user(user2)
            refresh['tenant_schema'] = 'oneotalent'
            refresh['email'] = user2.email
            access_token_str = str(refresh.access_token)
            print(f"✅ JWT Token created successfully")
            print(f"   Token length: {len(access_token_str)} chars")
            print(f"   Token preview: {access_token_str[:50]}...")
            
            # Decode the token to see what's in it
            access_token = AccessToken(access_token_str)
            payload = dict(access_token.payload)
            print(f"   Token payload: {payload}")
            
    except Exception as e:
        print(f"❌ Error creating token: {e}")
        return
    
    # Test JWT Authentication
    print("\n🧪 Testing JWT Authentication...")
    auth_class = TenantAwareJWTAuthentication()
    factory = RequestFactory()
    
    # Create request
    request = factory.get('/', 
                         HTTP_AUTHORIZATION=f'Bearer {access_token_str}',
                         HTTP_HOST='oneotalent.localhost')
    
    # Mock tenant on request
    class MockTenant:
        schema_name = 'oneotalent'
    request.tenant = MockTenant()
    
    try:
        # Test authentication
        print(f"   🔄 Calling authenticate() method...")
        result = auth_class.authenticate(request)
        
        if result:
            authenticated_user, validated_token = result
            print(f"   ✅ Authentication successful!")
            print(f"   👤 Authenticated user: {authenticated_user.email} (ID: {authenticated_user.id})")
            print(f"   🎯 Expected: testuser2@oneotalent.com (ID: 6)")
            print(f"   🏆 Match: {'YES' if authenticated_user.id == 6 else 'NO'}")
        else:
            print(f"   ❌ Authentication failed - returned None")
            
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()}")
    
    # Test direct token validation
    print("\n🔬 Testing Direct Token Validation...")
    try:
        # Parse the token
        access_token = AccessToken(access_token_str)
        user_id = access_token['user_id']
        token_tenant = access_token.get('tenant_schema')
        
        print(f"   📋 Token user_id: {user_id}")
        print(f"   📋 Token tenant: {token_tenant}")
        
        # Test direct user lookup in tenant context
        with schema_context('oneotalent'):
            try:
                user_from_db = User.objects.get(id=user_id)
                print(f"   ✅ Direct DB lookup successful: {user_from_db.email} (ID: {user_from_db.id})")
            except User.DoesNotExist:
                print(f"   ❌ Direct DB lookup failed - User {user_id} not found in oneotalent")
                
                # Check what users DO exist
                print(f"   📋 Users that DO exist in oneotalent:")
                for user in User.objects.all():
                    print(f"      - ID: {user.id}, Email: {user.email}")
    
    except Exception as e:
        print(f"   ❌ Direct validation error: {e}")
    
    # Test get_user method directly
    print("\n⚙️ Testing get_user() method directly...")
    try:
        access_token = AccessToken(access_token_str)
        validated_token = access_token.payload
        
        # Call our custom get_user method
        user_result = auth_class.get_user(validated_token, request=request, tenant_schema='oneotalent')
        
        if user_result:
            print(f"   ✅ get_user() successful: {user_result.email} (ID: {user_result.id})")
        else:
            print(f"   ❌ get_user() returned None")
            
    except Exception as e:
        print(f"   ❌ get_user() error: {e}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()}")

if __name__ == '__main__':
    debug_user2_issue()