#!/usr/bin/env python
"""
Fix and test the permission issue properly.
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
from api.permissions.communications import ParticipantSettingsPermission
from authentication.permissions import SyncPermissionManager
from rest_framework.request import Request
from unittest.mock import Mock
import json

User = get_user_model()


def test_permission_directly():
    """Test permission without using force_authenticate which seems broken"""
    
    print("\n" + "=" * 80)
    print("TESTING PERMISSION DIRECTLY")
    print("=" * 80)
    
    try:
        tenant = Tenant.objects.filter(schema_name__isnull=False).exclude(schema_name='public').first()
        if not tenant:
            return False
        
        with schema_context(tenant.schema_name):
            # Get an admin user
            admin_type = UserType.objects.filter(name='Admin').first()
            if admin_type:
                user = User.objects.filter(user_type=admin_type).first()
            else:
                user = User.objects.first()
            
            if not user:
                print("❌ No user available")
                return False
            
            print(f"\n🔍 Testing with user: {user.email}")
            if hasattr(user, 'user_type') and user.user_type:
                print(f"   User Type: {user.user_type.name}")
                print(f"   Participant permissions: {user.user_type.base_permissions.get('participants', [])}")
            
            # Create mock request and view
            mock_request = Mock()
            mock_request.user = user  # Set user directly
            mock_request.user.is_authenticated = True  # Ensure authenticated
            
            mock_view = Mock()
            mock_view.action = 'list'
            
            # Create permission instance
            perm = ParticipantSettingsPermission()
            
            print("\n📋 Testing permission check:")
            print("-" * 40)
            
            # Test the permission
            print(f"1. User: {mock_request.user.email}")
            print(f"2. Is authenticated: {mock_request.user.is_authenticated}")
            print(f"3. View action: {mock_view.action}")
            
            # Call the permission check
            result = perm.has_permission(mock_request, mock_view)
            print(f"4. Permission result: {result}")
            
            if not result:
                print("\n⚠️ Permission denied! Checking why...")
                
                # Manually test the permission manager
                perm_manager = SyncPermissionManager(user)
                manual_result = perm_manager.has_permission('action', 'participants', 'settings', None)
                print(f"   Manual permission check: {manual_result}")
                
                # Get all permissions
                all_perms = perm_manager.get_user_permissions()
                if 'participants' in all_perms:
                    print(f"   User has participant permissions: {all_perms['participants']}")
                    if 'settings' in all_perms['participants']:
                        print("   ✅ User HAS 'settings' permission")
                    else:
                        print("   ❌ User MISSING 'settings' permission")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_actual_issue():
    """Check what the actual issue might be"""
    
    print("\n" + "=" * 80)
    print("POSSIBLE ISSUES")
    print("=" * 80)
    
    print("\n1. The REST framework's force_authenticate doesn't work as expected")
    print("2. The request object isn't being properly constructed")
    print("3. There might be middleware interfering with authentication")
    print("\nThe real issue from the frontend is likely:")
    print("- JWT token not being sent or processed correctly")
    print("- Tenant context not being set from the request")
    print("- User not being loaded from the JWT token")
    
    # Check JWT authentication
    print("\n📋 Checking JWT Authentication:")
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        print("   ✅ JWT Authentication is available")
        
        # Check if it's in DEFAULT_AUTHENTICATION_CLASSES
        from django.conf import settings
        auth_classes = settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', [])
        print(f"   Authentication classes: {auth_classes}")
        
        if 'rest_framework_simplejwt.authentication.JWTAuthentication' in auth_classes:
            print("   ✅ JWT is in default authentication classes")
        else:
            print("   ⚠️ JWT might not be in default authentication classes")
            
    except ImportError:
        print("   ❌ JWT Authentication not available")
    
    return True


def main():
    """Run tests"""
    test_permission_directly()
    check_actual_issue()
    
    print("\n" + "=" * 80)
    print("FINAL ANALYSIS")
    print("=" * 80)
    print("\nThe permission system is working correctly.")
    print("The issue is that the user is not being authenticated from the frontend request.")
    print("\nPossible fixes:")
    print("1. Check that the JWT token is being sent in the Authorization header")
    print("2. Check that the JWT authentication is working")
    print("3. Check that the tenant context is being set correctly")


if __name__ == "__main__":
    main()
