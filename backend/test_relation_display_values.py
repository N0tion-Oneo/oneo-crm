#!/usr/bin/env python
"""
Test that relation fields include display values in API responses.
"""
import os
import django
import sys
import json

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record
from relationships.models import Relationship
from api.serializers import RecordSerializer, DynamicRecordSerializer


def test_relation_display_values(tenant_schema='oneotalent'):
    """Test that relation fields return display values in API responses"""

    print(f"\n{'='*80}")
    print(f"🧪 TESTING RELATION FIELD DISPLAY VALUES")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        # Get record 46 (Companies pipeline)
        record = Record.objects.get(id=46)
        print(f"📌 Testing with Record {record.id}: {record.title}")
        print(f"   Pipeline: {record.pipeline.name}")

        # Check for relation fields
        relation_fields = record.pipeline.fields.filter(field_type='relation')
        print(f"\n📊 Found {relation_fields.count()} relation fields:")
        for field in relation_fields:
            print(f"   - {field.name} ({field.slug})")
            config = field.field_config or {}
            target_pipeline_id = config.get('target_pipeline')
            display_field = config.get('display_field', 'title')
            print(f"     Target: Pipeline {target_pipeline_id}, Display: {display_field}")

        # Get relationships for this record
        print(f"\n🔗 Checking relationships:")
        relationships = Relationship.objects.filter(
            source_record_id=record.id
        ) | Relationship.objects.filter(
            target_record_id=record.id
        )

        for rel in relationships:
            print(f"   - Relationship {rel.id}: {rel.source_record_id} -> {rel.target_record_id}")
            print(f"     Type: {rel.relationship_type}")

        # Test serialization with both serializers
        print(f"\n📦 Testing serializers:")

        # Test RecordSerializer
        print(f"\n1. RecordSerializer:")
        serializer = RecordSerializer(record)
        data = serializer.data

        # Check for relation field data
        for field in relation_fields:
            field_data = data.get(field.slug)
            print(f"   {field.slug}: {field_data}")
            if field_data:
                if isinstance(field_data, list):
                    for item in field_data:
                        if isinstance(item, dict) and 'display_value' in item:
                            print(f"      ✅ Has display_value: {item['display_value']}")
                        else:
                            print(f"      ❌ Missing display_value: {item}")
                elif isinstance(field_data, dict) and 'display_value' in field_data:
                    print(f"      ✅ Has display_value: {field_data['display_value']}")
                else:
                    print(f"      ❌ Missing display_value: {field_data}")

        # Test DynamicRecordSerializer
        print(f"\n2. DynamicRecordSerializer:")
        dynamic_serializer = DynamicRecordSerializer(record, context={'pipeline': record.pipeline})
        dynamic_data = dynamic_serializer.data

        for field in relation_fields:
            field_data = dynamic_data.get(field.slug)
            print(f"   {field.slug}: {field_data}")
            if field_data:
                if isinstance(field_data, list):
                    for item in field_data:
                        if isinstance(item, dict) and 'display_value' in item:
                            print(f"      ✅ Has display_value: {item['display_value']}")
                        else:
                            print(f"      ❌ Missing display_value: {item}")
                elif isinstance(field_data, dict) and 'display_value' in field_data:
                    print(f"      ✅ Has display_value: {field_data['display_value']}")
                else:
                    print(f"      ❌ Missing display_value: {field_data}")

        # Output full JSON for debugging
        print(f"\n📄 Full serialized data (RecordSerializer):")
        print(json.dumps(data, indent=2, default=str))

        print(f"\n{'='*80}")
        print(f"✅ TEST COMPLETE")
        print(f"{'='*80}")


if __name__ == '__main__':
    test_relation_display_values('oneotalent')