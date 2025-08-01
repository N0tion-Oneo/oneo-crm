"""
Management command to setup default user types for tenants
Can be run on specific tenants or all tenants
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django_tenants.utils import schema_context
from tenants.models import Tenant
from authentication.models import UserType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup default user types (Admin, Manager, User, Viewer) for tenants'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Specific tenant schema name to setup (if not provided, runs on all tenants)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing user types with new permissions'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating anything'
        )
    
    def handle(self, *args, **options):
        tenant_schema = options.get('tenant')
        force_update = options.get('force', False)
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        if tenant_schema:
            # Setup for specific tenant
            try:
                tenant = Tenant.objects.get(schema_name=tenant_schema)
                self.setup_tenant_user_types(tenant, force_update, dry_run)
            except Tenant.DoesNotExist:
                raise CommandError(f"Tenant with schema '{tenant_schema}' does not exist")
        else:
            # Setup for all tenants (excluding public schema)
            tenants = Tenant.objects.exclude(schema_name='public')
            total_tenants = tenants.count()
            
            self.stdout.write(f"🏢 Setting up user types for {total_tenants} tenants...")
            
            success_count = 0
            error_count = 0
            
            for tenant in tenants:
                try:
                    self.setup_tenant_user_types(tenant, force_update, dry_run)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"❌ Failed for tenant {tenant.name}: {e}")
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ Completed: {success_count} successful, {error_count} errors")
            )
    
    def setup_tenant_user_types(self, tenant, force_update=False, dry_run=False):
        """Setup default user types for a single tenant"""
        self.stdout.write(f"🏢 Processing tenant: {tenant.name} ({tenant.schema_name})")
        
        # Comprehensive permission definitions
        default_types = [
            {
                'name': 'Admin',
                'slug': 'admin',
                'description': 'Full access to all tenant features and system administration',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'system': ['full_access'],
                    'users': ['create', 'read', 'update', 'delete', 'impersonate', 'assign_roles'],
                    'user_types': ['create', 'read', 'update', 'delete'],
                    'pipelines': ['create', 'read', 'update', 'delete', 'clone', 'export', 'import'],
                    'records': ['create', 'read', 'update', 'delete', 'bulk_edit', 'export', 'import'],
                    'fields': ['create', 'read', 'update', 'delete', 'configure'],
                    'relationships': ['create', 'read', 'update', 'delete', 'traverse'],
                    'workflows': ['create', 'read', 'update', 'delete', 'execute'],
                    'communications': ['create', 'read', 'update', 'delete', 'send'],
                    'settings': ['read', 'update'],
                    'monitoring': ['read', 'update'],
                    'ai_features': ['create', 'read', 'update', 'delete', 'configure'],
                    'reports': ['create', 'read', 'update', 'delete', 'export'],
                    'api_access': ['full_access']
                }
            },
            {
                'name': 'Manager',
                'slug': 'manager',
                'description': 'Management access with user oversight and advanced features',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'users': ['create', 'read', 'update', 'assign_roles'],
                    'user_types': ['read'],
                    'pipelines': ['create', 'read', 'update', 'clone', 'export'],
                    'records': ['create', 'read', 'update', 'bulk_edit', 'export'],
                    'fields': ['create', 'read', 'update', 'configure'],
                    'relationships': ['create', 'read', 'update', 'traverse'],
                    'workflows': ['create', 'read', 'update', 'execute'],
                    'communications': ['create', 'read', 'update', 'send'],
                    'settings': ['read'],
                    'monitoring': ['read'],
                    'ai_features': ['create', 'read', 'update'],
                    'reports': ['create', 'read', 'update', 'export'],
                    'api_access': ['read', 'write']
                }
            },
            {
                'name': 'User',
                'slug': 'user',
                'description': 'Standard user access with record management capabilities',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'users': ['read'],
                    'user_types': ['read'],
                    'pipelines': ['read', 'update'],
                    'records': ['create', 'read', 'update', 'export'],
                    'fields': ['read', 'update'],
                    'relationships': ['create', 'read', 'update', 'traverse'],
                    'workflows': ['read', 'execute'],
                    'communications': ['create', 'read', 'update'],
                    'settings': ['read'],
                    'ai_features': ['read', 'update'],
                    'reports': ['read', 'export'],
                    'api_access': ['read', 'write']
                }
            },
            {
                'name': 'Viewer',
                'slug': 'viewer',
                'description': 'Read-only access with limited interaction capabilities',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'users': ['read'],
                    'user_types': ['read'],
                    'pipelines': ['read'],
                    'records': ['read', 'export'],
                    'fields': ['read'],
                    'relationships': ['read'],
                    'workflows': ['read'],
                    'communications': ['read'],
                    'settings': ['read'],
                    'ai_features': ['read'],
                    'reports': ['read', 'export'],
                    'api_access': ['read']
                }
            }
        ]
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        try:
            with schema_context(tenant.schema_name):
                with transaction.atomic():
                    self.stdout.write(f"📋 Processing {len(default_types)} default user types...")
                    
                    for user_type_data in default_types:
                        try:
                            if dry_run:
                                # Check if would be created/updated
                                exists = UserType.objects.filter(slug=user_type_data['slug']).exists()
                                if exists and not force_update:
                                    self.stdout.write(f"  📋 Would skip: {user_type_data['name']} (already exists)")
                                    skipped_count += 1
                                elif exists and force_update:
                                    self.stdout.write(f"  🔄 Would update: {user_type_data['name']}")
                                    updated_count += 1
                                else:
                                    self.stdout.write(f"  ✅ Would create: {user_type_data['name']}")
                                    created_count += 1
                                continue
                            
                            # Actual execution
                            user_type, created = UserType.objects.get_or_create(
                                slug=user_type_data['slug'],
                                defaults=user_type_data
                            )
                            
                            if created:
                                created_count += 1
                                self.stdout.write(f"  ✅ Created: {user_type.name}")
                                self.stdout.write(f"     📝 {user_type.description}")
                                self.stdout.write(f"     🔐 {len(user_type.base_permissions)} permission categories")
                            elif force_update:
                                # Update existing user type
                                for field, value in user_type_data.items():
                                    if field != 'slug':  # Don't update the slug
                                        setattr(user_type, field, value)
                                user_type.save()
                                updated_count += 1
                                self.stdout.write(f"  🔄 Updated: {user_type.name}")
                            else:
                                skipped_count += 1
                                self.stdout.write(f"  📋 Exists: {user_type.name}")
                                
                        except IntegrityError as e:
                            self.stdout.write(
                                self.style.WARNING(f"  ⚠️  {user_type_data['slug']} integrity error: {e}")
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"  ❌ Error with {user_type_data['slug']}: {e}")
                            )
                            raise
            
            # Summary
            if not dry_run:
                if created_count > 0 or updated_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"🎉 Tenant {tenant.name}: {created_count} created, "
                            f"{updated_count} updated, {skipped_count} skipped"
                        )
                    )
                else:
                    self.stdout.write(f"📋 Tenant {tenant.name}: All user types already existed")
            else:
                self.stdout.write(
                    f"🔍 Tenant {tenant.name} summary: {created_count} would create, "
                    f"{updated_count} would update, {skipped_count} would skip"
                )
                
        except Exception as e:
            error_msg = f"Failed to setup user types for tenant {tenant.name}: {e}"
            self.stdout.write(self.style.ERROR(f"❌ {error_msg}"))
            logger.error(error_msg)
            raise CommandError(error_msg)