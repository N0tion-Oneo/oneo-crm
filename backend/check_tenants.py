import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import get_public_schema_name
from tenants.models import Tenant, Domain

print('Public schema:', get_public_schema_name())

print('\nTenants:')
for t in Tenant.objects.all():
    print(f'  - {t.schema_name}: {t.name}')

print('\nDomains:')
for d in Domain.objects.all():
    print(f'  - {d.domain} -> {d.tenant.schema_name}')