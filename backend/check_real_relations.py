#!/usr/bin/env python
"""
Check for real production relation fields (not test fields)
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
from django.contrib.auth import get_user_model

User = get_user_model()


def check_real_relations(tenant_schema='oneotalent'):
    """Check for actual production relation fields"""

    print(f"\n{'='*80}")
    print(f"🔍 CHECKING REAL PRODUCTION RELATION FIELDS")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Find all relation fields, grouped by patterns
            print("📋 Step 1: Finding all relation fields and categorizing them")

            relation_fields = Field.objects.filter(
                field_type='relation',
                is_deleted=False
            ).order_by('pipeline__name', 'name')

            print(f"   Total relation fields found: {relation_fields.count()}\n")

            # Categorize fields
            test_fields = []
            api_test_fields = []
            production_fields = []

            for field in relation_fields:
                pipeline_name = field.pipeline.name.lower()
                field_name = field.name.lower()

                if 'test' in pipeline_name or 'test' in field_name:
                    if 'api test' in pipeline_name:
                        api_test_fields.append(field)
                    else:
                        test_fields.append(field)
                else:
                    production_fields.append(field)

            print(f"📊 Categorization Results:")
            print(f"   🧪 Test fields: {len(test_fields)}")
            print(f"   🔌 API Test fields: {len(api_test_fields)}")
            print(f"   🏭 Production fields: {len(production_fields)}\n")

            # Show production fields in detail
            print(f"🏭 Production Relation Fields:")
            if production_fields:
                pipelines_with_relations = {}
                for field in production_fields:
                    pipeline_name = field.pipeline.name
                    if pipeline_name not in pipelines_with_relations:
                        pipelines_with_relations[pipeline_name] = []
                    pipelines_with_relations[pipeline_name].append(field)

                for pipeline_name, fields in pipelines_with_relations.items():
                    print(f"\n   Pipeline: {pipeline_name}")
                    for field in fields:
                        print(f"      🔗 {field.name} (ID: {field.id})")
                        print(f"         Target Pipeline ID: {field.field_config.get('target_pipeline_id')}")
                        print(f"         Allow Multiple: {field.field_config.get('allow_multiple', False)}")
                        print(f"         Display Field: {field.field_config.get('display_field')}")
                        print(f"         Auto-generated: {field.is_auto_generated}")
                        print(f"         Reverse field ID: {field.reverse_field_id}")

                        # Try to find target pipeline name
                        target_id = field.field_config.get('target_pipeline_id')
                        if target_id:
                            try:
                                from pipelines.models import Pipeline
                                target_pipeline = Pipeline.objects.get(id=target_id)
                                print(f"         Target Pipeline: {target_pipeline.name}")
                            except Pipeline.DoesNotExist:
                                print(f"         Target Pipeline: Not found (ID: {target_id})")
                        print()
            else:
                print("   No production relation fields found!")

            # Show a few examples of test fields to understand the pattern
            print(f"\n🧪 Sample Test Fields (showing first 5):")
            for field in test_fields[:5]:
                print(f"   - {field.pipeline.name} → {field.name}")

            print(f"\n🔌 Sample API Test Fields (showing first 5):")
            for field in api_test_fields[:5]:
                print(f"   - {field.pipeline.name} → {field.name}")

            # Look for potential bidirectional pairs in production
            print(f"\n🔗 Analyzing potential bidirectional pairs in production:")
            if len(production_fields) >= 2:
                # Look for fields that might be referencing each other
                for i, field1 in enumerate(production_fields):
                    target1 = field1.field_config.get('target_pipeline_id')
                    if target1:
                        for j, field2 in enumerate(production_fields):
                            if i != j:
                                target2 = field2.field_config.get('target_pipeline_id')
                                # Check if they reference each other's pipelines
                                if (target1 == field2.pipeline_id and
                                    target2 == field1.pipeline_id):
                                    print(f"   🔄 BIDIRECTIONAL PAIR FOUND:")
                                    print(f"      Field 1: {field1.pipeline.name} → {field1.name} (targets {target1})")
                                    print(f"      Field 2: {field2.pipeline.name} → {field2.name} (targets {target2})")
                                    print(f"      Reverse linked: {field1.reverse_field_id == field2.id and field2.reverse_field_id == field1.id}")
                                    print()

        except Exception as e:
            print(f"\n❌ Check failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 CHECK COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    check_real_relations('oneotalent')