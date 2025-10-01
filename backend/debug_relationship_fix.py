#!/usr/bin/env python
"""
Debug the specific issue with RelationFieldHandler query logic
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def debug_relationship_fix():
    """Debug the specific RelationFieldHandler query issue"""

    print('=== RELATIONSHIP HANDLER QUERY DEBUG ===')
    print()

    with schema_context('oneotalent'):
        from pipelines.models import Record, Field
        from relationships.models import Relationship
        from pipelines.relation_field_handler import RelationFieldHandler
        from django.db.models import Q

        # Get test records
        sales_record = Record.objects.get(id=54)  # Sales Pipeline
        job_record = Record.objects.get(id=45)    # Job Applications

        print(f"📋 Sales record: {sales_record.id} in pipeline {sales_record.pipeline.id} ({sales_record.pipeline.name})")
        print(f"📋 Job record: {job_record.id} in pipeline {job_record.pipeline.id} ({job_record.pipeline.name})")
        print()

        # First, create a relationship manually to ensure one exists
        from relationships.models import RelationshipType
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(email='admin@oneo.com').first()

        relationship_type, created = RelationshipType.objects.get_or_create(
            slug='sales-pipeline_jobs_applied_for',
            defaults={
                'name': 'Sales Pipeline - Jobs Applied For',
                'is_bidirectional': True
            }
        )
        print(f"🔗 Relationship type: {relationship_type.slug} (created: {created})")

        # Create or restore relationship
        relationship, created = Relationship.objects.get_or_create(
            source_record_id=job_record.id,
            target_record_id=sales_record.id,
            source_pipeline_id=job_record.pipeline_id,
            target_pipeline_id=sales_record.pipeline_id,
            relationship_type=relationship_type,
            defaults={
                'created_by': user,
                'is_deleted': False
            }
        )

        # If relationship exists but is soft deleted, restore it
        if not created and relationship.is_deleted:
            relationship.is_deleted = False
            relationship.deleted_by = None
            relationship.deleted_at = None
            relationship.save()
            print("   Restored soft-deleted relationship")
        print(f"📦 Relationship: {relationship.id} ({'created' if created else 'existing'})")
        print(f"   Direction: {relationship.source_record_id} (pipeline {relationship.source_pipeline_id}) → {relationship.target_record_id} (pipeline {relationship.target_pipeline_id})")
        print()

        # Test current RelationFieldHandler logic
        relation_field = Field.objects.get(pipeline=job_record.pipeline, slug='company_relation')
        handler = RelationFieldHandler(relation_field)

        print(f"🔧 Handler config:")
        print(f"   Field pipeline: {handler.pipeline.id} ({handler.pipeline.name})")
        print(f"   Target pipeline: {handler.target_pipeline_id}")
        print(f"   RelationshipType: {handler.relationship_type.id} ({handler.relationship_type.slug})")
        print()

        # Test the current (broken) query
        print("=== CURRENT (BROKEN) QUERY ===")
        current_query = Relationship.objects.filter(
            Q(
                source_record_id=job_record.id,
                source_pipeline=handler.pipeline,  # THIS IS WRONG
                relationship_type=handler.relationship_type
            ) | Q(
                target_record_id=job_record.id,
                target_pipeline=handler.pipeline,  # THIS IS WRONG
                relationship_type=handler.relationship_type
            ),
            is_deleted=False
        )
        print(f"Current query found: {current_query.count()} relationships")
        for rel in current_query:
            print(f"   - {rel.id}: {rel.source_record_id} → {rel.target_record_id}")
        print()

        # Test the CORRECT query
        print("=== CORRECT QUERY ===")
        correct_query = Relationship.objects.filter(
            Q(
                source_record_id=job_record.id,
                source_pipeline_id=handler.pipeline.id,  # Use _id, not model
                relationship_type=handler.relationship_type
            ) | Q(
                target_record_id=job_record.id,
                target_pipeline_id=handler.pipeline.id,  # Use _id, not model
                relationship_type=handler.relationship_type
            ),
            is_deleted=False
        )
        print(f"Correct query found: {correct_query.count()} relationships")
        for rel in correct_query:
            print(f"   - {rel.id}: {rel.source_record_id} → {rel.target_record_id}")
        print()

        # Debug: Check what relationship types exist for our record
        print("=== RELATIONSHIP TYPE MISMATCH DEBUG ===")
        all_rels_for_record = Relationship.objects.filter(
            Q(source_record_id=job_record.id) | Q(target_record_id=job_record.id),
            is_deleted=False
        )
        print(f"All relationships for job record {job_record.id}:")
        for rel in all_rels_for_record:
            print(f"   - {rel.id}: {rel.source_record_id} → {rel.target_record_id}")
            print(f"     Type: {rel.relationship_type.id} ({rel.relationship_type.slug})")
            print(f"     Handler expects: {handler.relationship_type.id} ({handler.relationship_type.slug})")
            print(f"     Match: {rel.relationship_type.id == handler.relationship_type.id}")
        print()

        # Check if the relationship type created manually matches what the handler expects
        print("=== RELATIONSHIP TYPE COMPARISON ===")
        print(f"Created relationship type: {relationship_type.id} ({relationship_type.slug})")
        print(f"Handler relationship type: {handler.relationship_type.id} ({handler.relationship_type.slug})")
        print(f"Types match: {relationship_type.id == handler.relationship_type.id}")
        print()

        # Show relationship we just created/found
        print(f"=== CREATED RELATIONSHIP DETAILS ===")
        print(f"Relationship {relationship.id}:")
        print(f"   Direction: {relationship.source_record_id} → {relationship.target_record_id}")
        print(f"   Source pipeline: {relationship.source_pipeline_id}")
        print(f"   Target pipeline: {relationship.target_pipeline_id}")
        print(f"   Type: {relationship.relationship_type.id} ({relationship.relationship_type.slug})")
        print(f"   Deleted: {relationship.is_deleted}")
        print()

        # Test get_related_ids with fix
        print("=== TESTING get_related_ids WITH MANUAL FIX ===")
        relationships = correct_query
        related_ids = []
        for rel in relationships:
            if rel.source_record_id == job_record.id:
                related_ids.append(rel.target_record_id)
            else:
                related_ids.append(rel.source_record_id)

        print(f"Related IDs with fixed query: {related_ids}")
        print()

        print("=== EXPECTED RESULT ===")
        print(f"The WebSocket signal should broadcast:")
        print(f"  🔗 Field 'company_relation' has related IDs: {related_ids}")
        print(f"  Instead of: []")

if __name__ == '__main__':
    debug_relationship_fix()