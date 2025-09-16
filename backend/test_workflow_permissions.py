#!/usr/bin/env python
import os
import django
import sys

sys.path.insert(0, '/Users/joshcowan/Oneo\ CRM/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from authentication.models import CustomUser as User, UserType
from authentication.permissions import SyncPermissionManager

with schema_context('oneotalent'):
    # Get admin user
    admin_user = User.objects.filter(email='admin@oneotalent.com').first()
    if admin_user:
        print(f"User: {admin_user.email}")
        print(f"User Type: {admin_user.user_type}")
        print(f"User Type Slug: {admin_user.user_type.slug if admin_user.user_type else 'None'}")
        
        # Test permission manager
        perm_manager = SyncPermissionManager(admin_user)
        
        # Test workflows permissions
        actions = ['read', 'create', 'update', 'delete', 'execute']
        print("\nWorkflow Permissions:")
        for action in actions:
            has_perm = perm_manager.has_permission('action', 'workflows', action)
            print(f"  - workflows.{action}: {has_perm}")
        
        # Check the permission method in detail
        print("\nDebug permission check for 'workflows.read':")
        result = perm_manager.has_permission('action', 'workflows', 'read')
        print(f"  Result: {result}")
    else:
        print("Admin user not found")