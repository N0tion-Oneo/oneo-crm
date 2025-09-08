"""
Management command to migrate old permission actions to simplified model.

This command updates existing UserType permissions from the old granular model
(grant, revoke, update, assign, manage_roles) to the simplified model (manage).
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context, get_tenant_model
from authentication.models import UserType
import json


class Command(BaseCommand):
    help = 'Migrate permissions from old granular model to simplified model'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )
        parser.add_argument(
            '--tenant',
            type=str,
            help='Apply to specific tenant only (schema name)',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        specific_tenant = options.get('tenant')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        # Get tenants to process
        TenantModel = get_tenant_model()
        if specific_tenant:
            tenants = TenantModel.objects.filter(schema_name=specific_tenant)
            if not tenants.exists():
                self.stdout.write(self.style.ERROR(f'Tenant {specific_tenant} not found'))
                return
        else:
            tenants = TenantModel.objects.all()
        
        total_updated = 0
        
        for tenant in tenants:
            self.stdout.write(f'\nProcessing tenant: {tenant.schema_name} ({tenant.name})')
            
            with schema_context(tenant.schema_name):
                updated = self._migrate_tenant_permissions(dry_run)
                total_updated += updated
                
                if updated > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'  Updated {updated} user type(s)')
                    )
                else:
                    self.stdout.write('  No updates needed')
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal user types updated: {total_updated}')
        )
    
    def _migrate_tenant_permissions(self, dry_run):
        """Migrate permissions for a single tenant"""
        updated_count = 0
        
        # Old permission actions that should be replaced with 'manage'
        old_actions = ['grant', 'revoke', 'update', 'assign', 'manage_roles']
        
        for user_type in UserType.objects.all():
            permissions = user_type.base_permissions or {}
            updated = False
            
            # Check if 'permissions' category exists
            if 'permissions' in permissions:
                perm_actions = permissions['permissions']
                
                # Handle both list and dict formats
                if isinstance(perm_actions, list):
                    # Check if any old actions exist
                    has_old_actions = any(action in perm_actions for action in old_actions)
                    
                    if has_old_actions:
                        # Remove old actions
                        new_actions = [
                            action for action in perm_actions 
                            if action not in old_actions
                        ]
                        
                        # Add 'manage' if not present
                        if 'manage' not in new_actions:
                            new_actions.append('manage')
                        
                        permissions['permissions'] = new_actions
                        updated = True
                        
                        self.stdout.write(
                            f'    {user_type.name}: Updated permissions '
                            f'{perm_actions} -> {new_actions}'
                        )
                
                elif isinstance(perm_actions, dict) and 'actions' in perm_actions:
                    # Handle nested format
                    actions = perm_actions['actions']
                    has_old_actions = any(action in actions for action in old_actions)
                    
                    if has_old_actions:
                        # Remove old actions
                        new_actions = [
                            action for action in actions 
                            if action not in old_actions
                        ]
                        
                        # Add 'manage' if not present
                        if 'manage' not in new_actions:
                            new_actions.append('manage')
                        
                        perm_actions['actions'] = new_actions
                        updated = True
                        
                        self.stdout.write(
                            f'    {user_type.name}: Updated permissions '
                            f'{actions} -> {new_actions}'
                        )
            
            if updated and not dry_run:
                user_type.base_permissions = permissions
                user_type.save(update_fields=['base_permissions'])
                updated_count += 1
            elif updated and dry_run:
                updated_count += 1
        
        return updated_count