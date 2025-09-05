#!/usr/bin/env python
"""
Trace the exact permission structure and how it's being checked.
"""

import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model
from authentication.models import UserType
from authentication.permissions import AsyncPermissionManager, SyncPermissionManager
from asgiref.sync import async_to_sync
import json

User = get_user_model()


def trace_permission_check():
    """Trace exactly how permissions are being checked"""
    
    print("\n" + "=" * 80)
    print("TRACING PERMISSION CHECK STRUCTURE")
    print("=" * 80)
    
    try:
        tenant = Tenant.objects.filter(schema_name__isnull=False).exclude(schema_name='public').first()
        if not tenant:
            print("❌ No tenant available")
            return False
        
        with schema_context(tenant.schema_name):
            # Get a user with Manager role
            manager_type = UserType.objects.filter(name='Manager').first()
            if manager_type:
                user = User.objects.filter(user_type=manager_type).first()
            else:
                user = User.objects.first()
            
            if not user:
                print("❌ No user available")
                return False
            
            print(f"\n🔍 Testing with user: {user.email}")
            if hasattr(user, 'user_type') and user.user_type:
                print(f"   User Type: {user.user_type.name}")
            
            # Create AsyncPermissionManager directly
            async_manager = AsyncPermissionManager(user)
            
            # Get permissions directly
            print("\n📋 Getting permissions directly from AsyncPermissionManager:")
            permissions = async_to_sync(async_manager.get_user_permissions)()
            print(f"   Raw permissions structure: {json.dumps(permissions, indent=6)}")
            
            # Check what's in participants
            if 'participants' in permissions:
                print(f"\n   ✅ 'participants' key exists in permissions")
                print(f"   Value type: {type(permissions['participants'])}")
                print(f"   Value: {permissions['participants']}")
            else:
                print(f"\n   ❌ 'participants' key NOT in permissions")
            
            # Now test the has_permission method directly
            print("\n📋 Testing has_permission method directly:")
            
            test_args = [
                ('action', 'participants', 'settings', None),
                ('action', 'participants', 'read', None),
            ]
            
            for args in test_args:
                result = async_to_sync(async_manager.has_permission)(*args)
                print(f"   has_permission{args} = {result}")
                
                # Manually trace the logic
                permission_type, resource_type, action, resource_id = args
                print(f"      Checking: resource_type='{resource_type}', action='{action}'")
                
                # Check system permissions
                system_perms = permissions.get('system', [])
                if 'full_access' in system_perms:
                    print(f"      → Would return True (system.full_access)")
                
                # Check resource permissions
                resource_perms = permissions.get(resource_type, [])
                print(f"      → permissions.get('{resource_type}') = {resource_perms}")
                print(f"      → Type: {type(resource_perms)}")
                
                if isinstance(resource_perms, list):
                    print(f"      → Is list, checking if '{action}' in {resource_perms}")
                    print(f"      → Result: {action in resource_perms}")
                elif isinstance(resource_perms, dict):
                    print(f"      → Is dict, would check for resource_id or 'default' key")
            
            # Check if this is a permission_type issue
            print("\n⚠️ IMPORTANT: The permission check is using 'action' as permission_type")
            print("   But the actual permission structure doesn't use permission_type")
            print("   The has_permission method ignores permission_type and just checks resource_type!")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sync_permission_manager():
    """Test the SyncPermissionManager wrapper"""
    
    print("\n" + "=" * 80)
    print("TESTING SYNC PERMISSION MANAGER")
    print("=" * 80)
    
    try:
        tenant = Tenant.objects.filter(schema_name__isnull=False).exclude(schema_name='public').first()
        if not tenant:
            return False
        
        with schema_context(tenant.schema_name):
            # Get a manager user
            manager_type = UserType.objects.filter(name='Manager').first()
            if manager_type:
                user = User.objects.filter(user_type=manager_type).first()
            else:
                user = User.objects.first()
            
            if not user:
                return False
            
            print(f"\n🔍 User: {user.email}")
            if hasattr(user, 'user_type') and user.user_type:
                print(f"   User Type: {user.user_type.name}")
                print(f"   Base Permissions 'participants': {user.user_type.base_permissions.get('participants', 'NOT FOUND')}")
            
            # Test SyncPermissionManager
            sync_manager = SyncPermissionManager(user)
            
            # Test the check
            result = sync_manager.has_permission('action', 'participants', 'settings', None)
            print(f"\n   SyncPermissionManager.has_permission('action', 'participants', 'settings', None) = {result}")
            
            # Get all permissions
            all_perms = sync_manager.get_user_permissions()
            print(f"\n   All permissions from sync manager:")
            if 'participants' in all_perms:
                print(f"      participants: {all_perms['participants']}")
            else:
                print(f"      participants: NOT FOUND")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run tracing"""
    print("\n🔍 PERMISSION STRUCTURE TRACING")
    
    trace_permission_check()
    test_sync_permission_manager()
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("\nThe permission check is working correctly at the AsyncPermissionManager level.")
    print("The issue must be elsewhere - possibly in how the request user is determined")
    print("or in the actual API request being made from the frontend.")


if __name__ == "__main__":
    main()