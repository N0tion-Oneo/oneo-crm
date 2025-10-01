#!/usr/bin/env python
"""
Debug the entire relationship chain to find where the breakdown is happening
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def debug_full_chain():
    """Debug the entire relationship chain step by step"""

    print('=== FULL CHAIN DEBUG ==='  )
    print()

    with schema_context('oneotalent'):
        from pipelines.models import Record, Field
        from relationships.models import Relationship
        from pipelines.relation_field_handler import RelationFieldHandler
        from django.contrib.auth import get_user_model
        from django.db.models import Q
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

        print(f"🔗 Relation field: {relation_field.slug}")
        print(f"   Field ID: {relation_field.id}")
        print(f"   Pipeline: {relation_field.pipeline.id}")
        print(f"   Target pipeline: {handler.target_pipeline_id}")
        print(f"   Relationship type ID: {handler.relationship_type.id}")
        print()

        # STEP 1: Check what relationships exist in the database
        print("=== STEP 1: DATABASE RELATIONSHIP CHECK ===")

        # Check with both managers
        all_relationships = Relationship.all_objects.filter(relationship_type_id=handler.relationship_type.id)
        active_relationships = Relationship.objects.filter(relationship_type_id=handler.relationship_type.id)

        print(f"📊 Total relationships (all_objects): {all_relationships.count()}")
        print(f"📊 Active relationships (objects): {active_relationships.count()}")

        for rel in all_relationships:
            status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({status})")
        print()

        # STEP 2: Test handler.get_relationships() method
        print("=== STEP 2: HANDLER get_relationships() TEST ===")

        # Test with include_deleted=True (internal operations)
        internal_rels = handler.get_relationships(job_record, include_deleted=True)
        print(f"🔧 Internal query (include_deleted=True): {internal_rels.count()}")
        for rel in internal_rels:
            status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({status})")

        # Test with include_deleted=False (display operations)
        display_rels = handler.get_relationships(job_record, include_deleted=False)
        print(f"🎨 Display query (include_deleted=False): {display_rels.count()}")
        for rel in display_rels:
            status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({status})")
        print()

        # STEP 3: Test the exact query from set_relationships
        print("=== STEP 3: set_relationships() QUERY TEST ===")

        # This is the exact query from line 242-252 in set_relationships
        current_relationships = Relationship.all_objects.filter(
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

        print(f"🔧 set_relationships query result: {current_relationships.count()}")
        for rel in current_relationships:
            status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({status})")
        print()

        # STEP 4: Check the target IDs collection logic
        print("=== STEP 4: TARGET IDS COLLECTION TEST ===")

        current_target_ids = set()
        relationships_map = {}

        for rel in current_relationships:
            if rel.source_record_id == job_record.id:
                target_id = rel.target_record_id
            else:
                target_id = rel.source_record_id

            current_target_ids.add(target_id)
            relationships_map[target_id] = rel
            print(f"   - Found target ID: {target_id} from rel {rel.id}")

        print(f"📊 Current target IDs: {list(current_target_ids)}")
        print(f"📊 Relationships map: {list(relationships_map.keys())}")
        print()

        # STEP 5: Test what happens when we try to add [54]
        print("=== STEP 5: SIMULATE set_relationships([54]) ===")

        new_target_ids = {54}

        print(f"📊 Current target IDs: {list(current_target_ids)}")
        print(f"📊 New target IDs: {list(new_target_ids)}")

        to_remove = current_target_ids - new_target_ids
        to_add = new_target_ids - current_target_ids
        unchanged = new_target_ids & current_target_ids

        print(f"📊 To remove: {list(to_remove)}")
        print(f"📊 To add: {list(to_add)}")
        print(f"📊 Unchanged: {list(unchanged)}")
        print()

        # STEP 6: Check for existing relationship when trying to add
        print("=== STEP 6: CHECK FOR EXISTING RELATIONSHIP ===")

        if 54 in to_add:
            print(f"🔍 Checking for existing relationship to target {54}")

            # This is the exact query from line 307-321 in set_relationships
            existing = Relationship.all_objects.filter(
                relationship_type_id=handler.relationship_type.id
            ).filter(
                Q(
                    source_pipeline_id=handler.pipeline.id,
                    source_record_id=job_record.id,
                    target_pipeline_id=handler.target_pipeline_id,
                    target_record_id=54
                ) | Q(
                    source_pipeline_id=handler.target_pipeline_id,
                    source_record_id=54,
                    target_pipeline_id=handler.pipeline.id,
                    target_record_id=job_record.id
                )
            ).first()

            if existing:
                status = "DELETED" if existing.is_deleted else "ACTIVE"
                print(f"✅ Found existing relationship {existing.id}: {status}")
                print(f"   Source: {existing.source_pipeline_id}:{existing.source_record_id}")
                print(f"   Target: {existing.target_pipeline_id}:{existing.target_record_id}")

                if existing.is_deleted:
                    print("🔄 This should be resurrected!")
                else:
                    print("➡️ This should be marked as unchanged!")
            else:
                print("❌ No existing relationship found - this is the problem!")
                print("   This means the query isn't finding the soft-deleted relationship")
        print()

        # STEP 7: Manual verification - find all relationships between these records
        print("=== STEP 7: MANUAL VERIFICATION ===")

        manual_check = Relationship.all_objects.filter(
            Q(source_record_id=job_record.id, target_record_id=54) |
            Q(source_record_id=54, target_record_id=job_record.id)
        )

        print(f"🔍 Manual check - all relationships between records {job_record.id} and 54:")
        for rel in manual_check:
            status = "DELETED" if rel.is_deleted else "ACTIVE"
            print(f"   - Rel {rel.id}: type={rel.relationship_type_id}, {rel.source_pipeline_id}:{rel.source_record_id} → {rel.target_pipeline_id}:{rel.target_record_id} ({status})")

        print()
        print("=== ANALYSIS ===")
        print("If manual check finds relationships but STEP 6 doesn't,")
        print("then the issue is in the relationship_type_id or pipeline_id filtering.")
        print("If manual check finds nothing, then the relationships don't exist in the database.")

if __name__ == '__main__':
    debug_full_chain()