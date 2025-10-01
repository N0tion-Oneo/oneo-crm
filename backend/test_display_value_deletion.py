#!/usr/bin/env python
"""
Test to reproduce and fix the display value issue during relationship deletion
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
from pipelines.relation_field_handler import RelationFieldHandler
from api.serializers import RecordSerializer

def test_display_value_during_deletion(tenant_schema='oneotalent'):
    """Test display value generation during relationship deletion"""

    with schema_context(tenant_schema):
        try:
            print('=== DISPLAY VALUE DELETION TEST ===')
            print()

            # Use our known working test data
            relation_field = Field.objects.get(id=316)  # contacts field
            sales_record = Record.objects.get(id=516)  # Companies record
            job_app_record = Record.objects.get(id=518)  # Contacts record

            print(f"📋 Using relation field: {relation_field.slug} (ID: {relation_field.id})")
            print(f"📋 Display field configured: {relation_field.field_config.get('display_field', 'title')}")
            print(f"📋 Sales Record: {sales_record.id} (pipeline {sales_record.pipeline.name})")
            print(f"📋 Contact Record: {job_app_record.id} (pipeline {job_app_record.pipeline.name})")
            print(f"📋 Contact Record Data: {job_app_record.data}")
            print()

            # Clean up existing relationships
            existing_rels = Relationship.objects.filter(
                source_record_id__in=[sales_record.id, job_app_record.id],
                target_record_id__in=[sales_record.id, job_app_record.id]
            )
            if existing_rels.exists():
                print(f"🧹 Cleaning up {existing_rels.count()} existing relationships")
                existing_rels.delete()

            # Step 1: Create relationship and check display value
            print('=== STEP 1: Create Relationship and Check Display ===')

            sales_record.data = sales_record.data or {}
            sales_record.data[relation_field.slug] = [job_app_record.id]
            sales_record.save()

            # Test serialization BEFORE deletion
            print("📊 Testing serialization BEFORE deletion:")
            serializer = RecordSerializer(sales_record)
            serialized_data = serializer.to_representation(sales_record)
            relation_data = serialized_data.get('data', {}).get(relation_field.slug)
            print(f"   Relation field data: {relation_data}")

            # Test RelationFieldHandler directly
            print("🔧 Testing RelationFieldHandler directly:")
            handler = RelationFieldHandler(relation_field)
            display_records = handler.get_related_records_with_display(sales_record)
            print(f"   Display records: {display_records}")
            print()

            # Step 2: Remove relationship and check display value during the process
            print('=== STEP 2: Remove Relationship and Track Display Values ===')

            # Set relationship to empty list (this triggers deletion)
            print("🗑️ Setting relation field to empty list...")
            sales_record.data[relation_field.slug] = []

            # Test display value BEFORE saving (relationship still exists)
            print("📊 Testing display value BEFORE saving (relationship still exists):")
            handler = RelationFieldHandler(relation_field)
            display_records_before = handler.get_related_records_with_display(sales_record)
            print(f"   Display records before save: {display_records_before}")

            # Now save (this will trigger soft deletion)
            sales_record.save()
            print("✅ Record saved - relationship should be soft deleted")

            # Test display value AFTER saving (relationship is soft deleted)
            print("📊 Testing display value AFTER saving (relationship soft deleted):")
            display_records_after = handler.get_related_records_with_display(sales_record)
            print(f"   Display records after save: {display_records_after}")

            # Test full serialization AFTER deletion
            print("📊 Testing full serialization AFTER deletion:")
            serializer = RecordSerializer(sales_record)
            serialized_data_after = serializer.to_representation(sales_record)
            relation_data_after = serialized_data_after.get('data', {}).get(relation_field.slug)
            print(f"   Relation field data after deletion: {relation_data_after}")
            print()

            # Step 3: Check what happens to the target record's data
            print('=== STEP 3: Analyze Target Record Data ===')

            # Refresh the target record to see if data changed
            job_app_record.refresh_from_db()
            print(f"📋 Target record data after deletion: {job_app_record.data}")

            # Check specifically for the display field
            display_field_name = relation_field.field_config.get('display_field', 'title')
            print(f"📋 Display field '{display_field_name}': {job_app_record.data.get(display_field_name)}")

            # Check alternative field names
            alt_field = display_field_name.lower().replace(' ', '_')
            print(f"📋 Alternative field '{alt_field}': {job_app_record.data.get(alt_field)}")

            # Check title fallback
            print(f"📋 Record title: {job_app_record.title}")
            print()

            # Step 4: Test manual display value generation
            print('=== STEP 4: Manual Display Value Generation ===')

            try:
                target_record = Record.objects.get(
                    id=job_app_record.id,
                    pipeline_id=relation_field.field_config.get('target_pipeline_id'),
                    is_deleted=False
                )

                display_value = target_record.data.get(display_field_name)
                print(f"   Direct display value: {display_value}")

                if not display_value:
                    alt_field = display_field_name.lower().replace(' ', '_')
                    display_value = target_record.data.get(alt_field)
                    print(f"   Alternative field value: {display_value}")

                if not display_value:
                    display_value = target_record.title or f"Record #{target_record.id}"
                    print(f"   Final fallback value: {display_value}")

            except Record.DoesNotExist:
                print("   ❌ Target record not found")

            print()
            print('=== ANALYSIS COMPLETE ===')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_display_value_during_deletion()