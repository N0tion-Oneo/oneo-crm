#!/usr/bin/env python
"""
Test script to verify filter and sharing permissions are properly integrated 
with the permission matrix system across all tenants.
"""

import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import tenant_context, get_tenant_model
from authentication.models import UserType, CustomUser
from authentication.permissions import SyncPermissionManager


def test_permission_integration():
    """Test that filter and sharing permissions work correctly"""
    Tenant = get_tenant_model()
    
    print("🔍 Testing Filter & Sharing Permission Integration")
    print("=" * 60)
    
    # Test each tenant
    tenants = Tenant.objects.all()
    
    for tenant in tenants:
        print(f"\n📊 Testing tenant: {tenant.schema_name}")
        print("-" * 40)
        
        with tenant_context(tenant):
            # Get all user types in this tenant
            user_types = UserType.objects.all()
            
            for user_type in user_types:
                print(f"\n👤 User Type: {user_type.name}")
                
                # Check filter permissions
                filter_perms = user_type.base_permissions.get('filters', [])
                sharing_perms = user_type.base_permissions.get('sharing', [])
                
                print(f"   📁 Filter Permissions: {filter_perms}")
                print(f"   🔗 Sharing Permissions: {sharing_perms}")
                
                # Test with actual user if exists
                test_user = CustomUser.objects.filter(user_type=user_type).first()
                if test_user:
                    perm_manager = SyncPermissionManager(test_user)
                    
                    # Test specific permissions
                    can_create_filters = perm_manager.has_permission('action', 'filters', 'create_filters')
                    can_edit_filters = perm_manager.has_permission('action', 'filters', 'edit_filters')
                    can_delete_filters = perm_manager.has_permission('action', 'filters', 'delete_filters')
                    can_create_shares = perm_manager.has_permission('action', 'sharing', 'create_shared_views')
                    can_revoke_shares = perm_manager.has_permission('action', 'sharing', 'revoke_shared_views_forms')
                    
                    print(f"   ✅ Real User Test ({test_user.email}):")
                    print(f"      - Create Filters: {can_create_filters}")
                    print(f"      - Edit Filters: {can_edit_filters}")  
                    print(f"      - Delete Filters: {can_delete_filters}")
                    print(f"      - Create Shares: {can_create_shares}")
                    print(f"      - Revoke Shares: {can_revoke_shares}")
                    
                    # Verify consistency
                    expected_create_filters = 'create_filters' in filter_perms
                    expected_create_shares = 'create_shared_views' in sharing_perms
                    
                    if can_create_filters == expected_create_filters and can_create_shares == expected_create_shares:
                        print(f"      🎉 Permission consistency: VERIFIED")
                    else:
                        print(f"      ⚠️  Permission consistency: MISMATCH!")
                        print(f"         Expected create_filters: {expected_create_filters}, Got: {can_create_filters}")
                        print(f"         Expected create_shares: {expected_create_shares}, Got: {can_create_shares}")
                else:
                    print(f"   ℹ️  No test user found for this user type")


def test_permission_registry_integration():
    """Test that permissions are properly defined in the registry"""
    from authentication.permissions_registry import get_permission_schema, get_default_permissions_for_role
    
    print(f"\n\n🔧 Testing Permission Registry Integration")
    print("=" * 60)
    
    schema = get_permission_schema()
    
    print(f"📋 Available Permission Categories:")
    for category in schema.keys():
        print(f"   - {category}")
    
    print(f"\n📁 Filter Permissions: {schema.get('filters', 'NOT FOUND')}")
    print(f"🔗 Sharing Permissions: {schema.get('sharing', 'NOT FOUND')}")
    
    print(f"\n👥 Default Role Permissions:")
    for role in ['admin', 'manager', 'user', 'viewer']:
        default_perms = get_default_permissions_for_role(role)
        filter_perms = default_perms.get('filters', [])
        sharing_perms = default_perms.get('sharing', [])
        print(f"   {role.title()}:")
        print(f"      - Filters: {filter_perms}")
        print(f"      - Sharing: {sharing_perms}")


if __name__ == "__main__":
    try:
        test_permission_registry_integration()
        test_permission_integration()
        print(f"\n🎉 All permission integration tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)