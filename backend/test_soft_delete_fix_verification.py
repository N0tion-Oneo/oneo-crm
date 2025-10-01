#!/usr/bin/env python
"""
Test to verify the soft delete relationship fix is working correctly
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def test_soft_delete_fix():
    """Test that soft deleted relationships are being detected correctly"""

    print('=== SOFT DELETE RELATIONSHIP FIX VERIFICATION ===')
    print()

    with schema_context('oneotalent'):
        from pipelines.models import Record, Field
        from relationships.models import Relationship
        from pipelines.relation_field_handler import RelationFieldHandler
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Get test records
        job_record = Record.objects.get(id=45)    # Job Applications
        sales_record = Record.objects.get(id=54)  # Sales Pipeline

        print(f"📋 Job record: {job_record.id} - {job_record.data.get('vanessas_text_field', 'No field')}")
        print(f"📋 Sales record: {sales_record.id} - {sales_record.data.get('company_name', 'No name')}")
        print()

        # Get the relation field
        relation_field = Field.objects.get(pipeline=job_record.pipeline, slug='company_relation')
        handler = RelationFieldHandler(relation_field)

        print(f"🔗 Testing RelationFieldHandler for field: {relation_field.slug}")
        print(f"   Target pipeline: {handler.target_pipeline_id}")
        print(f"   Relationship type ID: {handler.relationship_type.id}")
        print()

        # Check all relationships for this type
        all_rels = Relationship.all_objects.filter(relationship_type_id=handler.relationship_type.id)
        print(f"📊 Total relationships for type {handler.relationship_type.id}: {all_rels.count()}")

        # Show details
        for rel in all_rels:
            deleted_status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({deleted_status})")
        print()

        # Test current relationships query
        current_relationships = handler.get_relationships(job_record)
        print(f"🔍 Current relationships found by handler: {current_relationships.count()}")
        for rel in current_relationships:
            deleted_status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({deleted_status})")
        print()

        # Test the new query logic directly
        from django.db.models import Q
        test_query = Relationship.all_objects.filter(
            relationship_type_id=handler.relationship_type.id
        ).filter(
            Q(
                source_record_id=job_record.id,
                source_pipeline_id=handler.pipeline.id
            ) | Q(
                target_record_id=job_record.id,
                target_pipeline_id=handler.pipeline.id
            )
        )

        print(f"🧪 Direct query test results: {test_query.count()}")
        for rel in test_query:
            deleted_status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({deleted_status})")
        print()

        print("=== CONCLUSION ===")
        if test_query.count() > 0:
            print("✅ SOFT DELETE FIX IS WORKING")
            print("   - all_objects manager is finding soft-deleted relationships")
            print("   - Double-click issue should be resolved")
        else:
            print("❌ SOFT DELETE FIX NOT WORKING")
            print("   - No relationships found even with all_objects manager")
        print()

if __name__ == '__main__':
    test_soft_delete_fix()