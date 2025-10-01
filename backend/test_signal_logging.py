#!/usr/bin/env python
"""
Test script to verify signal logging is working for relationship updates
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Field, Record, Pipeline
from relationships.models import Relationship

def test_signal_logging(tenant_schema='oneotalent'):
    """Test that signals fire with enhanced logging"""

    with schema_context(tenant_schema):
        try:
            print('=== SIGNAL LOGGING TEST ===')
            print()

            # Get a relationship field
            relation_field = Field.objects.filter(field_type='relation', is_deleted=False).first()
            if not relation_field:
                print("❌ No relation fields found")
                return

            print(f"📋 Using relation field: {relation_field.slug} (ID: {relation_field.id})")
            print(f"   📍 Source pipeline: {relation_field.pipeline.name}")
            print(f"   🎯 Target pipeline ID: {relation_field.field_config.get('target_pipeline_id')}")

            # Get a record from the source pipeline
            source_record = Record.objects.filter(
                pipeline_id=relation_field.pipeline_id,
                is_deleted=False
            ).first()

            if not source_record:
                print("❌ No source records found")
                return

            # Get a record from the target pipeline
            target_pipeline_id = relation_field.field_config.get('target_pipeline_id')
            target_record = Record.objects.filter(
                pipeline_id=target_pipeline_id,
                is_deleted=False
            ).first()

            if not target_record:
                print("❌ No target records found")
                return

            print(f"📋 Source Record: {source_record.id} ({source_record.data.get('title', 'No title')})")
            print(f"📋 Target Record: {target_record.id} ({target_record.data.get('title', 'No title')})")
            print()

            # Test 1: Add a relationship via relation field
            print('=== TEST 1: Adding Relationship via Field Update ===')
            print(f"🔄 Setting {relation_field.slug} = [{target_record.id}] on record {source_record.id}")

            # Update the record's relation field
            source_record.data = source_record.data or {}
            source_record.data[relation_field.slug] = [target_record.id]
            source_record.save()

            print()
            print('=== TEST 1 COMPLETE ===')
            print()

            # Test 2: Check existing relationships
            print('=== TEST 2: Checking Existing Relationships ===')
            relationships = Relationship.objects.filter(
                source_record_id__in=[source_record.id, target_record.id],
                target_record_id__in=[source_record.id, target_record.id],
                is_deleted=False
            )

            print(f"Found {relationships.count()} existing relationships:")
            for rel in relationships:
                print(f"   🔗 {rel.id}: {rel.source_record_id} → {rel.target_record_id}")

            print()
            print('=== SIGNAL LOGGING TEST COMPLETE ===')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_signal_logging()