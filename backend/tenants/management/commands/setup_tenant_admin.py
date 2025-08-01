from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from tenants.models import Tenant
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup platform admin user for a tenant (creates Oneo platform admin and optional tenant admin)'

    def add_arguments(self, parser):
        parser.add_argument('schema_name', type=str, help='Tenant schema name')
        parser.add_argument('--admin-email', type=str, help='Tenant admin email (required for tenant user)')
        parser.add_argument('--admin-password', type=str, help='Tenant admin password (required for tenant user)')
        parser.add_argument('--admin-first-name', type=str, help='Tenant admin first name')
        parser.add_argument('--admin-last-name', type=str, help='Tenant admin last name')

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        tenant_admin_email = options.get('admin_email')
        tenant_admin_password = options.get('admin_password')
        tenant_admin_first_name = options.get('admin_first_name', 'Admin')
        tenant_admin_last_name = options.get('admin_last_name', 'User')
        
        try:
            # Get tenant
            tenant = Tenant.objects.get(schema_name=schema_name)
        except Tenant.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Tenant with schema "{schema_name}" does not exist')
            )
            return

        try:
            with schema_context(schema_name):
                User = get_user_model()
                
                # 1. Create Oneo superuser (global platform admin)
                oneo_superuser_email = 'admin@oneo.com'
                if not User.objects.filter(email=oneo_superuser_email).exists():
                    oneo_user = User.objects.create_user(
                        username='oneo_admin',
                        email=oneo_superuser_email,
                        password='oneoadmin123',  # Secure default password
                        is_superuser=True,
                        is_staff=True,
                        is_active=True,
                        first_name='Oneo',
                        last_name='Platform Admin'
                    )
                    
                    # Set user type to Admin
                    from authentication.models import UserType
                    admin_type = UserType.objects.filter(slug='admin').first()
                    if admin_type:
                        oneo_user.user_type = admin_type
                        oneo_user.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Oneo superuser created: {oneo_user.username} ({oneo_user.email})')
                    )
                else:
                    # Update existing user to have admin type if missing
                    oneo_user = User.objects.get(email=oneo_superuser_email)
                    if not oneo_user.user_type:
                        from authentication.models import UserType
                        admin_type = UserType.objects.filter(slug='admin').first()
                        if admin_type:
                            oneo_user.user_type = admin_type
                            oneo_user.save()
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ Oneo superuser user type updated: {oneo_superuser_email}')
                            )
                    self.stdout.write(
                        self.style.WARNING(f'Oneo superuser already exists: {oneo_superuser_email}')
                    )
                
                # 2. Create tenant admin user (if provided)
                if tenant_admin_email and tenant_admin_password:
                    if not User.objects.filter(email=tenant_admin_email).exists():
                        tenant_admin = User.objects.create_user(
                            username=tenant_admin_email,  # Use email as username
                            email=tenant_admin_email,
                            password=tenant_admin_password,
                            is_superuser=False,  # Not a platform superuser
                            is_staff=True,       # Can access admin
                            is_active=True,
                            first_name=tenant_admin_first_name,
                            last_name=tenant_admin_last_name
                        )
                        
                        # Set user type to Admin
                        from authentication.models import UserType
                        admin_type = UserType.objects.filter(slug='admin').first()
                        if admin_type:
                            tenant_admin.user_type = admin_type
                            tenant_admin.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Tenant admin created: {tenant_admin.username} ({tenant_admin.email})')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'Tenant admin already exists: {tenant_admin_email}')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING('No tenant admin email/password provided - skipping tenant admin creation')
                    )
                
                # 3. Support user creation removed - no automatic support users
                
                # Show final user count
                total_users = User.objects.count()
                self.stdout.write(
                    self.style.SUCCESS(f'Total users in {schema_name}: {total_users}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up admin for tenant {schema_name}: {str(e)}')
            )