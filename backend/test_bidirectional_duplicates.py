#!/usr/bin/env python
"""
Test to check if we're creating duplicate bidirectional relationship records
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

def test_bidirectional_duplicates(tenant_schema='oneotalent'):
    """Test if we're creating duplicate bidirectional relationships"""

    with schema_context(tenant_schema):
        try:
            print('=== BIDIRECTIONAL RELATIONSHIP DUPLICATE TEST ===')
            print()

            # Get the relation field and records
            relation_field = Field.objects.get(id=316)  # contacts field
            sales_record = Record.objects.get(id=516)  # Companies record
            job_app_record = Record.objects.get(id=518)  # Contacts record

            print(f"🔧 Relation field: {relation_field.slug} (ID: {relation_field.id})")
            print(f"📋 Sales Record: {sales_record.id} from pipeline {sales_record.pipeline.name}")
            print(f"📋 Contact Record: {job_app_record.id} from pipeline {job_app_record.pipeline.name}")
            print()

            # Clean up any existing relationships first
            print("🧹 Cleaning up existing relationships...")
            existing_rels = Relationship.objects.filter(
                source_record_id__in=[sales_record.id, job_app_record.id],
                target_record_id__in=[sales_record.id, job_app_record.id]
            )
            print(f"   Found {existing_rels.count()} existing relationships:")
            for rel in existing_rels:
                print(f"   🔗 {rel.id}: {rel.source_record_id} → {rel.target_record_id} (deleted: {rel.is_deleted})")
            existing_rels.delete()
            print("   ✅ Cleaned up")
            print()

            # Step 1: Create relationship and check for duplicates
            print('=== STEP 1: Create Relationship and Check for Duplicates ===')

            print(f"🔄 Setting {relation_field.slug} = [{job_app_record.id}] on record {sales_record.id}")
            sales_record.data = sales_record.data or {}
            sales_record.data[relation_field.slug] = [job_app_record.id]
            sales_record.save()
            print("✅ Record saved")
            print()

            # Check how many relationships were created
            print("🔍 Checking created relationships...")
            all_relationships = Relationship.objects.filter(
                source_record_id__in=[sales_record.id, job_app_record.id],
                target_record_id__in=[sales_record.id, job_app_record.id]
            ).order_by('id')

            print(f"📊 Total relationships found: {all_relationships.count()}")
            for rel in all_relationships:
                print(f"   🔗 Relationship {rel.id}:")
                print(f"      📍 Direction: {rel.source_record_id} → {rel.target_record_id}")
                print(f"      🏗️ Pipelines: {rel.source_pipeline_id} → {rel.target_pipeline_id}")
                print(f"      🔄 Type: {rel.relationship_type.slug} (bidirectional: {rel.relationship_type.is_bidirectional})")
                print(f"      🗑️ Deleted: {rel.is_deleted}")
                print()

            # Check for problematic patterns
            active_relationships = all_relationships.filter(is_deleted=False)
            if active_relationships.count() > 1:
                print(f"⚠️ WARNING: Found {active_relationships.count()} active relationships - this suggests duplicates!")

                # Check if they're actually duplicates (same records, different directions)
                forward_rel = active_relationships.filter(
                    source_record_id=sales_record.id,
                    target_record_id=job_app_record.id
                ).first()
                reverse_rel = active_relationships.filter(
                    source_record_id=job_app_record.id,
                    target_record_id=sales_record.id
                ).first()

                if forward_rel and reverse_rel:
                    print("❌ DUPLICATE DETECTED: Found both forward and reverse relationship records!")
                    print(f"   📤 Forward: {forward_rel.id} ({forward_rel.source_record_id} → {forward_rel.target_record_id})")
                    print(f"   📥 Reverse: {reverse_rel.id} ({reverse_rel.source_record_id} → {reverse_rel.target_record_id})")
                else:
                    print("✅ No forward/reverse duplicates found")
            else:
                print(f"✅ Correct: Found exactly {active_relationships.count()} active relationship(s)")

            print()

            # Test the RelationFieldHandler to see what it returns
            print("🔧 Testing RelationFieldHandler display values...")
            from pipelines.relation_field_handler import RelationFieldHandler

            handler = RelationFieldHandler(relation_field)
            related_records = handler.get_related_records_with_display(sales_record)
            print(f"📊 Display records returned: {related_records}")

            if isinstance(related_records, list) and len(related_records) > 1:
                print(f"⚠️ WARNING: Handler returned {len(related_records)} records - this might cause UI issues!")
                for i, record in enumerate(related_records):
                    print(f"   📋 Record {i+1}: {record}")
            elif related_records:
                print("✅ Handler returned single record correctly")
            else:
                print("❌ Handler returned no records")

            print()
            print('=== DUPLICATE ANALYSIS COMPLETE ===')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_bidirectional_duplicates()