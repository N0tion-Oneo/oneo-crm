#!/usr/bin/env python
"""
Test the deletion fix for single-click behavior
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def test_deletion_fix():
    """Test that deletion now works with single click"""

    print('=== DELETION FIX TEST ===')
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

        print(f"📋 Job record: {job_record.id}")
        print(f"📋 Sales record: {sales_record.id}")
        print()

        # Get the relation field
        relation_field = Field.objects.get(pipeline=job_record.pipeline, slug='company_relation')
        handler = RelationFieldHandler(relation_field)

        # Set user context
        user = User.objects.filter(email='admin@oneo.com').first()
        print(f"👤 User: {user.email}")
        print()

        # STEP 1: Ensure we have an active relationship
        print("=== STEP 1: CREATE RELATIONSHIP ===")
        result = handler.set_relationships(job_record, [54], user)
        print(f"Create result: {result}")

        # Check current state
        active_rels = handler.get_relationships(job_record, include_deleted=False)
        all_rels = handler.get_relationships(job_record, include_deleted=True)
        print(f"Active relationships: {active_rels.count()}")
        print(f"All relationships: {all_rels.count()}")
        print()

        # STEP 2: Test single-click deletion
        print("=== STEP 2: SINGLE-CLICK DELETION TEST ===")
        print("Simulating frontend sending company_relation: []")

        # This should soft-delete all active relationships in ONE operation
        result = handler.set_relationships(job_record, [], user)
        print(f"Delete result: {result}")

        # Check if it worked
        active_rels_after = handler.get_relationships(job_record, include_deleted=False)
        all_rels_after = handler.get_relationships(job_record, include_deleted=True)
        print(f"Active relationships after: {active_rels_after.count()}")
        print(f"All relationships after: {all_rels_after.count()}")

        # Check display methods
        related_ids = handler.get_related_ids(job_record)
        related_records = handler.get_related_records_with_display(job_record)
        print(f"get_related_ids(): {related_ids}")
        print(f"get_related_records_with_display(): {related_records}")
        print()

        print("=== RESULT ANALYSIS ===")
        if result['removed'] > 0:
            print("✅ SUCCESS: Deletion worked in single operation")
            print(f"   - Removed {result['removed']} relationship(s)")
            if active_rels_after.count() == 0:
                print("✅ Display methods correctly show empty")
            else:
                print("❌ Display methods still show relationships")
        else:
            print("❌ FAILURE: No relationships were removed")
            print("   - This means the double-click issue persists")

        if all_rels_after.count() > active_rels_after.count():
            print("✅ Soft-delete working: All relationships > Active relationships")
        else:
            print("⚠️ No soft-deleted relationships found")

if __name__ == '__main__':
    test_deletion_fix()