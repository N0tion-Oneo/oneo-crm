from django.core.management.base import BaseCommand, CommandError
from tenants.models import Tenant, Domain
from django.db import transaction


class Command(BaseCommand):
    help = 'Create a new tenant with domain'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Tenant name')
        parser.add_argument('domain', type=str, help='Tenant domain')
        parser.add_argument('--schema', type=str, help='Schema name (optional)')
        parser.add_argument('--max-users', type=int, default=100, help='Maximum users for tenant')
        
        # Tenant admin user arguments
        parser.add_argument('--admin-email', type=str, help='Tenant admin email address')
        parser.add_argument('--admin-password', type=str, help='Tenant admin password')
        parser.add_argument('--admin-first-name', type=str, default='Admin', help='Tenant admin first name')
        parser.add_argument('--admin-last-name', type=str, default='User', help='Tenant admin last name')

    def handle(self, *args, **options):
        name = options['name']
        domain_name = options['domain']
        schema_name = options.get('schema', name.lower().replace(' ', '_').replace('-', '_'))
        max_users = options['max_users']
        
        # Get tenant admin info
        admin_email = options.get('admin_email')
        admin_password = options.get('admin_password')
        admin_first_name = options.get('admin_first_name')
        admin_last_name = options.get('admin_last_name')

        try:
            with transaction.atomic():
                # Check if tenant already exists
                if Tenant.objects.filter(schema_name=schema_name).exists():
                    raise CommandError(f'Tenant with schema "{schema_name}" already exists')
                
                if Domain.objects.filter(domain=domain_name).exists():
                    raise CommandError(f'Domain "{domain_name}" already exists')

                # Create tenant
                tenant = Tenant.objects.create(
                    name=name,
                    schema_name=schema_name,
                    max_users=max_users
                )
                
                # Store admin info as temporary attributes for signal handler
                if admin_email and admin_password:
                    tenant._admin_email = admin_email
                    tenant._admin_password = admin_password
                    tenant._admin_first_name = admin_first_name
                    tenant._admin_last_name = admin_last_name

                # Create domain
                domain = Domain.objects.create(
                    domain=domain_name,
                    tenant=tenant,
                    is_primary=True
                )

                admin_info = ""
                if admin_email and admin_password:
                    admin_info = f'\nTenant admin: {admin_email} (will be created automatically)'
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created tenant "{name}" with domain "{domain_name}"\n'
                        f'Schema: {schema_name}\n'
                        f'Max users: {max_users}{admin_info}\n'
                        f'Platform admin (admin@oneo.com) will be created automatically'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error creating tenant: {str(e)}')