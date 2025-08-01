"""
Management command to add a new tenant domain.
Usage: python manage.py add_tenant_domain <domain> <tenant_name>
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from tenants.models import Tenant, Domain


class Command(BaseCommand):
    help = 'Add a new tenant with domain'

    def add_arguments(self, parser):
        parser.add_argument('domain', type=str, help='Domain name (e.g., client.localhost)')
        parser.add_argument('name', type=str, help='Tenant name (e.g., "Client Company")')
        parser.add_argument(
            '--schema',
            type=str,
            help='Schema name (defaults to domain without TLD)',
            default=None
        )

    def handle(self, *args, **options):
        domain = options['domain']
        name = options['name']
        schema_name = options['schema'] or domain.split('.')[0]

        try:
            with transaction.atomic():
                # Create tenant
                tenant = Tenant.objects.create(
                    schema_name=schema_name,
                    name=name
                )
                
                # Create domain
                Domain.objects.create(
                    domain=domain,
                    tenant=tenant,
                    is_primary=True
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created tenant "{name}" with domain "{domain}" '
                        f'and schema "{schema_name}"'
                    )
                )
                
        except Exception as e:
            raise CommandError(f'Error creating tenant: {e}')