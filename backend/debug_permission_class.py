#!/usr/bin/env python
"""
Debug the ParticipantSettingsPermission class directly.
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
from rest_framework.test import force_authenticate
from unittest.mock import Mock, patch
import json

User = get_user_model()


def debug_permission_class():
    """Debug the permission class step by step"""
    
    print("\n" + "=" * 80)
    print("DEBUGGING ParticipantSettingsPermission CLASS")
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
            factory = RequestFactory()
            django_request = factory.get('/api/v1/participant-settings/')
            request = Request(django_request)
            force_authenticate(request, user=user)
            
            mock_view = Mock()
            mock_view.action = 'list'
            
            # Create permission instance
            perm = ParticipantSettingsPermission()
            
            print("\n📋 Step-by-step permission check:")
            print("-" * 40)
            
            # Step 1: Check if user is authenticated
            print(f"1. request.user.is_authenticated = {request.user.is_authenticated}")
            
            # Step 2: Create permission manager
            print(f"2. Creating SyncPermissionManager for user: {request.user.email}")
            perm_manager = SyncPermissionManager(request.user)
            
            # Step 3: Check what view.action is
            print(f"3. view.action = '{mock_view.action}'")
            
            # Step 4: Check the actual permission
            print(f"4. Calling has_permission with args:")
            print(f"   ('action', 'participants', 'settings', None)")
            
            # Manually check the permission
            result = perm_manager.has_permission('action', 'participants', 'settings', None)
            print(f"5. Manual check result: {result}")
            
            # Now test the actual permission class method
            print("\n6. Testing ParticipantSettingsPermission.has_permission():")
            
            # Patch the has_permission method to see what it's doing
            with patch.object(SyncPermissionManager, 'has_permission', wraps=perm_manager.has_permission) as mock_has_perm:
                try:
                    result = perm.has_permission(request, mock_view)
                    print(f"   Result: {result}")
                    
                    # Check what was called
                    if mock_has_perm.called:
                        print(f"   has_permission was called {mock_has_perm.call_count} time(s)")
                        for call in mock_has_perm.call_args_list:
                            print(f"   Call: {call}")
                    else:
                        print("   has_permission was NOT called!")
                        
                except Exception as e:
                    print(f"   Exception: {e}")
            
            # Check if there's an issue with the permission class itself
            print("\n7. Checking permission class source:")
            import inspect
            source = inspect.getsource(ParticipantSettingsPermission.has_permission)
            print("   Source code:")
            for line in source.split('\n')[:20]:  # First 20 lines
                print(f"   {line}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run debug"""
    debug_permission_class()
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)


if __name__ == "__main__":
    main()
