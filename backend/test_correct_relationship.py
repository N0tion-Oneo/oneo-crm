#!/usr/bin/env python
"""
Test relationship display with the CORRECT related records
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Field, Record
from pipelines.relation_field_handler import RelationFieldHandler

def test_correct_relationship(tenant_schema='oneotalent'):
    """Test relationship display with the correct related records"""

    with schema_context(tenant_schema):
        try:
            # Get the relationship fields
            sales_field = Field.objects.get(id=5)  # Sales -> Job Apps
            job_apps_field = Field.objects.get(id=66)  # Job Apps -> Sales

            # Get the CORRECT related records from our debugging
            sales_record = Record.objects.get(id=54)  # Sales record
            job_app_record = Record.objects.get(id=46)  # The RELATED Job App record

            print('=== TESTING WITH CORRECT RELATED RECORDS ===')
            print()
            print(f'Sales Record (ID: {sales_record.id}): {sales_record.data.get("company_name")}')
            print(f'Job App Record (ID: {job_app_record.id}): {job_app_record.data.get("validation_test_field")}')

            print()
            print('=== TESTING SALES FIELD (Sales -> Job Apps) ===')
            sales_handler = RelationFieldHandler(sales_field)
            print(f'Sales field display_field config: "{sales_handler.display_field}"')
            sales_related = sales_handler.get_related_records_with_display(sales_record)
            print(f'Sales record sees related records: {sales_related}')

            print()
            print('=== TESTING JOB APPS FIELD (Job Apps -> Sales) ===')
            job_apps_handler = RelationFieldHandler(job_apps_field)
            print(f'Job Apps field display_field config: "{job_apps_handler.display_field}"')
            job_apps_related = job_apps_handler.get_related_records_with_display(job_app_record)
            print(f'Job Apps record sees related records: {job_apps_related}')

            print()
            print('=== SUMMARY ===')
            if sales_related and job_apps_related:
                print('✅ Both sides showing display values correctly!')
                print(f'Sales → Job Apps: {sales_related[0]["display_value"]}')
                print(f'Job Apps → Sales: {job_apps_related[0]["display_value"]}')
            elif sales_related and not job_apps_related:
                print('⚠️ Only Sales side showing display values')
            elif not sales_related and job_apps_related:
                print('⚠️ Only Job Apps side showing display values')
            else:
                print('❌ Neither side showing display values')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_correct_relationship('oneotalent')