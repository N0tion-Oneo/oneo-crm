#!/usr/bin/env python
"""
Check what fields are available in each pipeline for proper display field configuration
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field

def check_available_fields(tenant_schema='oneotalent'):
    """Check available fields in each pipeline"""

    with schema_context(tenant_schema):
        try:
            # Get the pipelines
            sales_pipeline = Pipeline.objects.get(id=1)  # Sales Pipeline
            job_apps_pipeline = Pipeline.objects.get(id=2)  # Job Applications

            print('=== AVAILABLE FIELDS FOR DISPLAY CONFIGURATION ===')
            print()

            print(f'Sales Pipeline (ID: {sales_pipeline.id}) - "{sales_pipeline.name}":')
            sales_fields = Field.objects.filter(pipeline=sales_pipeline, is_deleted=False).order_by('name')
            for field in sales_fields:
                print(f'  - {field.name} (slug: {field.slug}, type: {field.field_type})')

            print()
            print(f'Job Applications Pipeline (ID: {job_apps_pipeline.id}) - "{job_apps_pipeline.name}":')
            job_fields = Field.objects.filter(pipeline=job_apps_pipeline, is_deleted=False).order_by('name')
            for field in job_fields:
                print(f'  - {field.name} (slug: {field.slug}, type: {field.field_type})')

            print()
            print('=== CURRENT RELATIONSHIP FIELD CONFIGURATIONS ===')
            print()

            sales_rel_field = Field.objects.get(id=5)
            job_apps_rel_field = Field.objects.get(id=66)

            print(f'Sales field "{sales_rel_field.name}" points to Job Applications:')
            print(f'  - Currently configured to show: "{sales_rel_field.field_config.get("display_field")}"')
            print(f'  - Should probably show one of these Job Application fields instead')

            print()
            print(f'Job Apps field "{job_apps_rel_field.name}" points to Sales:')
            print(f'  - Currently configured to show: "{job_apps_rel_field.field_config.get("display_field")}"')
            print(f'  - Should probably show one of these Sales fields instead')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    check_available_fields('oneotalent')