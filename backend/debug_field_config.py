#!/usr/bin/env python
"""
Debug the field configuration mismatch for display values
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Field, Record, Pipeline

def debug_field_config(tenant_schema='oneotalent'):
    """Debug field configuration mismatch"""

    with schema_context(tenant_schema):
        try:
            print('=== DEBUGGING FIELD CONFIGURATION ===')
            print()

            # Get the relation field and its configuration
            relation_field = Field.objects.get(id=316)
            target_pipeline_id = relation_field.field_config.get('target_pipeline_id')
            display_field_name = relation_field.field_config.get('display_field')

            print(f"🔧 Relation field: {relation_field.slug} (ID: {relation_field.id})")
            print(f"📍 Display field configured: '{display_field_name}'")
            print(f"🎯 Target pipeline ID: {target_pipeline_id}")
            print()

            # Get the target pipeline and check its fields
            target_pipeline = Pipeline.objects.get(id=target_pipeline_id)
            print(f"🏗️ Target pipeline: {target_pipeline.name} (ID: {target_pipeline.id})")
            print(f"📋 Pipeline fields:")

            name_field_exists = False
            for field in target_pipeline.fields.filter(is_deleted=False):
                print(f"   🔧 {field.slug} ({field.field_type}): {field.name}")
                if field.slug == 'name':
                    name_field_exists = True
                    print(f"      ✅ Found 'name' field!")

            if not name_field_exists:
                print(f"   ❌ NO 'name' field found in {target_pipeline.name} pipeline!")
                print(f"   📋 Available field slugs: {[f.slug for f in target_pipeline.fields.filter(is_deleted=False)]}")
            print()

            # Get the target record and check its data
            target_record = Record.objects.get(id=518)
            print(f"📋 Target record data: {target_record.data}")
            print()

            # Test different display field options
            print("🧪 Testing different display field options:")

            possible_fields = ['name', 'first_name', 'last_name', 'work_email', 'personal_email']
            for field_name in possible_fields:
                value = target_record.data.get(field_name)
                print(f"   🔍 {field_name}: {value}")

            # Create a combined name from first_name + last_name
            first_name = target_record.data.get('first_name', '').strip()
            last_name = target_record.data.get('last_name', '').strip()
            if first_name and last_name:
                combined_name = f"{first_name} {last_name}"
                print(f"   🔧 Combined name: '{combined_name}'")
            print()

            # Check if we need to update the relation field configuration
            # to use a field that actually exists
            print("🔧 SOLUTION OPTIONS:")
            print("1. Add a 'name' field to the Contacts pipeline")
            print("2. Change the display_field in the relation configuration to use an existing field")
            print("3. Create a computed field that combines first_name + last_name")
            print()

            # Option 2: Update the relation field to use first_name
            print("📝 Testing Option 2: Change display_field to 'first_name'")
            if first_name:
                print(f"   ✅ first_name has value: '{first_name}'")
                print(f"   🔧 Updating relation field configuration...")

                # Update the field configuration
                relation_field.field_config['display_field'] = 'first_name'
                relation_field.save()
                print(f"   ✅ Updated display_field from 'name' to 'first_name'")

                # Test the display value generation now
                from pipelines.relation_field_handler import RelationFieldHandler

                # Test with the updated configuration
                sales_record = Record.objects.get(id=516)
                handler = RelationFieldHandler(relation_field)
                display_records = handler.get_related_records_with_display(sales_record)
                print(f"   📊 Display records with first_name: {display_records}")

                if display_records and display_records[0]['display_value'] != f"Record #{target_record.id}":
                    print("   🎉 SUCCESS! Display value is now working with first_name")
                else:
                    print("   ❌ Still showing Record #X fallback")
            else:
                print(f"   ❌ first_name is empty: '{first_name}'")
            print()

            print('=== DEBUG COMPLETE ===')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_field_config()