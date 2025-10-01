#!/usr/bin/env python
"""
Test to verify that soft-deleted relationships are excluded from display but included for resurrection
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def test_display_fix():
    """Test that display methods exclude soft-deleted but resurrection includes them"""

    print('=== RELATIONSHIP DISPLAY FIX VERIFICATION ===')
    print()

    with schema_context('oneotalent'):
        from pipelines.models import Record, Field
        from relationships.models import Relationship
        from pipelines.relation_field_handler import RelationFieldHandler
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Get test records
        job_record = Record.objects.get(id=45)    # Job Applications

        print(f"📋 Job record: {job_record.id} - {job_record.data.get('vanessas_text_field', 'No field')}")
        print()

        # Get the relation field
        relation_field = Field.objects.get(pipeline=job_record.pipeline, slug='company_relation')
        handler = RelationFieldHandler(relation_field)

        print(f"🔗 Testing RelationFieldHandler for field: {relation_field.slug}")
        print(f"   Relationship type ID: {handler.relationship_type.id}")
        print()

        # Test 1: Internal query (includes soft-deleted)
        internal_relationships = handler.get_relationships(job_record, include_deleted=True)
        print(f"🔧 Internal query (include_deleted=True): {internal_relationships.count()} relationships")
        for rel in internal_relationships:
            deleted_status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({deleted_status})")
        print()

        # Test 2: Display query (excludes soft-deleted)
        display_relationships = handler.get_relationships(job_record, include_deleted=False)
        print(f"🎨 Display query (include_deleted=False): {display_relationships.count()} relationships")
        for rel in display_relationships:
            deleted_status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({deleted_status})")
        print()

        # Test 3: get_related_ids (used by serializers)
        related_ids = handler.get_related_ids(job_record)
        print(f"📊 get_related_ids() result: {related_ids}")
        print()

        # Test 4: get_related_records_with_display (used by API)
        display_records = handler.get_related_records_with_display(job_record)
        print(f"🔍 get_related_records_with_display() result: {display_records}")
        print()

        print("=== EXPECTED BEHAVIOR ===")
        print("✅ Internal query should include soft-deleted relationships (for resurrection)")
        print("✅ Display query should exclude soft-deleted relationships (clean UI)")
        print("✅ get_related_ids should only return IDs of active relationships")
        print("✅ get_related_records_with_display should only show active relationships")
        print()

        print("=== CONCLUSION ===")
        if internal_relationships.count() > display_relationships.count():
            print("✅ DISPLAY FIX IS WORKING")
            print("   - Internal operations see soft-deleted relationships")
            print("   - Display operations hide soft-deleted relationships")
            print("   - Users should now see clean relationship lists")
        elif internal_relationships.count() == 0 and display_relationships.count() == 0:
            print("ℹ️  NO RELATIONSHIPS TO TEST")
            print("   - Add some relationships to test the functionality")
        else:
            print("❌ DISPLAY FIX MAY NOT BE WORKING")
            print("   - Both queries return the same count")

if __name__ == '__main__':
    test_display_fix()