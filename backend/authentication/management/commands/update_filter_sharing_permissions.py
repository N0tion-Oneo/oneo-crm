"""
Management command to update existing user types with filter and sharing permissions.

This command adds the missing 'filters' and 'sharing' permissions to existing 
user types based on their role level.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import tenant_context, get_tenant_model
from authentication.models import UserType
from authentication.permissions_registry import get_default_permissions_for_role


class Command(BaseCommand):
    help = 'Update existing user types with filter and sharing permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema name to update (default: all tenants)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        Tenant = get_tenant_model()
        dry_run = options['dry_run']
        specific_tenant = options['tenant']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Get tenants to update
        if specific_tenant:
            try:
                tenants = [Tenant.objects.get(schema_name=specific_tenant)]
                self.stdout.write(f'Updating tenant: {specific_tenant}')
            except Tenant.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Tenant "{specific_tenant}" does not exist')
                )
                return
        else:
            tenants = Tenant.objects.all()
            self.stdout.write(f'Updating all tenants ({tenants.count()} found)')

        total_updated = 0
        
        for tenant in tenants:
            self.stdout.write(f'\n--- Processing tenant: {tenant.schema_name} ---')
            
            with tenant_context(tenant):
                try:
                    updated_count = self.update_tenant_permissions(dry_run)
                    total_updated += updated_count
                    
                    if updated_count > 0:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Updated {updated_count} user types in {tenant.schema_name}'
                            )
                        )
                    else:
                        self.stdout.write(
                            f'No updates needed for {tenant.schema_name}'
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error updating {tenant.schema_name}: {e}'
                        )
                    )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN COMPLETE - Would have updated {total_updated} user types'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nUpdate complete! Updated {total_updated} user types across all tenants'
                )
            )

    def update_tenant_permissions(self, dry_run=False):
        """Update user type permissions within a tenant context"""
        updated_count = 0
        
        user_types = UserType.objects.all()
        
        for user_type in user_types:
            # Get expected permissions for this role level
            role_level = self.determine_role_level(user_type)
            expected_permissions = get_default_permissions_for_role(role_level)
            
            # Check if filters and sharing permissions are missing
            current_permissions = user_type.base_permissions or {}
            needs_update = False
            
            # Check for missing filter permissions
            if 'filters' not in current_permissions:
                needs_update = True
                if not dry_run:
                    current_permissions['filters'] = expected_permissions.get('filters', [])
                self.stdout.write(
                    f'  + Adding filters permissions to {user_type.name}: {expected_permissions.get("filters", [])}'
                )
            
            # Check for missing sharing permissions
            if 'sharing' not in current_permissions:
                needs_update = True
                if not dry_run:
                    current_permissions['sharing'] = expected_permissions.get('sharing', [])
                self.stdout.write(
                    f'  + Adding sharing permissions to {user_type.name}: {expected_permissions.get("sharing", [])}'
                )
            
            # Save changes
            if needs_update:
                if not dry_run:
                    with transaction.atomic():
                        user_type.base_permissions = current_permissions
                        user_type.save(update_fields=['base_permissions'])
                updated_count += 1
        
        return updated_count

    def determine_role_level(self, user_type):
        """
        Determine the role level based on user type name and permissions.
        This is a heuristic approach since we don't store role level explicitly.
        """
        name_lower = user_type.name.lower()
        
        # Check by name patterns first
        if 'admin' in name_lower:
            return 'admin'
        elif 'manager' in name_lower:
            return 'manager' 
        elif 'viewer' in name_lower:
            return 'viewer'
        elif 'user' in name_lower:
            return 'user'
        
        # Check by permission patterns
        permissions = user_type.base_permissions or {}
        
        # If has system.full_access, it's admin
        if permissions.get('system', []) and 'full_access' in permissions['system']:
            return 'admin'
        
        # If can create users, it's likely manager
        if permissions.get('users', []) and 'create' in permissions['users']:
            return 'manager'
        
        # If has very limited permissions, it's viewer
        if len(permissions) <= 3:
            return 'viewer'
        
        # Default to user
        return 'user'