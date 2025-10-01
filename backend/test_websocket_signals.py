#!/usr/bin/env python
"""
Test WebSocket signal firing for relation field updates
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


def test_websocket_signals(tenant_schema='oneotalent'):
    """Test that WebSocket signals fire when relation fields are updated"""

    print(f"\n{'='*80}")
    print(f"🧪 TESTING WEBSOCKET SIGNALS FOR RELATION FIELDS")
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

            # Test creating a new relationship
            print(f"\n🔄 Step 3: Testing relationship creation (should trigger WebSocket signals)")

            sales_handler = RelationFieldHandler(sales_field)
            user = User.objects.first()

            # Add the job app record to the sales record's relations
            print(f"   → Adding job app {job_app_record.id} to sales record {sales_record.id}")
            result = sales_handler.set_relationships(sales_record, [job_app_record.id], user)
            print(f"   → Result: {result}")

            # Check the logs to see if WebSocket signals fired
            print(f"   📊 Check the Django logs above for WebSocket signal messages")
            print(f"   📊 You should see messages like:")
            print(f"        - '🔗 WEBSOCKET: Processing relationship save'")
            print(f"        - '🔄 WEBSOCKET: Starting record updates for relationship change'")
            print(f"        - '📡 Broadcasting record update to WebSocket channels...'")

            # Test updating (removing) a relationship
            print(f"\n🔄 Step 4: Testing relationship removal (should trigger WebSocket signals)")

            print(f"   → Removing job app {job_app_record.id} from sales record {sales_record.id}")
            result = sales_handler.set_relationships(sales_record, [], user)
            print(f"   → Result: {result}")

            print(f"   📊 Check the Django logs above for more WebSocket signal messages")

            print(f"\n✅ WebSocket signal test completed!")
            print(f"📊 Check the logs above to verify that signals fired correctly")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 TEST COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    test_websocket_signals('oneotalent')