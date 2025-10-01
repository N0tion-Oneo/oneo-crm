#!/usr/bin/env python
"""
Test bidirectional relationship implementation
Tests the complete flow from field creation to API display
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
from relationships.models import Relationship
from api.serializers import RecordSerializer, DynamicRecordSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


def test_bidirectional_relationships(tenant_schema='oneotalent'):
    """Test the complete bidirectional relationship implementation"""

    print(f"\n{'='*80}")
    print(f"🧪 TESTING BIDIRECTIONAL RELATIONSHIP IMPLEMENTATION")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Get a test user
            user = User.objects.first()
            if not user:
                print("❌ No users found in the tenant")
                return

            print(f"👤 Using test user: {user.email}")

            # Create test pipelines
            print("\n📋 Step 1: Creating test pipelines")

            # Pipeline A - Companies
            pipeline_a, created = Pipeline.objects.get_or_create(
                name="Test Companies",
                defaults={
                    'description': 'Test pipeline for companies',
                    'created_by': user,
                    'pipeline_type': 'companies'
                }
            )
            print(f"   {'✅ Created' if created else '📋 Using existing'} Pipeline A: {pipeline_a.name} (ID: {pipeline_a.id})")

            # Pipeline B - Contacts
            pipeline_b, created = Pipeline.objects.get_or_create(
                name="Test Contacts",
                defaults={
                    'description': 'Test pipeline for contacts',
                    'created_by': user,
                    'pipeline_type': 'contacts'
                }
            )
            print(f"   {'✅ Created' if created else '📋 Using existing'} Pipeline B: {pipeline_b.name} (ID: {pipeline_b.id})")

            # Create a relation field from Companies to Contacts
            print(f"\n🔗 Step 2: Creating relation field from {pipeline_a.name} to {pipeline_b.name}")

            # Create a new relation field (use timestamp to ensure uniqueness)
            import time
            timestamp = int(time.time())
            field_name = f"Primary Contact Test {timestamp}"

            relation_field = Field.objects.create(
                pipeline=pipeline_a,
                name=field_name,
                field_type="relation",
                field_config={
                    'target_pipeline_id': pipeline_b.id,
                    'display_field': 'full_name',
                    'cardinality': 'one_to_many'
                },
                display_name=field_name,
                help_text="The primary contact for this company",
                created_by=user
            )
            print(f"   ✅ Created relation field: {relation_field.name} (ID: {relation_field.id})")

            # Check if reverse field was created automatically
            print(f"\n🔄 Step 3: Checking for automatic reverse field creation")

            if relation_field.reverse_field_id:
                try:
                    reverse_field = Field.objects.get(id=relation_field.reverse_field_id)
                    print(f"   ✅ Reverse field found: {reverse_field.name} (ID: {reverse_field.id})")
                    print(f"      Pipeline: {reverse_field.pipeline.name}")
                    print(f"      Auto-generated: {reverse_field.is_auto_generated}")
                    print(f"      Config: {reverse_field.field_config}")
                except Field.DoesNotExist:
                    print(f"   ❌ Reverse field {relation_field.reverse_field_id} not found")
            else:
                print(f"   ❌ No reverse field ID set on original field")

            # List all relation fields in both pipelines
            print(f"\n📊 Step 4: Listing all relation fields")

            # Pipeline A relation fields
            pipeline_a_fields = pipeline_a.fields.filter(field_type='relation', is_deleted=False)
            print(f"\n   {pipeline_a.name} relation fields ({pipeline_a_fields.count()}):")
            for field in pipeline_a_fields:
                print(f"      - {field.name} (auto: {field.is_auto_generated})")
                if field.reverse_field_id:
                    print(f"        → Links to reverse field ID: {field.reverse_field_id}")

            # Pipeline B relation fields
            pipeline_b_fields = pipeline_b.fields.filter(field_type='relation', is_deleted=False)
            print(f"\n   {pipeline_b.name} relation fields ({pipeline_b_fields.count()}):")
            for field in pipeline_b_fields:
                print(f"      - {field.name} (auto: {field.is_auto_generated})")
                if field.reverse_field_id:
                    print(f"        → Links to reverse field ID: {field.reverse_field_id}")

            # Create test records
            print(f"\n📝 Step 5: Creating test records")

            # Create a company record
            company_record = Record.objects.create(
                pipeline=pipeline_a,
                data={
                    'company_name': 'Test Company Inc',
                    'industry': 'Technology'
                },
                created_by=user,
                updated_by=user
            )
            print(f"   ✅ Created company record: {company_record.id}")

            # Create a contact record
            contact_record = Record.objects.create(
                pipeline=pipeline_b,
                data={
                    'full_name': 'John Doe',
                    'email': 'john@testcompany.com'
                },
                created_by=user,
                updated_by=user
            )
            print(f"   ✅ Created contact record: {contact_record.id}")

            # Create a relationship using the relation field handler
            print(f"\n🔗 Step 6: Creating relationship between records")
            from pipelines.relation_field_handler import RelationFieldHandler

            handler = RelationFieldHandler(relation_field)
            result = handler.set_relationships(company_record, [contact_record.id], user)
            print(f"   ✅ Relationship creation result: {result}")

            # Test API serialization
            print(f"\n📡 Step 7: Testing API serialization")

            # Test RecordSerializer
            print(f"\n   Testing RecordSerializer for company record:")
            serializer = RecordSerializer(company_record)
            data = serializer.data
            relation_data = data.get('data', {}).get(relation_field.slug)
            print(f"      Relation field data: {relation_data}")

            # Test DynamicRecordSerializer
            print(f"\n   Testing DynamicRecordSerializer for company record:")
            dynamic_serializer = DynamicRecordSerializer(company_record, context={'pipeline': pipeline_a})
            dynamic_data = dynamic_serializer.data
            dynamic_relation_data = dynamic_data.get('data', {}).get(relation_field.slug)
            print(f"      Relation field data: {dynamic_relation_data}")

            # Test reverse relationship (if reverse field exists)
            if relation_field.reverse_field_id:
                try:
                    reverse_field = Field.objects.get(id=relation_field.reverse_field_id)
                    print(f"\n   Testing reverse relationship for contact record:")

                    reverse_handler = RelationFieldHandler(reverse_field)
                    reverse_data = reverse_handler.get_related_records_with_display(contact_record)
                    print(f"      Reverse relation data: {reverse_data}")

                    # Test API serialization of reverse field
                    contact_serializer = RecordSerializer(contact_record)
                    contact_data = contact_serializer.data
                    reverse_relation_data = contact_data.get('data', {}).get(reverse_field.slug)
                    print(f"      Reverse field in API: {reverse_relation_data}")

                except Field.DoesNotExist:
                    print(f"   ❌ Reverse field not found for testing")

            print(f"\n✅ Bidirectional relationship test completed successfully!")

        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 TEST COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    test_bidirectional_relationships('oneotalent')