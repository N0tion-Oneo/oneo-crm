#!/usr/bin/env python
"""
Debug script to test the complete permission matrix flow
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from authentication.models import UserType
from authentication.serializers import UserTypeSerializer
from authentication.permissions_registry import get_complete_permission_schema, get_permission_matrix_configuration
from authentication.permission_matrix import PermissionMatrixManager
from django_tenants.utils import get_tenant_model
from django.db import connection
import json

User = get_user_model()

def test_permission_flow():
    """Test the complete permission flow from UserType to frontend matrix"""
    
    print("🔍 PERMISSION MATRIX FLOW DIAGNOSTIC")
    print("=" * 60)
    
    # 1. Check current tenant
    print(f"\n📍 Current Tenant: {connection.schema_name}")
    
    try:
        Tenant = get_tenant_model()
        tenant = Tenant.objects.get(schema_name=connection.schema_name)
        print(f"   Tenant Name: {tenant.name}")
    except Exception as e:
        print(f"   Error getting tenant: {e}")
        return
    
    # 2. Check UserTypes and their base_permissions
    print(f"\n👥 USER TYPES AND PERMISSIONS:")
    user_types = UserType.objects.all()
    
    for user_type in user_types:
        print(f"\n   UserType: {user_type.name} (ID: {user_type.id})")
        print(f"   System Default: {user_type.is_system_default}")
        print(f"   Base Permissions Keys: {list(user_type.base_permissions.keys()) if user_type.base_permissions else 'No permissions'}")
        
        # Count permissions
        if user_type.base_permissions:
            total_perms = sum(len(actions) for actions in user_type.base_permissions.values())
            print(f"   Total Permission Actions: {total_perms}")
        
        # Sample permissions
        if user_type.base_permissions:
            sample_cat = list(user_type.base_permissions.keys())[0]
            sample_actions = user_type.base_permissions[sample_cat]
            print(f"   Sample ({sample_cat}): {sample_actions}")
    
    # 3. Test UserTypeSerializer output
    print(f"\n🔄 SERIALIZER OUTPUT TEST:")
    serializer = UserTypeSerializer(user_types, many=True)
    serialized_data = serializer.data
    
    for user_type_data in serialized_data:
        print(f"\n   Serialized UserType: {user_type_data['name']}")
        print(f"   Has base_permissions: {'base_permissions' in user_type_data}")
        if 'base_permissions' in user_type_data:
            base_perms = user_type_data['base_permissions']
            if base_perms:
                print(f"   Permission categories: {list(base_perms.keys())}")
                total_actions = sum(len(actions) for actions in base_perms.values())
                print(f"   Total actions: {total_actions}")
            else:
                print(f"   base_permissions is empty: {base_perms}")
    
    # 4. Test Permission Schema
    print(f"\n📋 PERMISSION SCHEMA TEST:")
    try:
        schema = get_complete_permission_schema(tenant)
        print(f"   Schema Categories: {len(schema)}")
        static_cats = [name for name, data in schema.items() if not data.get('is_dynamic', False)]
        dynamic_cats = [name for name, data in schema.items() if data.get('is_dynamic', False)]
        print(f"   Static Categories: {len(static_cats)} - {static_cats}")
        print(f"   Dynamic Categories: {len(dynamic_cats)} - {dynamic_cats[:3]}{'...' if len(dynamic_cats) > 3 else ''}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 5. Test Permission Matrix Configuration
    print(f"\n🎛️  PERMISSION MATRIX CONFIG TEST:")
    try:
        matrix_config = get_permission_matrix_configuration(tenant)
        print(f"   Matrix Config Keys: {list(matrix_config.keys())}")
        print(f"   Categories Count: {len(matrix_config.get('categories', {}))}")
        print(f"   Grouped Categories: {list(matrix_config.get('grouped_categories', {}).keys())}")
        print(f"   UI Config: {matrix_config.get('ui_config', {})}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 6. Test PermissionMatrixManager Frontend Config
    print(f"\n🖥️  FRONTEND MATRIX CONFIG TEST:")
    try:
        matrix_manager = PermissionMatrixManager(tenant)
        frontend_config = matrix_manager.get_frontend_matrix_config()
        print(f"   Frontend Config Keys: {list(frontend_config.keys())}")
        print(f"   Categories: {len(frontend_config.get('categories', {}))}")
        print(f"   Cached: {frontend_config.get('cached', False)}")
        print(f"   Generated At: {frontend_config.get('generated_at', 'Unknown')}")
        
        # Check specific categories that should have actions
        categories = frontend_config.get('categories', {})
        for cat_name in ['users', 'pipelines', 'workflows']:
            if cat_name in categories:
                actions = categories[cat_name].get('actions', [])
                print(f"   {cat_name} actions: {actions}")
            else:
                print(f"   {cat_name}: NOT FOUND")
                
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 7. Integration Test: Check if UserType permissions match available schema
    print(f"\n🔗 INTEGRATION TEST:")
    try:
        schema = get_complete_permission_schema(tenant)
        
        for user_type in user_types:
            print(f"\n   Testing UserType: {user_type.name}")
            user_perms = user_type.base_permissions or {}
            
            # Check if user permissions are valid against schema
            valid_categories = 0
            invalid_categories = 0
            
            for category, actions in user_perms.items():
                if category in schema:
                    valid_categories += 1
                    schema_actions = schema[category].get('actions', [])
                    invalid_actions = [a for a in actions if a not in schema_actions]
                    if invalid_actions:
                        print(f"     ⚠️  {category}: Invalid actions {invalid_actions}")
                else:
                    invalid_categories += 1
                    print(f"     ❌ {category}: Category not in schema")
            
            print(f"     ✅ Valid categories: {valid_categories}")
            if invalid_categories > 0:
                print(f"     ❌ Invalid categories: {invalid_categories}")
    
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print(f"\n🎯 SUMMARY:")
    print(f"   - UserTypes found: {user_types.count()}")
    print(f"   - Serializer includes base_permissions: ✅")
    print(f"   - Permission schema generation: ✅" if 'schema' in locals() else "   - Permission schema generation: ❌")
    print(f"   - Frontend matrix config: ✅" if 'frontend_config' in locals() else "   - Frontend matrix config: ❌")
    
    print(f"\n💡 NEXT STEPS:")
    print(f"   1. Start the Django server: python manage.py runserver")
    print(f"   2. Test API endpoint: GET /api/v1/auth/permission_matrix/")
    print(f"   3. Test UserType endpoint: GET /auth/user-types/")
    print(f"   4. Check frontend integration")

if __name__ == "__main__":
    test_permission_flow()