#!/usr/bin/env python
"""
Debug actual relationships between records
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from django.db.models import Q
from pipelines.models import Record
from relationships.models import Relationship

def debug_relationships(tenant_schema='oneotalent'):
    """Debug actual relationships between records"""

    with schema_context(tenant_schema):
        try:
            # Get test records
            sales_record = Record.objects.filter(pipeline_id=1, is_deleted=False).first()
            job_app_record = Record.objects.filter(pipeline_id=2, is_deleted=False).first()

            print('=== RELATIONSHIP DEBUG ===')
            print()
            print(f'Sales Record: {sales_record.id} (pipeline {sales_record.pipeline_id})')
            print(f'Job App Record: {job_app_record.id} (pipeline {job_app_record.pipeline_id})')

            # Check for any relationships involving these records
            print()
            print('=== ALL RELATIONSHIPS ===')
            all_relationships = Relationship.objects.filter(is_deleted=False)

            for rel in all_relationships:
                print(f'Relationship {rel.id}: {rel.source_record_id} (pipeline {rel.source_pipeline_id}) → {rel.target_record_id} (pipeline {rel.target_pipeline_id})')
                print(f'  Type: {rel.relationship_type.slug}')

            # Check for relationships involving our specific records
            print()
            print('=== RELATIONSHIPS INVOLVING OUR RECORDS ===')
            our_relationships = Relationship.objects.filter(
                Q(source_record_id=sales_record.id) | Q(target_record_id=sales_record.id) |
                Q(source_record_id=job_app_record.id) | Q(target_record_id=job_app_record.id),
                is_deleted=False
            )

            if our_relationships.exists():
                for rel in our_relationships:
                    print(f'Found: {rel.source_record_id} → {rel.target_record_id} (type: {rel.relationship_type.slug})')
            else:
                print('No relationships found involving these records')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_relationships('oneotalent')