#!/usr/bin/env python
"""
Debug the company_name field issue
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record

def debug_company_name(tenant_schema='oneotalent'):
    """Debug company_name field issue"""

    with schema_context(tenant_schema):
        try:
            # Get the sales record that should be related
            sales_record = Record.objects.filter(pipeline_id=1, is_deleted=False).first()

            print('=== SALES RECORD COMPANY NAME DEBUG ===')
            print()
            print(f'Sales Record (ID: {sales_record.id}):')
            print(f'  Data: {sales_record.data}')
            print()
            print('Checking for company name fields:')
            print(f'  "Company Name": {sales_record.data.get("Company Name")}')
            print(f'  "company_name": {sales_record.data.get("company_name")}')
            print(f'  "company Name": {sales_record.data.get("company Name")}')
            print(f'  "Company name": {sales_record.data.get("Company name")}')

            # Also test the conversion logic
            display_field = "Company Name"
            alt_field = display_field.lower().replace(' ', '_')
            print()
            print(f'Display field: "{display_field}"')
            print(f'Alt field: "{alt_field}"')
            print(f'Value from display_field: {sales_record.data.get(display_field)}')
            print(f'Value from alt_field: {sales_record.data.get(alt_field)}')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_company_name('oneotalent')