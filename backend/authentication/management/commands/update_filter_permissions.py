"""
Management command to update existing user types with new filter and sharing permissions.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import get_tenant_model, tenant_context
from authentication.models import UserType


class Command(BaseCommand):
    help = 'Update existing user types with new filter and sharing permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Update specific tenant only (by schema name)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        """Handle the command execution"""
        TenantModel = get_tenant_model()
        
        # Get tenants to process
        if options['tenant']:
            tenants = [TenantModel.objects.get(schema_name=options['tenant'])]
        else:
            tenants = list(TenantModel.objects.all())
        
        self.stdout.write(f"Processing {len(tenants)} tenant(s)...")
        
        # Define the new permissions to add
        new_permissions = {
            'filters': ['create_filters', 'edit_filters', 'delete_filters'],
            'sharing': ['create_shared_views', 'create_shared_forms', 'configure_shared_views_forms', 'revoke_shared_views_forms']
        }
        
        # Define per user type
        user_type_permissions = {
            'admin': {
                'filters': ['create_filters', 'edit_filters', 'delete_filters'],
                'sharing': ['create_shared_views', 'create_shared_forms', 'configure_shared_views_forms', 'revoke_shared_views_forms']
            },
            'manager': {
                'filters': ['create_filters', 'edit_filters', 'delete_filters'],
                'sharing': ['create_shared_views', 'create_shared_forms', 'configure_shared_views_forms', 'revoke_shared_views_forms']
            },
            'user': {
                'filters': ['create_filters', 'edit_filters'],
                'sharing': ['create_shared_views', 'create_shared_forms']
            },
            'viewer': {
                'filters': [],
                'sharing': []
            }
        }
        
        total_updated = 0
        
        for tenant in tenants:
            self.stdout.write(f"\nProcessing tenant: {tenant.schema_name}")
            
            with tenant_context(tenant):
                try:
                    # Get all user types for this tenant
                    user_types = UserType.objects.all()
                    
                    for user_type in user_types:
                        updated = False
                        permissions = user_type.base_permissions.copy()
                        
                        # Determine permissions based on user type slug
                        type_perms = user_type_permissions.get(user_type.slug, {})
                        
                        # Add new permissions
                        for category, actions in type_perms.items():
                            if category not in permissions:
                                permissions[category] = actions
                                updated = True
                                self.stdout.write(f"  Added {category} permissions to {user_type.name}")
                            elif set(permissions[category]) != set(actions):
                                permissions[category] = actions
                                updated = True
                                self.stdout.write(f"  Updated {category} permissions for {user_type.name}")
                        
                        # Update if changes were made
                        if updated and not options['dry_run']:
                            user_type.base_permissions = permissions
                            user_type.save()
                            total_updated += 1
                            self.stdout.write(f"  ✅ Updated {user_type.name}")
                        elif updated:
                            self.stdout.write(f"  🔄 Would update {user_type.name} (dry run)")
                        else:
                            self.stdout.write(f"  ⏭️  {user_type.name} already up to date")
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing tenant {tenant.schema_name}: {e}")
                    )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f"\n🔄 Dry run complete. Would have updated user types in {len(tenants)} tenants.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Successfully updated {total_updated} user types across {len(tenants)} tenants.")
            )
            
        # Show permission summary
        self.stdout.write("\n📋 New Permission Summary:")
        for category, actions in new_permissions.items():
            self.stdout.write(f"  {category}:")
            for action in actions:
                self.stdout.write(f"    - {action}")