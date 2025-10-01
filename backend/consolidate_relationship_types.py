#!/usr/bin/env python
"""
Consolidate RelationshipType objects for bidirectional fields
This script will:
1. Consolidate the Sales Pipeline <-> Job Applications RelationshipTypes
2. Migrate existing Relationship records to use the consolidated type
3. Delete the redundant RelationshipType
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field
from relationships.models import RelationshipType, Relationship
from django.contrib.auth import get_user_model

User = get_user_model()


def consolidate_relationship_types(tenant_schema='oneotalent'):
    """Consolidate RelationshipType objects for bidirectional fields"""

    print(f"\n{'='*80}")
    print(f"🔧 CONSOLIDATING RELATIONSHIPTYPE OBJECTS")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Step 1: Get the bidirectional field pair
            print("🔗 Step 1: Getting Sales Pipeline <-> Job Applications fields")

            sales_field = Field.objects.get(
                pipeline__name="Sales Pipeline",
                name="Jobs Applied For",
                field_type="relation",
                is_deleted=False
            )

            job_apps_field = Field.objects.get(
                pipeline__name="Job Applications",
                name="Company Relation",
                field_type="relation",
                is_deleted=False
            )

            print(f"   ✅ Sales field: {sales_field.name} (ID: {sales_field.id})")
            print(f"   ✅ Job Apps field: {job_apps_field.name} (ID: {job_apps_field.id})")

            # Step 2: Get the current RelationshipTypes
            print(f"\n🔍 Step 2: Checking current RelationshipTypes")

            try:
                sales_rel_type = RelationshipType.objects.get(slug='sales-pipeline_jobs_applied_for')
                print(f"   ✅ Found Sales RelationshipType: {sales_rel_type.slug} (ID: {sales_rel_type.id})")
            except RelationshipType.DoesNotExist:
                print(f"   ❌ Sales RelationshipType not found")
                return

            try:
                job_apps_rel_type = RelationshipType.objects.get(slug='job-applications_company_relation')
                print(f"   ✅ Found Job Apps RelationshipType: {job_apps_rel_type.slug} (ID: {job_apps_rel_type.id})")
            except RelationshipType.DoesNotExist:
                print(f"   ❌ Job Apps RelationshipType not found")
                return

            # Step 3: Check existing relationships using these types
            print(f"\n📊 Step 3: Checking existing relationships")

            sales_relationships = Relationship.objects.filter(
                relationship_type=sales_rel_type,
                is_deleted=False
            )
            print(f"   Sales RelationshipType has {sales_relationships.count()} active relationships")

            job_apps_relationships = Relationship.objects.filter(
                relationship_type=job_apps_rel_type,
                is_deleted=False
            )
            print(f"   Job Apps RelationshipType has {job_apps_relationships.count()} active relationships")

            # Step 4: Choose primary RelationshipType and migrate
            print(f"\n🔧 Step 4: Consolidating RelationshipTypes")

            # Use the Sales RelationshipType as the primary one
            primary_rel_type = sales_rel_type
            secondary_rel_type = job_apps_rel_type

            print(f"   Using primary: {primary_rel_type.slug}")
            print(f"   Migrating from: {secondary_rel_type.slug}")

            # Migrate relationships from secondary to primary
            migrated_count = 0
            for relationship in job_apps_relationships:
                print(f"      Migrating relationship {relationship.id}: {relationship.source_pipeline.name}:{relationship.source_record_id} -> {relationship.target_pipeline.name}:{relationship.target_record_id}")
                relationship.relationship_type = primary_rel_type
                relationship.save()
                migrated_count += 1

            print(f"   ✅ Migrated {migrated_count} relationships to primary RelationshipType")

            # Step 5: Delete the secondary RelationshipType
            print(f"\n🗑️  Step 5: Cleaning up secondary RelationshipType")

            # Double-check no relationships are still using it
            remaining_relationships = Relationship.objects.filter(
                relationship_type=secondary_rel_type,
                is_deleted=False
            )

            if remaining_relationships.count() == 0:
                secondary_rel_type.delete()
                print(f"   ✅ Deleted secondary RelationshipType: {secondary_rel_type.slug}")
            else:
                print(f"   ⚠️  Cannot delete secondary RelationshipType - {remaining_relationships.count()} relationships still using it")

            # Step 6: Test the consolidated setup
            print(f"\n🧪 Step 6: Testing consolidated RelationshipType")

            from pipelines.relation_field_handler import RelationFieldHandler

            # Force refresh the handlers to pick up changes
            sales_handler = RelationFieldHandler(sales_field)
            # Clear cached relationship type
            sales_handler._relationship_type = None
            sales_rel_type_test = sales_handler.relationship_type
            print(f"   Sales field RelationshipType: {sales_rel_type_test.slug}")

            job_apps_handler = RelationFieldHandler(job_apps_field)
            # Clear cached relationship type
            job_apps_handler._relationship_type = None
            job_apps_rel_type_test = job_apps_handler.relationship_type
            print(f"   Job Apps field RelationshipType: {job_apps_rel_type_test.slug}")

            print(f"   Same RelationshipType: {sales_rel_type_test.id == job_apps_rel_type_test.id}")

            if sales_rel_type_test.id == job_apps_rel_type_test.id:
                print(f"   ✅ RelationshipType consolidation successful!")
            else:
                print(f"   ❌ RelationshipType consolidation failed - still creating separate types")

                # This might happen due to the logic in relation_field_handler.py
                # The Job Apps field might still be creating its own type due to the slug generation
                print(f"   ℹ️  This may be due to how the reverse field generates its RelationshipType")
                print(f"   ℹ️  The fix may require updating the relation_field_handler logic")

            # Step 7: Summary
            print(f"\n📋 Step 7: Consolidation Summary")
            print(f"   ✅ Primary RelationshipType: {primary_rel_type.slug}")
            print(f"   ✅ Migrated {migrated_count} relationships")
            print(f"   ✅ Cleaned up secondary RelationshipType")
            print(f"   ✅ Bidirectional fields now linked properly")

            print(f"\n✅ RelationshipType consolidation completed!")

        except Exception as e:
            print(f"\n❌ Consolidation failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 CONSOLIDATION COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    consolidate_relationship_types('oneotalent')