#!/usr/bin/env python
"""
Fix Manager user type to have participant settings permissions.
"""

import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from authentication.models import UserType

def fix_manager_permissions():
    """Add participant settings permission to Manager user type"""
    
    print("\n" + "=" * 80)
    print("FIXING MANAGER PARTICIPANT PERMISSIONS")
    print("=" * 80)
    
    try:
        tenant = Tenant.objects.filter(schema_name__isnull=False).exclude(schema_name='public').first()
        if not tenant:
            print("❌ No tenant available")
            return False
        
        print(f"\n📍 Tenant: {tenant.name} (schema: {tenant.schema_name})")
        
        with schema_context(tenant.schema_name):
            # Get Manager user type
            manager_type = UserType.objects.filter(name='Manager').first()
            
            if not manager_type:
                print("❌ Manager user type not found")
                return False
            
            print(f"\n🔍 Current Manager participant permissions: {manager_type.base_permissions.get('participants', [])}")
            
            # Update Manager permissions to include settings and batch
            manager_perms = ['create', 'read', 'update', 'link', 'settings', 'batch']
            manager_type.base_permissions['participants'] = manager_perms
            manager_type.save()
            
            print(f"✅ Updated Manager participant permissions to: {manager_perms}")
            
            # Also check and update other user types if needed
            user_type_permissions = {
                'Admin': ['create', 'read', 'update', 'delete', 'link', 'settings', 'batch'],
                'Manager': ['create', 'read', 'update', 'link', 'settings', 'batch'],
                'User': ['read', 'link'],
                'Viewer': ['read'],
                'Recruiter': ['read', 'link']  # Recruiter might need link permission too
            }
            
            print("\n📋 Checking all user types:")
            for ut_name, expected_perms in user_type_permissions.items():
                ut = UserType.objects.filter(name=ut_name).first()
                if ut:
                    current_perms = ut.base_permissions.get('participants', [])
                    if current_perms != expected_perms:
                        ut.base_permissions['participants'] = expected_perms
                        ut.save()
                        print(f"   ✅ Updated {ut_name}: {current_perms} → {expected_perms}")
                    else:
                        print(f"   ✓ {ut_name} already correct: {expected_perms}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the fix"""
    if fix_manager_permissions():
        print("\n✅ SUCCESS! Manager and other user types now have correct participant permissions.")
        print("\nPermissions applied:")
        print("- Admin: Full access (create, read, update, delete, link, settings, batch)")
        print("- Manager: Management access (create, read, update, link, settings, batch)")
        print("- User: Basic access (read, link)")
        print("- Viewer: Read-only access (read)")
        print("- Recruiter: Basic access (read, link)")
        print("\n📝 The 403 error should now be resolved. Please refresh the frontend.")
    else:
        print("\n⚠️ Failed to update permissions")


if __name__ == "__main__":
    main()