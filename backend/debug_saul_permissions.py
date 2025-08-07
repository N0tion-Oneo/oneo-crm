#!/usr/bin/env python
"""Debug permissions for saul@oneodigital.com in oneotalent tenant"""

import os
import sys

# Set up Django first
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

import django
django.setup()

# Now import django-tenants
from django_tenants.utils import schema_context

from django.contrib.auth import get_user_model
from tenants.models import Tenant
from authentication.permissions import SyncPermissionManager as PermissionManager

def debug_saul_permissions():
    User = get_user_model()
    
    try:
        # Get the oneotalent tenant
        tenant = Tenant.objects.get(schema_name='oneotalent')
        print(f"✅ Found tenant: {tenant.name} ({tenant.schema_name})")
        
        # Switch to tenant context
        with schema_context(tenant.schema_name):
            try:
                # Get the user
                user = User.objects.get(email='saul@oneodigital.com')
                print(f"✅ Found user: {user.email}")
                print(f"   - User type: {user.user_type.name if hasattr(user, 'user_type') and user.user_type else 'No user type'}")
                print(f"   - Is active: {user.is_active}")
                print(f"   - Is superuser: {user.is_superuser}")
                
                # Create permission manager
                pm = PermissionManager(user)
                
                print(f"\n🔍 PERMISSION CHECKS:")
                
                # Test field permissions on pipeline 1 (adjust pipeline ID as needed)
                pipeline_id = "1"  # Change this to a valid pipeline ID in your tenant
                
                permissions_to_test = [
                    ('fields', 'read'),
                    ('fields', 'create'),
                    ('fields', 'update'),
                    ('fields', 'delete'),
                    ('fields', 'configure'),
                    ('fields', 'manage'),
                    ('fields', 'recover'),
                    ('fields', 'reorder'),
                    ('fields', 'migrate'),
                    ('pipelines', 'read'),
                    ('pipelines', 'update'),
                ]
                
                for resource, action in permissions_to_test:
                    result = pm.has_permission('action', resource, action, pipeline_id)
                    status = "✅ ALLOWED" if result else "❌ DENIED"
                    print(f"   {status} - {resource}.{action} on pipeline {pipeline_id}")
                
                # Also test without pipeline ID (general permissions)
                print(f"\n🔍 GENERAL PERMISSIONS (no pipeline):")
                for resource, action in permissions_to_test:
                    result = pm.has_permission('action', resource, action)
                    status = "✅ ALLOWED" if result else "❌ DENIED"
                    print(f"   {status} - {resource}.{action}")
                
                # Check user type permissions
                if hasattr(user, 'user_type') and user.user_type:
                    print(f"\n🔍 USER TYPE BASE PERMISSIONS:")
                    print(f"   User type: {user.user_type.name}")
                    print(f"   Base permissions: {user.user_type.base_permissions}")
                    
                    if 'fields' in user.user_type.base_permissions:
                        print(f"   Field permissions: {user.user_type.base_permissions['fields']}")
                    else:
                        print(f"   ❌ No 'fields' permissions in base_permissions")
                
                # Check permission overrides
                if hasattr(user, 'permission_overrides') and user.permission_overrides:
                    print(f"\n🔍 USER PERMISSION OVERRIDES:")
                    print(f"   Permission overrides: {user.permission_overrides}")
                else:
                    print(f"\n🔍 No permission overrides found")
                    
            except User.DoesNotExist:
                print(f"❌ User 'saul@oneodigital.com' not found in tenant '{tenant.schema_name}'")
                
                # List all users in the tenant
                print(f"\n📋 All users in {tenant.schema_name}:")
                all_users = User.objects.all()
                for u in all_users:
                    print(f"   - {u.email} ({u.user_type.name if hasattr(u, 'user_type') and u.user_type else 'No type'})")
                
    except Tenant.DoesNotExist:
        print(f"❌ Tenant 'oneotalent' not found")
        
        # List all tenants
        print(f"\n📋 Available tenants:")
        all_tenants = Tenant.objects.all()
        for t in all_tenants:
            print(f"   - {t.schema_name}: {t.name}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_saul_permissions()