#!/usr/bin/env python
"""
Debug the relationship query to see why get_bidirectional_relationships returns empty
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def debug_relationship_query():
    """Debug why the relationship query returns empty"""

    print('=== RELATIONSHIP QUERY DEBUG ===')
    print()

    with schema_context('oneotalent'):
        from pipelines.models import Record, Field
        from relationships.models import Relationship
        from pipelines.relation_field_handler import RelationFieldHandler

        # Get test records
        sales_record = Record.objects.get(id=54)  # Sales Pipeline
        job_record = Record.objects.get(id=45)    # Job Applications

        print(f"📋 Sales record: {sales_record.id} in pipeline {sales_record.pipeline.id} ({sales_record.pipeline.name})")
        print(f"📋 Job record: {job_record.id} in pipeline {job_record.pipeline.id} ({job_record.pipeline.name})")
        print()

        # Get the relation field from Job Applications
        relation_field = Field.objects.get(pipeline=job_record.pipeline, slug='company_relation')
        print(f"🔗 Relation field: {relation_field.slug} (ID: {relation_field.id})")
        print(f"   Pipeline: {relation_field.pipeline.id} ({relation_field.pipeline.name})")
        print(f"   Config: {relation_field.field_config}")
        print()

        # Check what relationships exist
        print("=== ALL RELATIONSHIPS FOR THESE RECORDS ===")
        all_rels = Relationship.objects.filter(
            source_record_id__in=[sales_record.id, job_record.id],
            target_record_id__in=[sales_record.id, job_record.id],
            is_deleted=False
        )
        print(f"Found {all_rels.count()} relationships:")
        for rel in all_rels:
            print(f"   Relationship {rel.id}:")
            print(f"      📍 {rel.source_record_id} (pipeline {rel.source_pipeline_id}) → {rel.target_record_id} (pipeline {rel.target_pipeline_id})")
            print(f"      🔗 Type: {rel.relationship_type_id} ({rel.relationship_type.slug})")
            print()

        # Test the RelationFieldHandler query
        print("=== TESTING RelationFieldHandler ===")
        handler = RelationFieldHandler(relation_field)

        print(f"Handler config:")
        print(f"   Pipeline: {handler.pipeline.id} ({handler.pipeline.name})")
        print(f"   Target pipeline: {handler.target_pipeline_id}")
        print(f"   RelationshipType: {handler.relationship_type.id} ({handler.relationship_type.slug})")
        print()

        # Test the get_relationships query for job record
        print(f"Testing get_relationships for job record {job_record.id}:")
        relationships = handler.get_relationships(job_record)
        print(f"   Found {relationships.count()} relationships")
        for rel in relationships:
            print(f"   - {rel.id}: {rel.source_record_id} → {rel.target_record_id}")

        # Test the manual query to see what's different
        print(f"\nManual query for job record {job_record.id}:")
        from django.db.models import Q
        manual_rels = Relationship.objects.filter(
            Q(
                source_record_id=job_record.id,
                source_pipeline_id=handler.pipeline.id,
                relationship_type_id=handler.relationship_type.id
            ) | Q(
                target_record_id=job_record.id,
                target_pipeline_id=handler.pipeline.id,
                relationship_type_id=handler.relationship_type.id
            ),
            is_deleted=False
        )
        print(f"   Manual query found {manual_rels.count()} relationships")
        for rel in manual_rels:
            print(f"   - {rel.id}: {rel.source_record_id} (pipeline {rel.source_pipeline_id}) → {rel.target_record_id} (pipeline {rel.target_pipeline_id})")

        # Test the get_related_ids method
        print(f"\nTesting get_related_ids:")
        related_ids = handler.get_related_ids(job_record)
        print(f"   Related IDs: {related_ids}")

if __name__ == '__main__':
    debug_relationship_query()