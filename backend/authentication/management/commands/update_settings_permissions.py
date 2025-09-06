"""
Management command to update settings permissions to simplified page-based structure
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import get_tenant_model, schema_context
from authentication.models import UserType
import json


class Command(BaseCommand):
    help = 'Update settings permissions to simplified page-based structure (one permission per page)'

    def handle(self, *args, **options):
        """Update permissions for all user types across all tenants"""
        
        # Get all tenants
        TenantModel = get_tenant_model()
        tenants = TenantModel.objects.all()
        
        self.stdout.write(self.style.WARNING('Updating settings permissions to simplified structure...'))
        
        # Define the old to new permission mapping
        # Map all view/edit/read/update variants to single page permission
        permission_mapping = {
            # Organization settings
            'read_organization': 'organization',
            'update_organization': 'organization',
            'view_organization': 'organization',
            'edit_organization': 'organization',
            
            # Branding settings
            'read_branding': 'branding',
            'update_branding': 'branding',
            'view_branding': 'branding',
            'edit_branding': 'branding',
            
            # Localization settings
            'read_localization': 'localization',
            'update_localization': 'localization',
            'view_localization': 'localization',
            'edit_localization': 'localization',
            
            # Security settings
            'read_security': 'security',
            'update_security': 'security',
            'view_security': 'security',
            'edit_security': 'security',
            
            # Data policies
            'read_data_policies': 'data_policies',
            'update_data_policies': 'data_policies',
            'view_data_policies': 'data_policies',
            'edit_data_policies': 'data_policies',
            
            # Usage/Billing
            'read_billing': 'usage',
            'update_billing': 'usage',
            'view_billing': 'usage',
            'edit_billing': 'usage',
            'read_usage': 'usage',
            'update_usage': 'usage',
            'view_usage': 'usage',
            'edit_usage': 'usage',
            
            # Communication settings
            'read_communication_general': 'communications_general',
            'update_communication_general': 'communications_general',
            'view_communication_general': 'communications_general',
            'edit_communication_general': 'communications_general',
            
            'read_communication_accounts': 'communications_accounts',
            'update_communication_accounts': 'communications_accounts',
            'view_communication_accounts': 'communications_accounts',
            'edit_communication_accounts': 'communications_accounts',
            
            'read_communication_provider': 'communications_providers',
            'update_communication_provider': 'communications_providers',
            'view_communication_provider': 'communications_providers',
            'edit_communication_provider': 'communications_providers',
            'read_communication_providers': 'communications_providers',
            'update_communication_providers': 'communications_providers',
            'view_communication_providers': 'communications_providers',
            'edit_communication_providers': 'communications_providers',
            
            'read_communication_advanced': 'communications_advanced',
            'update_communication_advanced': 'communications_advanced',
            'view_communication_advanced': 'communications_advanced',
            'edit_communication_advanced': 'communications_advanced',
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
                    
                    # Get current settings permissions
                    settings_perms = permissions.get('settings', {})
                    if isinstance(settings_perms, dict):
                        current_actions = settings_perms.get('actions', [])
                    elif isinstance(settings_perms, list):
                        current_actions = settings_perms
                    else:
                        current_actions = []
                    
                    # Track new simplified permissions
                    new_permissions = set()
                    
                    # Process current permissions
                    for action in current_actions:
                        # Skip generic read/update permissions
                        if action in ['read', 'update']:
                            continue
                            
                        # Map old permission to new
                        if action in permission_mapping:
                            new_permissions.add(permission_mapping[action])
                            self.stdout.write(
                                f"  Mapping {action} -> {permission_mapping[action]} for {user_type.name}"
                            )
                    
                    # Also check communication_settings resource if it exists
                    comm_settings = permissions.get('communication_settings', {})
                    if isinstance(comm_settings, dict):
                        comm_actions = comm_settings.get('actions', [])
                    elif isinstance(comm_settings, list):
                        comm_actions = comm_settings
                    else:
                        comm_actions = []
                    
                    # Map communication settings permissions
                    comm_mapping = {
                        'view_general': 'communications_general',
                        'edit_general': 'communications_general',
                        'view_accounts': 'communications_accounts',
                        'edit_accounts': 'communications_accounts',
                        'view_providers': 'communications_providers',
                        'edit_providers': 'communications_providers',
                        'view_advanced': 'communications_advanced',
                        'edit_advanced': 'communications_advanced',
                    }
                    
                    for action in comm_actions:
                        if action in comm_mapping:
                            new_permissions.add(comm_mapping[action])
                            self.stdout.write(
                                f"  Mapping communication_settings.{action} -> {comm_mapping[action]} for {user_type.name}"
                            )
                    
                    # Update permissions if changes were made
                    if new_permissions or current_actions:
                        # Set the new simplified permissions
                        permissions['settings'] = {
                            'actions': sorted(list(new_permissions))
                        }
                        
                        # Remove old communication_settings resource if it exists
                        if 'communication_settings' in permissions:
                            del permissions['communication_settings']
                            self.stdout.write(f"  Removed communication_settings resource")
                        
                        user_type.base_permissions = permissions
                        user_type.save()
                        updated = True
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Updated {user_type.name}: {sorted(list(new_permissions))}"
                            )
                        )
                    
                    # Handle Admin user type - should have all settings permissions
                    if user_type.slug == 'admin':
                        # Ensure admin has all main settings permissions
                        if 'settings' not in permissions:
                            permissions['settings'] = {'actions': []}
                        
                        main_settings_perms = [
                            'organization', 'branding', 'localization', 'security',
                            'data_policies', 'usage', 'communications'
                        ]
                        
                        # Ensure all main settings permissions are present
                        for perm in main_settings_perms:
                            if perm not in permissions['settings']['actions']:
                                permissions['settings']['actions'].append(perm)
                        
                        # Ensure admin has all communication sub-settings permissions
                        if 'communication_settings' not in permissions:
                            permissions['communication_settings'] = {'actions': []}
                        
                        comm_settings_perms = ['general', 'accounts', 'providers', 'advanced']
                        permissions['communication_settings']['actions'] = comm_settings_perms
                        
                        user_type.base_permissions = permissions
                        user_type.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Updated Admin user type with all settings permissions"
                            )
                        )
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Successfully updated all settings permissions to simplified structure!')
        )
        self.stdout.write(
            self.style.WARNING(
                '\n⚠️  Please restart your Django server for changes to take effect.'
            )
        )