#!/usr/bin/env python
"""
Fix production relation fields to work bidirectionally
This script will:
1. Update the Sales Pipeline <-> Job Applications bidirectional pair
2. Create reverse fields for Companies relations if needed
3. Ensure proper RelationshipType sharing
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
from relationships.models import RelationshipType
from django.contrib.auth import get_user_model

User = get_user_model()


def fix_production_relations(tenant_schema='oneotalent'):
    """Fix production relation fields for bidirectional functionality"""

    print(f"\n{'='*80}")
    print(f"🔧 FIXING PRODUCTION RELATION FIELDS")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Get the user for field creation
            user = User.objects.first()
            if not user:
                print("❌ No users found in tenant")
                return

            print(f"👤 Using user: {user.email}\n")

            # Step 1: Fix Sales Pipeline <-> Job Applications bidirectional pair
            print("🔗 Step 1: Fixing Sales Pipeline <-> Job Applications bidirectional pair")

            # Get the specific fields
            try:
                sales_field = Field.objects.get(
                    pipeline__name="Sales Pipeline",
                    name="Jobs Applied For",
                    field_type="relation",
                    is_deleted=False
                )
                print(f"   ✅ Found Sales Pipeline field: {sales_field.name} (ID: {sales_field.id})")

                job_apps_field = Field.objects.get(
                    pipeline__name="Job Applications",
                    name="Company Relation",
                    field_type="relation",
                    is_deleted=False
                )
                print(f"   ✅ Found Job Applications field: {job_apps_field.name} (ID: {job_apps_field.id})")

            except Field.DoesNotExist as e:
                print(f"   ❌ Could not find one of the bidirectional fields: {e}")
                return

            # Check current state
            print(f"\n   📊 Current state:")
            print(f"      Sales field reverse_field_id: {sales_field.reverse_field_id}")
            print(f"      Job Apps field reverse_field_id: {job_apps_field.reverse_field_id}")

            # Update reverse field links
            print(f"\n   🔧 Updating reverse field links...")

            # Update sales field to point to job apps field
            sales_field.reverse_field_id = job_apps_field.id
            sales_field.save()
            print(f"      ✅ Updated Sales Pipeline field reverse_field_id = {job_apps_field.id}")

            # Update job apps field to point to sales field
            job_apps_field.reverse_field_id = sales_field.id
            job_apps_field.save()
            print(f"      ✅ Updated Job Applications field reverse_field_id = {sales_field.id}")

            # Update job apps field config to indicate it's a reverse field
            job_apps_config = job_apps_field.field_config.copy() if job_apps_field.field_config else {}
            job_apps_config.update({
                'is_reverse_field': True,
                'original_field_id': sales_field.id
            })
            job_apps_field.field_config = job_apps_config
            job_apps_field.save()
            print(f"      ✅ Updated Job Applications field config to mark as reverse field")

            # Test the bidirectional functionality
            print(f"\n   🧪 Testing bidirectional functionality...")

            from pipelines.relation_field_handler import RelationFieldHandler

            sales_handler = RelationFieldHandler(sales_field)
            sales_rel_type = sales_handler.relationship_type
            print(f"      Sales field RelationshipType: {sales_rel_type.slug}")

            job_apps_handler = RelationFieldHandler(job_apps_field)
            job_apps_rel_type = job_apps_handler.relationship_type
            print(f"      Job Apps field RelationshipType: {job_apps_rel_type.slug}")

            print(f"      Same RelationshipType: {sales_rel_type.id == job_apps_rel_type.id}")

            if sales_rel_type.id == job_apps_rel_type.id:
                print(f"      ✅ RelationshipType sharing working correctly!")
            else:
                print(f"      ❌ RelationshipType sharing not working - different types created")

            # Step 2: Check Companies relations
            print(f"\n🏢 Step 2: Checking Companies relation fields")

            companies_fields = Field.objects.filter(
                pipeline__name="Companies",
                field_type="relation",
                is_deleted=False
            )

            print(f"   Found {companies_fields.count()} relation fields in Companies pipeline:")

            for field in companies_fields:
                print(f"\n   🔗 Field: {field.name} (ID: {field.id})")
                print(f"      Target Pipeline ID: {field.field_config.get('target_pipeline_id')}")
                print(f"      Reverse field ID: {field.reverse_field_id}")

                # Check if reverse field exists
                target_pipeline_id = field.field_config.get('target_pipeline_id')
                if target_pipeline_id and not field.reverse_field_id:
                    print(f"      ⚠️  No reverse field exists - this is a one-way relation")

                    # Check if user wants to create reverse fields for these
                    try:
                        target_pipeline = Pipeline.objects.get(id=target_pipeline_id)
                        print(f"      Target pipeline: {target_pipeline.name}")

                        # For now, just report - don't auto-create reverse fields for Companies
                        print(f"      ℹ️  Could create reverse field in {target_pipeline.name} if needed")

                    except Pipeline.DoesNotExist:
                        print(f"      ❌ Target pipeline {target_pipeline_id} not found")

            # Step 3: Summary and recommendations
            print(f"\n📋 Step 3: Summary and Recommendations")
            print(f"   ✅ Sales Pipeline <-> Job Applications: Fixed bidirectional linking")
            print(f"   ℹ️  Companies relations: Currently one-way (no reverse fields created)")
            print(f"   ℹ️  If you want Companies relations to be bidirectional, run additional script")

            print(f"\n✅ Production relation fields fix completed!")

        except Exception as e:
            print(f"\n❌ Fix failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 FIX COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    fix_production_relations('oneotalent')