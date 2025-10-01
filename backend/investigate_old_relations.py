#!/usr/bin/env python
"""
Investigate existing old relation fields and their RelationshipType objects
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record
from relationships.models import Relationship, RelationshipType
from pipelines.relation_field_handler import RelationFieldHandler
from django.contrib.auth import get_user_model

User = get_user_model()


def investigate_old_relations(tenant_schema='oneotalent'):
    """Investigate existing old relation fields"""

    print(f"\n{'='*80}")
    print(f"🔍 INVESTIGATING OLD RELATION FIELDS")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Find all relation fields (excluding the test ones we just created)
            print("📋 Step 1: Finding all relation fields")

            relation_fields = Field.objects.filter(
                field_type='relation',
                is_deleted=False
            ).exclude(
                name__contains='Test'  # Exclude our test fields
            ).order_by('pipeline__name', 'name')

            print(f"   Found {relation_fields.count()} non-test relation fields\n")

            if relation_fields.count() == 0:
                print("   ⚠️  No old relation fields found")
                return

            # Group by pipeline for better display
            pipelines_with_relations = {}
            for field in relation_fields:
                pipeline_name = field.pipeline.name
                if pipeline_name not in pipelines_with_relations:
                    pipelines_with_relations[pipeline_name] = []
                pipelines_with_relations[pipeline_name].append(field)

            # Display all relation fields
            print("📊 Step 2: Analyzing relation fields by pipeline")
            for pipeline_name, fields in pipelines_with_relations.items():
                print(f"\n   Pipeline: {pipeline_name}")
                for field in fields:
                    print(f"      🔗 {field.name} (ID: {field.id})")
                    print(f"         Auto-generated: {field.is_auto_generated}")
                    print(f"         Reverse field ID: {field.reverse_field_id}")
                    print(f"         Config: {field.field_config}")

            # Check RelationshipType objects
            print(f"\n🔗 Step 3: Checking RelationshipType objects")

            relationship_types = RelationshipType.objects.all()
            print(f"   Found {relationship_types.count()} RelationshipType objects\n")

            for rel_type in relationship_types:
                print(f"      RelationshipType: {rel_type.slug}")
                print(f"         Name: {rel_type.name}")
                print(f"         Cardinality: {rel_type.cardinality}")
                print(f"         Bidirectional: {rel_type.is_bidirectional}")

                # Count relationships using this type
                rel_count = Relationship.objects.filter(
                    relationship_type=rel_type,
                    is_deleted=False
                ).count()
                print(f"         Active relationships: {rel_count}")
                print()

            # Test RelationshipType creation for old fields
            print(f"\n🧪 Step 4: Testing RelationshipType creation for old fields")

            for field in relation_fields:
                print(f"\n   Testing field: {field.name} (ID: {field.id})")

                try:
                    handler = RelationFieldHandler(field)
                    rel_type = handler.relationship_type

                    print(f"      ✅ RelationshipType: {rel_type.slug}")
                    print(f"         Auto-generated: {field.is_auto_generated}")
                    print(f"         Is reverse field: {handler.is_reverse_field}")

                    # Check if this field has a reverse field
                    if field.reverse_field_id:
                        try:
                            reverse_field = Field.objects.get(id=field.reverse_field_id, is_deleted=False)
                            reverse_handler = RelationFieldHandler(reverse_field)
                            reverse_rel_type = reverse_handler.relationship_type

                            print(f"      🔄 Reverse field: {reverse_field.name} (ID: {reverse_field.id})")
                            print(f"         Reverse RelationshipType: {reverse_rel_type.slug}")
                            print(f"         Same RelationshipType: {rel_type.id == reverse_rel_type.id}")

                            if rel_type.id != reverse_rel_type.id:
                                print(f"         ❌ PROBLEM: Different RelationshipType objects!")
                                print(f"            Original: {rel_type.slug}")
                                print(f"            Reverse:  {reverse_rel_type.slug}")
                            else:
                                print(f"         ✅ Sharing same RelationshipType correctly")

                        except Field.DoesNotExist:
                            print(f"      ❌ Reverse field {field.reverse_field_id} not found")
                    else:
                        print(f"      ⚠️  No reverse field ID set")

                except Exception as e:
                    print(f"      ❌ Error testing field: {e}")

            # Check for any relationships and test bidirectional queries
            print(f"\n🔍 Step 5: Testing bidirectional queries on existing relationships")

            # Find any records with relationships
            relationships = Relationship.objects.filter(is_deleted=False)[:5]  # Limit to first 5
            print(f"   Found {relationships.count()} active relationships to test")

            for rel in relationships:
                print(f"\n      Testing relationship {rel.id}:")
                print(f"         Source: {rel.source_pipeline.name} record {rel.source_record_id}")
                print(f"         Target: {rel.target_pipeline.name} record {rel.target_record_id}")
                print(f"         Type: {rel.relationship_type.slug}")

                try:
                    # Test source record bidirectional query
                    source_record = Record.objects.get(id=rel.source_record_id, is_deleted=False)

                    # Find relation fields in source pipeline
                    source_rel_fields = Field.objects.filter(
                        pipeline=rel.source_pipeline,
                        field_type='relation',
                        is_deleted=False
                    )

                    for field in source_rel_fields:
                        handler = RelationFieldHandler(field)
                        if handler.relationship_type.id == rel.relationship_type.id:
                            print(f"         Testing field: {field.name}")
                            related_data = handler.get_related_records_with_display(source_record)
                            print(f"            Related data: {related_data}")
                            break

                except Record.DoesNotExist:
                    print(f"         ⚠️  Source record {rel.source_record_id} not found")
                except Exception as e:
                    print(f"         ❌ Error testing: {e}")

            print(f"\n✅ Investigation completed!")

        except Exception as e:
            print(f"\n❌ Investigation failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 INVESTIGATION COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    investigate_old_relations('oneotalent')