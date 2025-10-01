#!/usr/bin/env python
"""
Debug field configurations
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Field
from pipelines.relation_field_handler import RelationFieldHandler

def debug_field_configs(tenant_schema='oneotalent'):
    """Debug field configurations"""

    print(f"\n{'='*80}")
    print(f"🔍 DEBUGGING FIELD CONFIGURATIONS")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Get the bidirectional field pair
            sales_field = Field.objects.get(id=5)
            job_apps_field = Field.objects.get(id=66)

            print(f"Sales field: {sales_field.name} (ID: {sales_field.id})")
            print(f"  - is_reverse_field (config): {sales_field.field_config.get('is_reverse_field', False)}")
            print(f"  - reverse_field_id: {sales_field.reverse_field_id}")
            print(f"  - is_auto_generated: {sales_field.is_auto_generated}")
            print(f"  - target_pipeline_id: {sales_field.field_config.get('target_pipeline_id')}")

            print(f"\nJob Apps field: {job_apps_field.name} (ID: {job_apps_field.id})")
            print(f"  - is_reverse_field (config): {job_apps_field.field_config.get('is_reverse_field', False)}")
            print(f"  - reverse_field_id: {job_apps_field.reverse_field_id}")
            print(f"  - is_auto_generated: {job_apps_field.is_auto_generated}")
            print(f"  - target_pipeline_id: {job_apps_field.field_config.get('target_pipeline_id')}")

            # Check RelationshipTypes
            print(f"\n🔗 RelationshipType Analysis:")

            sales_handler = RelationFieldHandler(sales_field)
            job_apps_handler = RelationFieldHandler(job_apps_field)

            sales_rel_type = sales_handler.relationship_type
            job_apps_rel_type = job_apps_handler.relationship_type

            print(f"Sales RelationshipType: {sales_rel_type.slug} (ID: {sales_rel_type.id})")
            print(f"Job Apps RelationshipType: {job_apps_rel_type.slug} (ID: {job_apps_rel_type.id})")
            print(f"Are they the same? {sales_rel_type.id == job_apps_rel_type.id}")

            if sales_rel_type.id != job_apps_rel_type.id:
                print(f"❌ PROBLEM: Different RelationshipTypes!")
            else:
                print(f"✅ SUCCESS: Same RelationshipType!")

        except Exception as e:
            print(f"\n❌ Debug failed with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_field_configs('oneotalent')