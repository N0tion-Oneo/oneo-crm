#!/usr/bin/env python
"""
Quick check for relationship field display configurations
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Field

def check_display_configs(tenant_schema='oneotalent'):
    """Check field display configurations"""

    with schema_context(tenant_schema):
        try:
            # Get the two relationship fields
            sales_field = Field.objects.get(id=5)
            job_apps_field = Field.objects.get(id=66)

            print('=== RELATIONSHIP FIELD DISPLAY CONFIGURATIONS ===')
            print()
            print(f'Sales field: {sales_field.name} (ID: {sales_field.id})')
            print(f'  - display_field: {sales_field.field_config.get("display_field", "title")}')
            print(f'  - target_pipeline_id: {sales_field.field_config.get("target_pipeline_id")}')
            print(f'  - full config: {sales_field.field_config}')

            print()
            print(f'Job Apps field: {job_apps_field.name} (ID: {job_apps_field.id})')
            print(f'  - display_field: {job_apps_field.field_config.get("display_field", "title")}')
            print(f'  - target_pipeline_id: {job_apps_field.field_config.get("target_pipeline_id")}')
            print(f'  - full config: {job_apps_field.field_config}')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    check_display_configs('oneotalent')