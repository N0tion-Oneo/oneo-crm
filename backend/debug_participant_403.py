#!/usr/bin/env python
"""
Debug script to diagnose the 403 error on participant settings endpoint.
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
from authentication.permissions import SyncPermissionManager
from api.permissions.communications import ParticipantSettingsPermission
from communications.models import ParticipantSettings
from unittest.mock import Mock
import json

User = get_user_model()


def debug_user_permissions():
    """Debug what permissions users actually have"""
    
    print("\n" + "=" * 80)
    print("DEBUGGING 403 ERROR ON PARTICIPANT SETTINGS")
    print("=" * 80)
    
    try:
        # Get a tenant
        tenant = Tenant.objects.filter(schema_name__isnull=False).exclude(schema_name='public').first()
        if not tenant:
            print("❌ No tenant available for debugging")
            return False
        
        print(f"\n📍 Tenant: {tenant.name} (schema: {tenant.schema_name})")
        
        with schema_context(tenant.schema_name):
            # Check all users and their permissions
            users = User.objects.all()[:5]  # Check first 5 users
            
            print("\n👥 USER PERMISSIONS CHECK:")
            print("-" * 60)
            
            for user in users:
                print(f"\n🔍 User: {user.email}")
                print(f"   Is Active: {user.is_active}")
                print(f"   Is Superuser: {user.is_superuser}")
                
                # Check user type
                if hasattr(user, 'user_type') and user.user_type:
                    print(f"   User Type: {user.user_type.name}")
                    print(f"   Base Permissions: {json.dumps(user.user_type.base_permissions, indent=6)}")
                    
                    # Check if participants permissions exist
                    if 'participants' in user.user_type.base_permissions:
                        print(f"   ✅ Has 'participants' in base_permissions: {user.user_type.base_permissions['participants']}")
                    else:
                        print(f"   ❌ No 'participants' in base_permissions")
                else:
                    print(f"   ⚠️ No user_type assigned")
                
                # Test permission manager
                perm_manager = SyncPermissionManager(user)
                
                # Check the actual permission check
                print(f"\n   Testing Permission Checks:")
                test_permissions = [
                    ('action', 'participants', 'settings', None),
                    ('action', 'participants', 'read', None),
                    ('action', 'participants', 'batch', None),
                ]
                
                for perm_args in test_permissions:
                    try:
                        result = perm_manager.has_permission(*perm_args)
                        status = "✅" if result else "❌"
                        print(f"   {status} has_permission{perm_args}: {result}")
                    except Exception as e:
                        print(f"   ❌ has_permission{perm_args}: ERROR - {e}")
                
                # Test the actual permission class
                print(f"\n   Testing ParticipantSettingsPermission:")
                mock_request = Mock()
                mock_request.user = user
                mock_view = Mock()
                mock_view.action = 'list'
                
                settings_perm = ParticipantSettingsPermission()
                try:
                    result = settings_perm.has_permission(mock_request, mock_view)
                    status = "✅" if result else "❌"
                    print(f"   {status} ParticipantSettingsPermission.has_permission('list'): {result}")
                except Exception as e:
                    print(f"   ❌ ParticipantSettingsPermission.has_permission('list'): ERROR - {e}")
            
            # Check if ParticipantSettings exists
            print("\n" + "=" * 60)
            print("📊 PARTICIPANT SETTINGS MODEL CHECK:")
            try:
                settings = ParticipantSettings.get_or_create_for_tenant()
                print(f"   ✅ ParticipantSettings exists/created: ID={settings.id}")
            except Exception as e:
                print(f"   ❌ Error getting ParticipantSettings: {e}")
            
            # Check UserType default permissions
            print("\n" + "=" * 60)
            print("🔧 USER TYPE DEFAULT PERMISSIONS:")
            user_types = UserType.objects.all()
            for ut in user_types:
                print(f"\n   {ut.name}:")
                if 'participants' in ut.base_permissions:
                    print(f"      ✅ participants: {ut.base_permissions['participants']}")
                else:
                    print(f"      ❌ No participants permissions")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_permission_flow():
    """Trace the exact permission check flow"""
    
    print("\n" + "=" * 80)
    print("TRACING PERMISSION CHECK FLOW")
    print("=" * 80)
    
    try:
        tenant = Tenant.objects.filter(schema_name__isnull=False).exclude(schema_name='public').first()
        if not tenant:
            return False
        
        with schema_context(tenant.schema_name):
            # Get a specific user (likely the one getting 403)
            user = User.objects.filter(email='admin@demo.com').first()
            if not user:
                user = User.objects.first()
            
            if not user:
                print("❌ No user available")
                return False
            
            print(f"\n🔍 Testing with user: {user.email}")
            
            # Manually trace the permission check
            print("\n📋 Manual Permission Check Trace:")
            print("-" * 40)
            
            # Step 1: Check authentication
            print(f"1. Is Authenticated: {user.is_authenticated}")
            
            # Step 2: Get permission manager
            perm_manager = SyncPermissionManager(user)
            print(f"2. Created SyncPermissionManager")
            
            # Step 3: Check the actual permission
            print(f"3. Checking permission:")
            print(f"   Method: has_permission")
            print(f"   Args: ('action', 'participants', 'settings', None)")
            
            try:
                # Get the async manager to see internal state
                async_manager = perm_manager.async_manager
                print(f"4. AsyncPermissionManager user: {async_manager.user.email}")
                
                # Get user permissions
                from asgiref.sync import async_to_sync
                all_perms = async_to_sync(async_manager.get_user_permissions)()
                print(f"5. All user permissions: {json.dumps(all_perms, indent=6)}")
                
                # Check the specific permission
                result = perm_manager.has_permission('action', 'participants', 'settings', None)
                print(f"6. Permission result: {result}")
                
                if not result:
                    print("\n⚠️ PERMISSION DENIED - Investigating why:")
                    
                    # Check if user is superuser
                    if user.is_superuser:
                        print("   - User IS superuser (should have all permissions)")
                    else:
                        print("   - User is NOT superuser")
                    
                    # Check user type
                    if hasattr(user, 'user_type') and user.user_type:
                        print(f"   - User type: {user.user_type.name}")
                        perms = user.user_type.base_permissions
                        if 'participants' in perms:
                            print(f"   - User type HAS participants permissions: {perms['participants']}")
                        else:
                            print(f"   - User type MISSING participants permissions")
                    else:
                        print("   - User has NO user_type assigned")
                
            except Exception as e:
                print(f"❌ Error in permission check: {e}")
                import traceback
                traceback.print_exc()
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def fix_missing_permissions():
    """Add participant permissions to existing user types if missing"""
    
    print("\n" + "=" * 80)
    print("FIXING MISSING PARTICIPANT PERMISSIONS")
    print("=" * 80)
    
    try:
        tenant = Tenant.objects.filter(schema_name__isnull=False).exclude(schema_name='public').first()
        if not tenant:
            return False
        
        with schema_context(tenant.schema_name):
            user_types = UserType.objects.all()
            
            default_permissions = {
                'Admin': ['create', 'read', 'update', 'delete', 'link', 'settings', 'batch'],
                'Manager': ['create', 'read', 'update', 'link', 'settings', 'batch'],
                'User': ['read', 'link'],
                'Viewer': ['read']
            }
            
            for ut in user_types:
                if 'participants' not in ut.base_permissions:
                    # Add default permissions based on user type name
                    default_perms = default_permissions.get(ut.name, ['read'])
                    ut.base_permissions['participants'] = default_perms
                    ut.save()
                    print(f"✅ Added participant permissions to {ut.name}: {default_perms}")
                else:
                    print(f"✓ {ut.name} already has participant permissions: {ut.base_permissions['participants']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all debugging steps"""
    print("\n🔍 COMPREHENSIVE 403 ERROR DEBUGGING")
    print("=" * 80)
    
    # Step 1: Debug current permissions
    debug_user_permissions()
    
    # Step 2: Trace permission flow
    check_permission_flow()
    
    # Step 3: Fix missing permissions
    print("\n🔧 ATTEMPTING TO FIX MISSING PERMISSIONS...")
    if fix_missing_permissions():
        print("\n✅ Permissions fixed! Users should now have participant permissions.")
        print("\n📝 Next steps:")
        print("1. Refresh the frontend page")
        print("2. The 403 error should be resolved")
    else:
        print("\n⚠️ Could not automatically fix permissions")
    
    print("\n" + "=" * 80)
    print("DEBUGGING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()