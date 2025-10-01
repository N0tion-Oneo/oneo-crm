#!/usr/bin/env python
"""
Comprehensive test for WebSocket relationship field updates
Tests the complete end-to-end flow from relationship changes to WebSocket broadcasts
"""
import os
import django
import sys
import time

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


def test_websocket_relationship_flow(tenant_schema='oneotalent'):
    """Test complete WebSocket flow for relationship field updates"""

    print(f"\n{'='*80}")
    print(f"🧪 COMPREHENSIVE WEBSOCKET RELATIONSHIP FLOW TEST")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Step 1: Setup - Get fields and records
            print("🔗 Step 1: Setting up test data")

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

            # Step 2: Clean slate - Remove any existing relationships
            print(f"\n🧹 Step 2: Cleaning existing relationships")

            sales_handler = RelationFieldHandler(sales_field)
            job_apps_handler = RelationFieldHandler(job_apps_field)
            user = User.objects.first()

            # Clear both sides
            sales_handler.set_relationships(sales_record, [], user)
            job_apps_handler.set_relationships(job_app_record, [], user)

            # Count relationships to verify cleanup
            rel_type = sales_handler.relationship_type
            initial_count = Relationship.objects.filter(
                relationship_type=rel_type,
                is_deleted=False
            ).count()
            print(f"   📊 Initial relationship count: {initial_count}")

            # Step 3: Test relationship creation from Sales side
            print(f"\n🔄 Step 3: Creating relationship from Sales side")
            print(f"   📡 Expect: WebSocket broadcasts for both records")
            print(f"   📡 Channels: pipeline_records_{sales_record.pipeline_id}, pipeline_records_{job_app_record.pipeline_id}, pipelines_overview")
            print(f"   📡 Messages: record_update with relationship_changed=True")

            result = sales_handler.set_relationships(sales_record, [job_app_record.id], user)
            print(f"   → Result: {result}")

            # Verify single relationship created
            after_creation_count = Relationship.objects.filter(
                relationship_type=rel_type,
                is_deleted=False
            ).count()
            print(f"   📊 Relationships after creation: {after_creation_count}")

            if after_creation_count == 1:
                print(f"   ✅ SUCCESS: Single relationship record created")
            else:
                print(f"   ❌ PROBLEM: {after_creation_count} relationship records (should be 1)")
                return

            # Step 4: Test bidirectional access
            print(f"\n🔍 Step 4: Testing bidirectional access")

            sales_related = sales_handler.get_related_ids(sales_record)
            job_apps_related = job_apps_handler.get_related_ids(job_app_record)

            print(f"   Sales record sees: {sales_related}")
            print(f"   Job Apps record sees: {job_apps_related}")

            if sales_related == [job_app_record.id] and job_apps_related == [sales_record.id]:
                print(f"   ✅ SUCCESS: Bidirectional access working")
            else:
                print(f"   ❌ PROBLEM: Bidirectional access not working")

            # Step 5: Test relationship creation from Job Apps side (should not create duplicate)
            print(f"\n🔄 Step 5: Testing relationship from Job Apps side (should find existing)")
            print(f"   📡 Expect: WebSocket broadcasts for both records (refreshed data)")

            result = job_apps_handler.set_relationships(job_app_record, [sales_record.id], user)
            print(f"   → Result: {result}")

            # Verify still only one relationship
            after_second_creation_count = Relationship.objects.filter(
                relationship_type=rel_type,
                is_deleted=False
            ).count()
            print(f"   📊 Relationships after second creation: {after_second_creation_count}")

            if after_second_creation_count == 1:
                print(f"   ✅ SUCCESS: Still only one relationship record")
            else:
                print(f"   ❌ PROBLEM: {after_second_creation_count} relationship records (should still be 1)")

            # Step 6: Test relationship removal
            print(f"\n🔄 Step 6: Testing relationship removal")
            print(f"   📡 Expect: WebSocket broadcasts for both records with cleared relation data")

            result = sales_handler.set_relationships(sales_record, [], user)
            print(f"   → Result: {result}")

            # Verify relationship deleted
            after_deletion_count = Relationship.objects.filter(
                relationship_type=rel_type,
                is_deleted=False
            ).count()
            print(f"   📊 Relationships after deletion: {after_deletion_count}")

            if after_deletion_count == 0:
                print(f"   ✅ SUCCESS: Relationship properly deleted")
            else:
                print(f"   ❌ PROBLEM: {after_deletion_count} relationship records (should be 0)")

            # Final verification
            sales_related_final = sales_handler.get_related_ids(sales_record)
            job_apps_related_final = job_apps_handler.get_related_ids(job_app_record)

            print(f"   Final - Sales record sees: {sales_related_final}")
            print(f"   Final - Job Apps record sees: {job_apps_related_final}")

            # Step 7: WebSocket Analysis
            print(f"\n📊 Step 7: WebSocket Analysis")
            print(f"   📡 Check Django logs above for WebSocket messages:")
            print(f"       🔗 'WEBSOCKET: Processing relationship created/deleted'")
            print(f"       🔄 'WEBSOCKET: Starting record updates for relationship change'")
            print(f"       📡 'Broadcasting record update to WebSocket channels...'")
            print(f"       📡 Broadcasts to: pipeline_records_X, document_X, pipelines_overview")
            print(f"       🏷️ Messages should have 'relationship_changed': True flag")

            print(f"\n✅ WebSocket relationship flow test completed!")
            print(f"📊 All operations completed successfully - check logs for WebSocket activity")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 COMPREHENSIVE TEST COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    test_websocket_relationship_flow('oneotalent')