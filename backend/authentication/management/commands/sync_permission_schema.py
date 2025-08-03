"""
Management command to synchronize UserType permissions with the global permission schema.

This command ensures all UserTypes have consistent categories matching the permission schema
and applies appropriate default permissions for each role.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context
from tenants.models import Tenant
from authentication.models import UserType
from authentication.permissions_registry import PERMISSION_CATEGORIES
from asgiref.sync import async_to_sync
from authentication.permissions import AsyncPermissionManager
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Synchronize UserType permissions with global permission schema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to sync (default: all tenants)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create backup file of current permissions',
        )

    def handle(self, *args, **options):
        self.dry_run = options.get('dry_run', False)
        self.backup = options.get('backup', False)
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Get tenants to process
        if options.get('tenant'):
            try:
                tenant = Tenant.objects.get(schema_name=options['tenant'])
                tenants = [tenant]
            except Tenant.DoesNotExist:
                raise CommandError(f'Tenant "{options["tenant"]}" not found')
        else:
            tenants = Tenant.objects.exclude(schema_name='public')
        
        self.stdout.write(f'📋 Processing {len(tenants)} tenant(s)...')
        
        total_synced = 0
        
        for tenant in tenants:
            synced_count = self.sync_tenant_permissions(tenant)
            total_synced += synced_count
        
        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully synchronized {total_synced} UserTypes across {len(tenants)} tenant(s)')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'📊 Would synchronize {total_synced} UserTypes across {len(tenants)} tenant(s)')
            )

    def sync_tenant_permissions(self, tenant):
        """Synchronize permissions for a specific tenant"""
        
        with schema_context(tenant.schema_name):
            self.stdout.write(f'\n🏢 Processing tenant: {tenant.name} ({tenant.schema_name})')
            
            # Get all UserTypes in this tenant
            user_types = UserType.objects.all()
            
            if not user_types.exists():
                self.stdout.write('   ⚠️  No UserTypes found in this tenant')
                return 0
            
            # Create backup if requested
            if self.backup and not self.dry_run:
                self.create_backup(tenant, user_types)
            
            synced_count = 0
            
            for user_type in user_types:
                if self.sync_user_type_permissions(user_type):
                    synced_count += 1
            
            # Clear permission caches for this tenant
            if not self.dry_run and synced_count > 0:
                self.clear_permission_caches(user_types)
            
            return synced_count

    def sync_user_type_permissions(self, user_type):
        """Synchronize a single UserType with the schema"""
        
        self.stdout.write(f'   👤 Analyzing {user_type.name} UserType...')
        
        current_permissions = user_type.base_permissions.copy()
        schema_categories = set(PERMISSION_CATEGORIES.keys())
        actual_categories = set(current_permissions.keys())
        
        # Find discrepancies
        missing_categories = schema_categories - actual_categories
        extra_categories = actual_categories - schema_categories
        
        changes_needed = bool(missing_categories or extra_categories)
        
        if not changes_needed:
            self.stdout.write('      ✅ Already in sync with schema')
            return False
        
        # Show what needs to be changed
        if missing_categories:
            self.stdout.write(f'      ❌ Missing categories: {sorted(missing_categories)}')
        
        if extra_categories:
            self.stdout.write(f'      ❓ Extra categories (will merge): {sorted(extra_categories)}')
        
        if self.dry_run:
            return True
        
        # Apply synchronization
        new_permissions = self.build_synchronized_permissions(user_type, current_permissions)
        
        # Save changes
        with transaction.atomic():
            user_type.base_permissions = new_permissions
            user_type.save()
        
        self.stdout.write(f'      ✅ Synchronized with {len(new_permissions)} categories')
        
        return True

    def build_synchronized_permissions(self, user_type, current_permissions):
        """Build new permission structure synchronized with schema"""
        
        new_permissions = {}
        
        # Process each schema category
        for category, category_info in PERMISSION_CATEGORIES.items():
            available_actions = category_info['actions']
            
            # Get appropriate default permissions for this role and category
            default_actions = self.get_default_permissions(user_type.slug, category, available_actions)
            
            # Check if we have existing permissions for this category
            existing_actions = current_permissions.get(category, [])
            
            # Also check legacy/conflicting categories and merge them
            legacy_actions = []
            legacy_categories = self.get_legacy_category_names(category)
            for legacy_cat in legacy_categories:
                if legacy_cat in current_permissions:
                    legacy_actions.extend(current_permissions[legacy_cat])
                    self.stdout.write(f'         🔄 Merging {legacy_cat} → {category}')
            
            # Combine existing, legacy, and defaults (existing takes precedence)
            if existing_actions:
                # User type already has this category, keep existing permissions
                final_actions = existing_actions
            elif legacy_actions:
                # Migrate from legacy category
                final_actions = list(set(legacy_actions))  # Remove duplicates
            else:
                # New category, use defaults
                final_actions = default_actions
                self.stdout.write(f'         ➕ Adding {category} with defaults: {default_actions}')
            
            # Ensure we only include valid actions
            valid_actions = [action for action in final_actions if action in available_actions]
            
            if valid_actions:
                new_permissions[category] = valid_actions
        
        return new_permissions

    def get_legacy_category_names(self, category):
        """Get legacy category names that should be merged into the current category"""
        legacy_mapping = {
            'users': ['user'],
            'records': ['record'],
            'fields': ['field'],
            'pipelines': ['pipeline'],
            'workflows': ['workflow'],
            'relationships': ['relationship'],
            'communications': ['communication'],
            'business_rules': ['business'],
            'ai_features': ['ai'],
            'api_access': ['api']
        }
        
        return legacy_mapping.get(category, [])

    def get_default_permissions(self, user_type_slug, category, available_actions):
        """Get appropriate default permissions for a user type and category"""
        
        # Define role-based defaults
        role_defaults = {
            'admin': {
                # Admin gets all permissions for all categories
                'default': available_actions
            },
            'manager': {
                'system': [],  # No system access
                'users': ['create', 'read', 'update', 'assign_roles'],  # No delete or impersonate
                'user_types': ['read'],  # Can't modify user types
                'monitoring': ['read'],  # Read-only monitoring
                'default': available_actions  # Full access to everything else
            },
            'user': {
                'system': [],  # No system access
                'users': ['read'],  # Can only read users
                'user_types': ['read'],  # Read-only
                'pipelines': ['read', 'update'],  # Can't create/delete pipelines
                'records': ['create', 'read', 'update', 'export'],  # No delete, import, bulk_edit
                'fields': ['read', 'update'],  # Can't create/delete fields
                'workflows': ['read', 'execute'],  # Can't create/modify workflows
                'monitoring': [],  # No monitoring access
                'api_access': ['read', 'write'],  # Limited API access
                'default': ['create', 'read', 'update']  # Basic CRUD without delete
            },
            'viewer': {
                'system': [],  # No system access
                'users': ['read'],  # Read-only
                'user_types': ['read'],  # Read-only
                'monitoring': [],  # No monitoring access
                'api_access': ['read'],  # Read-only API access
                'default': ['read', 'export']  # Read-only with export capability
            }
        }
        
        # Get defaults for this role
        role_config = role_defaults.get(user_type_slug, role_defaults['viewer'])
        
        # Get category-specific defaults or fall back to role default
        category_defaults = role_config.get(category, role_config.get('default', ['read']))
        
        # Ensure we only return valid actions
        return [action for action in category_defaults if action in available_actions]

    def create_backup(self, tenant, user_types):
        """Create a backup file of current permissions"""
        
        backup_data = {
            'tenant': tenant.schema_name,
            'tenant_name': tenant.name,
            'backup_date': datetime.now().isoformat(),
            'user_types': []
        }
        
        for user_type in user_types:
            backup_data['user_types'].append({
                'id': user_type.id,
                'name': user_type.name,
                'slug': user_type.slug,
                'base_permissions': user_type.base_permissions,
                'is_system_default': user_type.is_system_default
            })
        
        backup_filename = f'permissions_backup_{tenant.schema_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(backup_filename, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        self.stdout.write(f'   📁 Backup saved to: {backup_filename}')

    def clear_permission_caches(self, user_types):
        """Clear permission caches for all affected user types"""
        
        self.stdout.write('   🧹 Clearing permission caches...')
        
        try:
            # Clear user type caches
            for user_type in user_types:
                async_to_sync(AsyncPermissionManager.clear_user_type_cache)(user_type.id)
            
            self.stdout.write('   ✅ Permission caches cleared')
            
        except Exception as e:
            self.stdout.write(f'   ⚠️  Warning: Could not clear caches: {e}')