"""
Simple test script for dot notation relationship traversal
Run with: python manage.py shell < test_dot_notation_simple.py
"""

print("=" * 80)
print("🧪 DOT NOTATION RELATIONSHIP TRAVERSAL - SIMPLE TEST")
print("=" * 80)

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record
from pipelines.field_path_resolver import FieldPathResolver, resolve_field_path
from pipelines.relation_field_handler import RelationFieldHandler

User = get_user_model()

print("\n✅ Imports successful!")

# Use existing test tenant
with schema_context('oneotalent'):
    print("\n🔧 Testing with oneotalent schema...")

    # Get a user
    user = User.objects.first()
    if not user:
        print("❌ No users found in oneotalent schema")
        exit(1)

    print(f"   Using user: {user.email}")

    # Get pipelines
    pipelines = list(Pipeline.objects.all()[:3])
    print(f"   Found {len(pipelines)} pipelines")

    if not pipelines:
        print("❌ No pipelines found")
        exit(1)

    # Get a record with relation fields
    for pipeline in pipelines:
        relation_fields = Field.objects.filter(
            pipeline=pipeline,
            field_type='relation',
            is_deleted=False
        )

        if relation_fields.exists():
            records = Record.objects.filter(pipeline=pipeline, is_deleted=False)[:5]

            for record in records:
                print(f"\n📋 Testing record: {record.id} from pipeline '{pipeline.name}'")
                print(f"   Record data keys: {list(record.data.keys())}")

                # Test basic field access
                resolver = FieldPathResolver(max_depth=3, enable_caching=True)

                for field in relation_fields:
                    field_slug = field.slug
                    print(f"\n   🔗 Relation field: '{field_slug}'")

                    # Test direct field access
                    direct_value = resolver.resolve(record, field_slug)
                    print(f"      Direct access: {direct_value}")

                    # Get field config
                    display_field = field.field_config.get('display_field', 'title')
                    print(f"      Display field: {display_field}")

                    # Test relationship traversal
                    if direct_value:
                        traversal_path = f"{field_slug}.{display_field}"
                        try:
                            traversed_value = resolver.resolve(record, traversal_path)
                            print(f"      ✅ Traversal '{traversal_path}': {traversed_value}")
                        except Exception as e:
                            print(f"      ⚠️  Traversal failed: {e}")

                    # Only test first relation field on first record
                    break

                # Only test first record with relations
                break

            # Only test first pipeline with relations
            break

print("\n" + "=" * 80)
print("✅ TEST COMPLETE")
print("=" * 80)
