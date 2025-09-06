"""
Management command to update existing permissions to nested structure under 'settings' resource
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context
from authentication.models import UserType
# Permission registry is used for reference only
import json


class Command(BaseCommand):
    help = 'Update existing permissions to nested structure under settings resource'

    def handle(self, *args, **options):
        """Update permissions for all user types across all tenants"""
        
        # Get all tenants
        TenantModel = get_tenant_model()
        tenants = TenantModel.objects.all()
        
        self.stdout.write(self.style.WARNING('Updating permissions to nested structure...'))
        
        # Define the old to new permission mapping
        permission_mapping = {
            # Old format -> New format
            ('organization_settings', 'read'): ('settings', 'read_organization'),
            ('organization_settings', 'update'): ('settings', 'update_organization'),
            ('branding_settings', 'read'): ('settings', 'read_branding'),
            ('branding_settings', 'update'): ('settings', 'update_branding'),
            ('localization_settings', 'read'): ('settings', 'read_localization'),
            ('localization_settings', 'update'): ('settings', 'update_localization'),
            ('security_settings', 'read'): ('settings', 'read_security'),
            ('security_settings', 'update'): ('settings', 'update_security'),
            ('data_policies_settings', 'read'): ('settings', 'read_data_policies'),
            ('data_policies_settings', 'update'): ('settings', 'update_data_policies'),
            ('billing_settings', 'read'): ('settings', 'read_billing'),
            ('billing_settings', 'update'): ('settings', 'update_billing'),
            ('communication_general_settings', 'read'): ('settings', 'read_communication_general'),
            ('communication_general_settings', 'update'): ('settings', 'update_communication_general'),
            ('communication_provider_settings', 'read'): ('settings', 'read_communication_provider'),
            ('communication_provider_settings', 'update'): ('settings', 'update_communication_provider'),
            ('communication_advanced_settings', 'read'): ('settings', 'read_communication_advanced'),
            ('communication_advanced_settings', 'update'): ('settings', 'update_communication_advanced'),
        }
        
        # Process each tenant
        for tenant in tenants:
            self.stdout.write(f"Processing tenant: {tenant.schema_name}")
            
            with schema_context(tenant.schema_name):
                # Get all user types in this tenant
                user_types = UserType.objects.all()
                
                for user_type in user_types:
                    permissions = user_type.base_permissions or {}
                    updated = False
                    
                    # Create new settings permissions structure if not exists
                    if 'settings' not in permissions:
                        permissions['settings'] = {'actions': []}
                    
                    # Ensure settings has actions list
                    settings_perms = permissions.get('settings', {})
                    if isinstance(settings_perms, dict):
                        if not isinstance(settings_perms.get('actions'), list):
                            permissions['settings']['actions'] = []
                    else:
                        # If settings is not a dict, recreate it
                        permissions['settings'] = {'actions': []}
                    
                    # Process old permissions and migrate them
                    for (old_resource, old_action), (new_resource, new_action) in permission_mapping.items():
                        # Check if old permission exists
                        if old_resource in permissions:
                            old_perms = permissions.get(old_resource, {})
                            # Check the structure of old_perms
                            if isinstance(old_perms, dict):
                                actions = old_perms.get('actions', [])
                            elif isinstance(old_perms, list):
                                actions = old_perms
                            else:
                                continue
                            
                            if old_action in actions:
                                # Add to new structure if not already there
                                if new_action not in permissions['settings']['actions']:
                                    permissions['settings']['actions'].append(new_action)
                                    updated = True
                                    self.stdout.write(
                                        f"  Migrated {old_resource}.{old_action} -> {new_resource}.{new_action} "
                                        f"for {user_type.name}"
                                    )
                    
                    # Remove old permission resources (except communications which stays)
                    old_resources = [
                        'organization_settings', 'branding_settings', 'localization_settings',
                        'security_settings', 'data_policies_settings', 'billing_settings',
                        'communication_general_settings', 'communication_provider_settings',
                        'communication_advanced_settings'
                    ]
                    
                    for old_resource in old_resources:
                        if old_resource in permissions:
                            del permissions[old_resource]
                            updated = True
                            self.stdout.write(f"  Removed old resource: {old_resource}")
                    
                    # Add general read/update permissions if user had any settings permissions
                    if permissions['settings']['actions']:
                        # If user has any read_* permission, give them general read
                        if any(action.startswith('read_') for action in permissions['settings']['actions']):
                            if 'read' not in permissions['settings']['actions']:
                                permissions['settings']['actions'].append('read')
                                updated = True
                        
                        # If user has any update_* permission, give them general update  
                        if any(action.startswith('update_') for action in permissions['settings']['actions']):
                            if 'update' not in permissions['settings']['actions']:
                                permissions['settings']['actions'].append('update')
                                updated = True
                    
                    # Clean up duplicates
                    if permissions.get('settings', {}).get('actions'):
                        permissions['settings']['actions'] = list(set(permissions['settings']['actions']))
                    
                    # Save if updated
                    if updated:
                        user_type.base_permissions = permissions
                        user_type.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Updated permissions for {user_type.name} in {tenant.schema_name}"
                            )
                        )
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Successfully updated all permissions to nested structure!')
        )
        self.stdout.write(
            self.style.WARNING(
                '\n⚠️  Please restart your Django server for changes to take effect.'
            )
        )