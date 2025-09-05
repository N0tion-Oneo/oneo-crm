#!/usr/bin/env python
"""
Test the actual participant-settings API endpoint to see what's happening.
"""

import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant
from authentication.models import UserType
from communications.views_settings import ParticipantSettingsViewSet
from rest_framework.test import force_authenticate
from rest_framework.request import Request
import json

User = get_user_model()


def test_api_endpoint():
    """Test the actual API endpoint"""
    
    print("\n" + "=" * 80)
    print("TESTING PARTICIPANT SETTINGS API ENDPOINT")
    print("=" * 80)
    
    try:
        tenant = Tenant.objects.filter(schema_name__isnull=False).exclude(schema_name='public').first()
        if not tenant:
            print("❌ No tenant available")
            return False
        
        print(f"\n📍 Tenant: {tenant.name} (schema: {tenant.schema_name})")
        
        with schema_context(tenant.schema_name):
            # Get different user types to test
            test_users = []
            
            # Get admin user
            admin_type = UserType.objects.filter(name='Admin').first()
            if admin_type:
                admin_user = User.objects.filter(user_type=admin_type).first()
                if admin_user:
                    test_users.append(('Admin', admin_user))
            
            # Get manager user
            manager_type = UserType.objects.filter(name='Manager').first()
            if manager_type:
                manager_user = User.objects.filter(user_type=manager_type).first()
                if manager_user:
                    test_users.append(('Manager', manager_user))
            
            # Get regular user
            user_type = UserType.objects.filter(name='User').first()
            if user_type:
                regular_user = User.objects.filter(user_type=user_type).first()
                if regular_user:
                    test_users.append(('User', regular_user))
            
            # If no specific users, just get any user
            if not test_users:
                any_user = User.objects.first()
                if any_user:
                    user_type_name = any_user.user_type.name if hasattr(any_user, 'user_type') and any_user.user_type else 'Unknown'
                    test_users.append((user_type_name, any_user))
            
            # Create request factory
            factory = RequestFactory()
            
            print("\n📋 Testing endpoint with different users:")
            print("-" * 60)
            
            for user_type_name, user in test_users:
                print(f"\n🔍 Testing as {user_type_name}: {user.email}")
                
                # Print user permissions
                if hasattr(user, 'user_type') and user.user_type:
                    participant_perms = user.user_type.base_permissions.get('participants', [])
                    print(f"   Participant permissions: {participant_perms}")
                
                # Create a GET request
                django_request = factory.get('/api/v1/participant-settings/')
                
                # Convert to DRF Request
                request = Request(django_request)
                
                # Force authenticate the user
                force_authenticate(request, user=user)
                
                # Create viewset instance
                viewset = ParticipantSettingsViewSet()
                viewset.action = 'list'
                viewset.request = request
                viewset.format_kwarg = None
                
                # Test permission check
                try:
                    has_permission = viewset.check_permissions(request)
                    print(f"   ✅ Permission check passed")
                    
                    # Try to actually call the list method
                    response = viewset.list(request)
                    print(f"   ✅ API call successful: Status {response.status_code}")
                    if response.status_code == 200:
                        print(f"   ✅ Response data received")
                    
                except Exception as e:
                    error_msg = str(e)
                    if "permission" in error_msg.lower() or "403" in error_msg or "forbidden" in error_msg.lower():
                        print(f"   ❌ Permission DENIED: {error_msg}")
                    else:
                        print(f"   ❌ Other error: {error_msg}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_tenant_middleware():
    """Check if tenant middleware might be the issue"""
    
    print("\n" + "=" * 80)
    print("CHECKING TENANT CONTEXT")
    print("=" * 80)
    
    # Check if we need specific domain/subdomain handling
    print("\n⚠️ IMPORTANT: The frontend might be making requests with a specific subdomain")
    print("   that doesn't match the tenant schema.")
    print("\n   Common issues:")
    print("   1. Frontend is at 'localhost:3000' but API expects 'demo.localhost:8000'")
    print("   2. JWT token might not include tenant information")
    print("   3. Tenant middleware might not be correctly identifying the tenant")
    
    return True


def main():
    """Run tests"""
    print("\n🔍 API ENDPOINT TESTING")
    
    test_api_endpoint()
    check_tenant_middleware()
    
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("\nIf the permission check passes in this test but fails from the frontend,")
    print("the issue is likely:")
    print("1. JWT token not being sent correctly")
    print("2. Tenant context not being set correctly")
    print("3. User not being authenticated properly")
    print("4. CORS or other middleware blocking the request")


if __name__ == "__main__":
    main()
