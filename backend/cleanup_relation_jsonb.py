#!/usr/bin/env python
"""
Clean up relation field data from JSONB storage.
Removes any relation field data that's incorrectly stored in JSONB
instead of the Relationship table.
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record
from django.db import transaction
import json


def cleanup_relation_fields(tenant_schema='oneotalent'):
    """Remove relation field data from JSONB for all records"""

    print(f"\n{'='*80}")
    print(f"🧹 CLEANING UP RELATION FIELDS FROM JSONB")
    print(f"{'='*80}")

    with schema_context(tenant_schema):
        # Get all relation fields
        relation_fields = Field.objects.filter(field_type='relation')
        print(f"\n📊 Found {relation_fields.count()} relation fields to clean up")

        # Group by pipeline for efficiency
        pipelines_with_relations = {}
        for field in relation_fields:
            if field.pipeline_id not in pipelines_with_relations:
                pipelines_with_relations[field.pipeline_id] = []
            pipelines_with_relations[field.pipeline_id].append(field.slug)

        total_cleaned = 0

        for pipeline_id, field_slugs in pipelines_with_relations.items():
            pipeline = Pipeline.objects.get(id=pipeline_id)
            print(f"\n🔧 Processing pipeline: {pipeline.name} (ID: {pipeline_id})")
            print(f"   Fields to remove: {field_slugs}")

            # Get all records for this pipeline
            records = Record.objects.filter(pipeline_id=pipeline_id, is_deleted=False)
            print(f"   Found {records.count()} records to check")

            cleaned_count = 0

            with transaction.atomic():
                for record in records:
                    modified = False
                    original_data = record.data.copy() if record.data else {}

                    # Remove each relation field from JSONB
                    for field_slug in field_slugs:
                        if field_slug in record.data:
                            value = record.data.pop(field_slug)
                            print(f"      - Record {record.id}: Removing '{field_slug}' = {value}")
                            modified = True

                    # Save if modified
                    if modified:
                        # Direct database update to avoid triggering save logic
                        Record.objects.filter(id=record.id).update(data=record.data)
                        cleaned_count += 1

            print(f"   ✅ Cleaned {cleaned_count} records in {pipeline.name}")
            total_cleaned += cleaned_count

        print(f"\n{'='*80}")
        print(f"✅ CLEANUP COMPLETE: Removed relation data from {total_cleaned} records")
        print(f"{'='*80}")

        # Verify cleanup
        print(f"\n🔍 Verification:")
        for pipeline_id, field_slugs in pipelines_with_relations.items():
            pipeline = Pipeline.objects.get(id=pipeline_id)

            # Check if any records still have relation fields in JSONB
            for field_slug in field_slugs:
                # Use raw SQL to check JSONB keys
                records_with_field = Record.objects.filter(
                    pipeline_id=pipeline_id,
                    is_deleted=False
                ).extra(where=[f"data ? %s"], params=[field_slug])

                if records_with_field.exists():
                    print(f"   ⚠️  {pipeline.name}: {records_with_field.count()} records still have '{field_slug}' in JSONB")
                else:
                    print(f"   ✅ {pipeline.name}: No records have '{field_slug}' in JSONB")


if __name__ == '__main__':
    # Clean up for oneotalent tenant
    cleanup_relation_fields('oneotalent')

    # You can add other tenants here if needed
    # cleanup_relation_fields('other_tenant')