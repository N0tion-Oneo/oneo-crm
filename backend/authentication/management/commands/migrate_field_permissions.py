"""
Management command to migrate field permissions from old structure to new simplified structure
Old: create, read, update, delete, recover, migrate
New: read, manage (create+update), delete (delete+recover+migrate)
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import schema_context
from authentication.models import UserType
from authentication.permissions_registry import PERMISSION_CATEGORIES
import json


class Command(BaseCommand):
    help = 'Migrate field permissions from 6 actions to 3 simplified actions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema to update',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_tenant = options.get('tenant')
        
        self.stdout.write(self.style.NOTICE('Starting field permission migration...'))
        self.stdout.write(self.style.NOTICE('Old structure: create, read, update, delete, recover, migrate'))
        self.stdout.write(self.style.NOTICE('New structure: read, manage (create+update), delete (delete+recover+migrate)\n'))
        
        # Get all tenant schemas
        cursor = connection.cursor()
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('public', 'information_schema', 'pg_catalog', 'pg_toast')
        """)
        schemas = [row[0] for row in cursor.fetchall()]
        
        if specific_tenant:
            if specific_tenant not in schemas:
                self.stdout.write(self.style.ERROR(f'Tenant {specific_tenant} not found'))
                return
            schemas = [specific_tenant]
        
        total_updated = 0
        
        # Process each tenant
        for schema_name in schemas:
            self.stdout.write(f'\n📂 Processing tenant: {schema_name}')
            
            with schema_context(schema_name):
                user_types = UserType.objects.all()
                
                for user_type in user_types:
                    permissions = user_type.base_permissions or {}
                    
                    # Check if field permissions exist and need updating
                    if 'fields' in permissions:
                        old_field_perms = permissions['fields']
                        
                        if isinstance(old_field_perms, list):
                            new_field_perms = []
                            
                            # Map old permissions to new structure
                            if 'read' in old_field_perms:
                                new_field_perms.append('read')
                            
                            # If they have create OR update, give them manage
                            if 'create' in old_field_perms or 'update' in old_field_perms:
                                if 'manage' not in new_field_perms:
                                    new_field_perms.append('manage')
                            
                            # If they have delete, recover, or migrate, give them delete
                            if 'delete' in old_field_perms or 'recover' in old_field_perms or 'migrate' in old_field_perms:
                                if 'delete' not in new_field_perms:
                                    new_field_perms.append('delete')
                            
                            # Check if permissions changed
                            old_set = set(old_field_perms)
                            new_set = set(new_field_perms)
                            
                            # Only update if there's an actual change
                            needs_update = False
                            
                            # Check if any old permissions need to be removed
                            old_only_perms = {'create', 'update', 'recover', 'migrate'}
                            if old_set.intersection(old_only_perms):
                                needs_update = True
                            
                            if needs_update:
                                self.stdout.write(f'  👤 {user_type.name}:')
                                self.stdout.write(
                                    self.style.WARNING(f'    Old: {sorted(old_field_perms)}')
                                )
                                self.stdout.write(
                                    self.style.SUCCESS(f'    New: {sorted(new_field_perms)}')
                                )
                                
                                if not dry_run:
                                    permissions['fields'] = new_field_perms
                                    user_type.base_permissions = permissions
                                    user_type.save()
                                    total_updated += 1
                                    self.stdout.write(self.style.SUCCESS('    ✅ Updated'))
                                else:
                                    self.stdout.write(self.style.NOTICE('    [DRY RUN] Would update'))
                            else:
                                # Already migrated or no field permissions
                                if old_field_perms:
                                    self.stdout.write(f'  👤 {user_type.name}: Already migrated ({sorted(old_field_perms)})')
                        
                        # Check for any invalid permissions
                        valid_actions = PERMISSION_CATEGORIES['fields']['actions']
                        current_perms = permissions.get('fields', [])
                        if isinstance(current_perms, list):
                            invalid = [p for p in current_perms if p not in valid_actions]
                            if invalid:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f'  ⚠️  {user_type.name} has invalid permissions: {invalid}'
                                    )
                                )
        
        # Summary
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN COMPLETE - No changes made'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Migration complete! Updated {total_updated} user types'))
        
        self.stdout.write('\n📋 New field permission structure:')
        self.stdout.write('  • read: View fields only (no configuration access)')
        self.stdout.write('  • manage: Access config, create and update fields')
        self.stdout.write('  • delete: Delete, recover, and migrate fields')