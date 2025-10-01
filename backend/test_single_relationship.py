#!/usr/bin/env python
"""
Test that we create only ONE relationship record for bidirectional relationships
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Field, Record
from pipelines.relation_field_handler import RelationFieldHandler
from relationships.models import Relationship
from django.contrib.auth import get_user_model

User = get_user_model()


def test_single_relationship(tenant_schema='oneotalent'):
    """Test that we create only ONE relationship record for bidirectional relationships"""

    print(f"\n{'='*80}")
    print(f"🧪 TESTING SINGLE RELATIONSHIP RECORD FOR BIDIRECTIONAL FIELDS")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Get the bidirectional field pair
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

            # Get test records
            print(f"\n📋 Step 2: Getting test records")

            sales_records = Record.objects.filter(
                pipeline__name="Sales Pipeline",
                is_deleted=False
            )[:2]

            job_app_records = Record.objects.filter(
                pipeline__name="Job Applications",
                is_deleted=False
            )[:2]

            if sales_records.count() == 0 or job_app_records.count() == 0:
                print(f"   ❌ Not enough test records")
                return

            sales_record = sales_records.first()
            job_app_record = job_app_records.first()

            print(f"   ✅ Using Sales record: {sales_record.id}")
            print(f"   ✅ Using Job App record: {job_app_record.id}")

            # Clear any existing relationships first
            print(f"\n🧹 Step 3: Clearing existing relationships")

            sales_handler = RelationFieldHandler(sales_field)
            job_apps_handler = RelationFieldHandler(job_apps_field)
            user = User.objects.first()

            # Clear both sides
            sales_handler.set_relationships(sales_record, [], user)
            job_apps_handler.set_relationships(job_app_record, [], user)

            # Count relationships before
            rel_type = sales_handler.relationship_type
            before_count = Relationship.objects.filter(
                relationship_type=rel_type,
                is_deleted=False
            ).count()
            print(f"   📊 Relationships before: {before_count}")

            # Test creating relationship from Sales side
            print(f"\n🔄 Step 4: Creating relationship from Sales side")
            print(f"   → Sales record {sales_record.id} → Job App record {job_app_record.id}")

            result = sales_handler.set_relationships(sales_record, [job_app_record.id], user)
            print(f"   → Result: {result}")

            # Count relationships after sales side
            after_sales_count = Relationship.objects.filter(
                relationship_type=rel_type,
                is_deleted=False
            ).count()
            print(f"   📊 Relationships after sales side: {after_sales_count}")

            # Test creating relationship from Job Apps side (should NOT create duplicate)
            print(f"\n🔄 Step 5: Creating relationship from Job Apps side")
            print(f"   → Job App record {job_app_record.id} → Sales record {sales_record.id}")

            result = job_apps_handler.set_relationships(job_app_record, [sales_record.id], user)
            print(f"   → Result: {result}")

            # Count relationships after job apps side
            after_both_count = Relationship.objects.filter(
                relationship_type=rel_type,
                is_deleted=False
            ).count()
            print(f"   📊 Relationships after both sides: {after_both_count}")

            # Analyze the results
            print(f"\n📊 Step 6: Analysis")

            print(f"   Before: {before_count} relationships")
            print(f"   After sales side: {after_sales_count} relationships")
            print(f"   After both sides: {after_both_count} relationships")

            if after_both_count == 1:
                print(f"   ✅ SUCCESS: Only 1 relationship record created for bidirectional relationship!")
            else:
                print(f"   ❌ PROBLEM: {after_both_count} relationship records created (should be 1)")

            # Show the actual relationship records
            relationships = Relationship.objects.filter(
                relationship_type=rel_type,
                is_deleted=False
            )

            print(f"\n   📋 Actual relationship records:")
            for rel in relationships:
                print(f"      → ID: {rel.id}, Source: {rel.source_record_id} → Target: {rel.target_record_id}")

            # Test bidirectional queries
            print(f"\n🔍 Step 7: Testing bidirectional queries")

            sales_related = sales_handler.get_related_ids(sales_record)
            job_apps_related = job_apps_handler.get_related_ids(job_app_record)

            print(f"   Sales record sees: {sales_related}")
            print(f"   Job Apps record sees: {job_apps_related}")

            if sales_related == [job_app_record.id] and job_apps_related == [sales_record.id]:
                print(f"   ✅ Bidirectional queries working correctly!")
            else:
                print(f"   ❌ Bidirectional queries not working properly")

            print(f"\n✅ Single relationship test completed!")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 TEST COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    test_single_relationship('oneotalent')