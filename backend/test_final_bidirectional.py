#!/usr/bin/env python
"""
Test final bidirectional relationships after all fixes
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
from django.contrib.auth import get_user_model

User = get_user_model()


def test_final_bidirectional(tenant_schema='oneotalent'):
    """Test final bidirectional relationships"""

    print(f"\n{'='*80}")
    print(f"🧪 TESTING FINAL BIDIRECTIONAL RELATIONSHIPS")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Test Sales Pipeline <-> Job Applications
            print("🔗 Step 1: Testing Sales Pipeline <-> Job Applications")

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

            print(f"   Sales field: {sales_field.name} (ID: {sales_field.id})")
            print(f"   Job Apps field: {job_apps_field.name} (ID: {job_apps_field.id})")

            # Test RelationshipType sharing
            print(f"\n   🔍 Testing RelationshipType sharing:")

            sales_handler = RelationFieldHandler(sales_field)
            sales_rel_type = sales_handler.relationship_type
            print(f"      Sales field RelationshipType: {sales_rel_type.slug}")

            job_apps_handler = RelationFieldHandler(job_apps_field)
            job_apps_rel_type = job_apps_handler.relationship_type
            print(f"      Job Apps field RelationshipType: {job_apps_rel_type.slug}")

            same_type = sales_rel_type.id == job_apps_rel_type.id
            print(f"      Same RelationshipType: {same_type}")

            if same_type:
                print(f"      ✅ RelationshipType sharing working correctly!")
            else:
                print(f"      ❌ RelationshipType sharing still not working")

            # Test bidirectional queries
            print(f"\n   🔍 Testing bidirectional queries:")

            # Find some test records
            sales_records = Record.objects.filter(
                pipeline__name="Sales Pipeline",
                is_deleted=False
            )[:2]

            job_app_records = Record.objects.filter(
                pipeline__name="Job Applications",
                is_deleted=False
            )[:2]

            print(f"      Found {sales_records.count()} sales records, {job_app_records.count()} job app records")

            if sales_records.count() > 0 and job_app_records.count() > 0:
                sales_record = sales_records.first()
                job_app_record = job_app_records.first()

                print(f"      Testing with Sales record {sales_record.id} and Job App record {job_app_record.id}")

                # Test forward direction (Sales -> Job Apps)
                forward_data = sales_handler.get_related_records_with_display(sales_record)
                print(f"      Forward direction (Sales -> Job Apps): {forward_data}")

                # Test reverse direction (Job Apps -> Sales)
                reverse_data = job_apps_handler.get_related_records_with_display(job_app_record)
                print(f"      Reverse direction (Job Apps -> Sales): {reverse_data}")

                # Test API serialization
                print(f"\n   📡 Testing API serialization:")

                from api.serializers import RecordSerializer

                sales_serializer = RecordSerializer(sales_record)
                sales_api_data = sales_serializer.data
                sales_relation_data = sales_api_data.get('data', {}).get(sales_field.slug)
                print(f"      Sales record API data: {sales_relation_data}")

                job_apps_serializer = RecordSerializer(job_app_record)
                job_apps_api_data = job_apps_serializer.data
                job_apps_relation_data = job_apps_api_data.get('data', {}).get(job_apps_field.slug)
                print(f"      Job Apps record API data: {job_apps_relation_data}")

            else:
                print(f"      ⚠️  Not enough test records to test bidirectional queries")

            print(f"\n✅ Bidirectional relationship test completed!")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 TEST COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    test_final_bidirectional('oneotalent')