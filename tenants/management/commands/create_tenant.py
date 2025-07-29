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

    def handle(self, *args, **options):
        name = options['name']
        domain_name = options['domain']
        schema_name = options.get('schema', name.lower().replace(' ', '_').replace('-', '_'))
        max_users = options['max_users']

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

                # Create domain
                domain = Domain.objects.create(
                    domain=domain_name,
                    tenant=tenant,
                    is_primary=True
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created tenant "{name}" with domain "{domain_name}"\n'
                        f'Schema: {schema_name}\n'
                        f'Max users: {max_users}'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error creating tenant: {str(e)}')