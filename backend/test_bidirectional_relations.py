#!/usr/bin/env python
"""
Test script to verify bidirectional relationship implementation
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
from pipelines.record_operations import RecordOperationManager
from pipelines.relation_field_handler import RelationFieldHandler
from pipelines.serializers import RecordSerializer
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


def cleanup_test_data(tenant_schema='oneotalent'):
    """Clean up test data from previous runs"""
    print("\n🧹 Cleaning up test data...")

    with schema_context(tenant_schema):
        # Delete test records
        test_records = Record.objects.filter(
            Q(data__contains={'test_field': 'Test Company'}) |
            Q(data__contains={'test_field': 'Test Contact'}) |
            Q(data__contains={'name': 'Test Company'}) |
            Q(data__contains={'name': 'Test Contact'})
        )
        count = test_records.count()
        if count > 0:
            test_records.delete()
            print(f"   Deleted {count} test records")

        # Delete test relationships (both active and soft-deleted)
        test_rel_types = RelationshipType.objects.filter(
            slug__in=['companies_contacts', 'test_companies_test_contacts']
        )

        if test_rel_types.exists():
            test_relationships = Relationship.objects.filter(
                relationship_type__in=test_rel_types
            )
            rel_count = test_relationships.count()
            if rel_count > 0:
                test_relationships.delete()  # Hard delete
                print(f"   Deleted {rel_count} test relationships")

            # Delete relationship types
            test_rel_types.delete()
            print(f"   Deleted {test_rel_types.count()} test relationship types")


def test_bidirectional_relationships(tenant_schema='oneotalent'):
    """Test bidirectional relationship functionality"""

    print("\n" + "="*80)
    print("🔍 TESTING BIDIRECTIONAL RELATIONSHIPS WITH SINGLE RECORD STORAGE")
    print("="*80)

    with schema_context(tenant_schema):
        # Get user for operations
        user = User.objects.filter(email='admin@oneo.com').first()
        print(f"\n✅ Using user: {user.email}")

        # Get or create pipelines
        companies_pipeline = Pipeline.objects.filter(slug='companies').first()
        contacts_pipeline = Pipeline.objects.filter(slug='contacts').first()

        if not companies_pipeline or not contacts_pipeline:
            print("❌ Required pipelines (companies, contacts) not found")
            return

        print(f"\n✅ Found pipelines:")
        print(f"   - Companies: {companies_pipeline.name} (ID: {companies_pipeline.id})")
        print(f"   - Contacts: {contacts_pipeline.name} (ID: {contacts_pipeline.id})")

        # Get or create relation field
        contacts_field = Field.objects.filter(
            pipeline=companies_pipeline,
            slug='contacts',
            field_type='relation'
        ).first()

        if not contacts_field:
            print("\n📝 Creating contacts relation field...")
            contacts_field = Field.objects.create(
                pipeline=companies_pipeline,
                name='Contacts',
                slug='contacts',
                field_type='relation',
                field_config={
                    'target_pipeline_id': contacts_pipeline.id,
                    'allow_multiple': True,
                    'display_field': 'name'
                },
                created_by=user
            )
            print(f"   ✅ Created field: {contacts_field.name}")
        else:
            print(f"\n✅ Found existing contacts field")

        # Create test records
        print("\n📝 Creating test records...")

        company = Record.objects.create(
            pipeline=companies_pipeline,
            data={'name': 'Test Company', 'test_field': 'Test Company'},
            status='active',
            created_by=user,
            updated_by=user
        )
        print(f"   ✅ Created company: ID {company.id}")

        contact1 = Record.objects.create(
            pipeline=contacts_pipeline,
            data={'name': 'Test Contact 1', 'test_field': 'Test Contact'},
            status='active',
            created_by=user,
            updated_by=user
        )
        print(f"   ✅ Created contact 1: ID {contact1.id}")

        contact2 = Record.objects.create(
            pipeline=contacts_pipeline,
            data={'name': 'Test Contact 2', 'test_field': 'Test Contact'},
            status='active',
            created_by=user,
            updated_by=user
        )
        print(f"   ✅ Created contact 2: ID {contact2.id}")

        # Test 1: Create relationships
        print("\n🧪 Test 1: Create relationships")
        print("   Setting contacts [contact1, contact2] for company...")

        operation_manager = RecordOperationManager(company)
        company.data['contacts'] = [contact1.id, contact2.id]
        operation_manager.process_record_save(company, user=user)

        # Check relationships were created
        handler = RelationFieldHandler(contacts_field)
        relationships = handler.get_relationships(company)

        print(f"   ✅ Created {relationships.count()} relationships")
        for rel in relationships:
            print(f"      - Relationship ID {rel.id}: {rel.source_record_id} → {rel.target_record_id}")

        # Verify no duplicates
        all_rels = Relationship.objects.filter(
            Q(source_record_id=company.id) | Q(target_record_id=company.id)
        )
        print(f"   ✅ Total relationships for company (both directions): {all_rels.count()}")

        # Test 2: Update relationships (remove one contact)
        print("\n🧪 Test 2: Update relationships (remove contact2)")
        print("   Setting contacts to [contact1] only...")

        company.data['contacts'] = [contact1.id]
        operation_manager = RecordOperationManager(company)
        operation_manager.process_record_save(company, user=user)

        # Check relationships
        relationships = handler.get_relationships(company)
        print(f"   ✅ Now have {relationships.count()} active relationships")

        # Check soft-deleted
        deleted_rels = Relationship.objects.filter(
            Q(source_record_id=company.id) | Q(target_record_id=company.id),
            is_deleted=True
        )
        print(f"   ✅ Soft-deleted relationships: {deleted_rels.count()}")

        # Test 3: Clear all relationships
        print("\n🧪 Test 3: Clear all relationships")
        print("   Setting contacts to None...")

        company.data['contacts'] = None
        operation_manager = RecordOperationManager(company)
        operation_manager.process_record_save(company, user=user)

        # Check relationships
        relationships = handler.get_relationships(company)
        print(f"   ✅ Active relationships: {relationships.count()}")

        deleted_rels = Relationship.objects.filter(
            Q(source_record_id=company.id) | Q(target_record_id=company.id),
            is_deleted=True
        )
        print(f"   ✅ Soft-deleted relationships: {deleted_rels.count()}")

        # Test 4: Re-add a previously deleted relationship
        print("\n🧪 Test 4: Re-add previously deleted relationship")
        print("   Setting contacts back to [contact1]...")

        company.data['contacts'] = [contact1.id]
        operation_manager = RecordOperationManager(company)
        operation_manager.process_record_save(company, user=user)

        # Check relationships
        relationships = handler.get_relationships(company)
        print(f"   ✅ Active relationships: {relationships.count()}")

        # Check if it reused the soft-deleted relationship
        for rel in relationships:
            print(f"      - Relationship ID {rel.id}: soft_deleted previously? {rel.deleted_at is not None}")

        # Test 5: Test serializer integration
        print("\n🧪 Test 5: Test serializer integration")

        serializer = RecordSerializer(company)
        data = serializer.data

        print(f"   ✅ Serialized data includes relation field:")
        if 'contacts' in data.get('data', {}):
            print(f"      contacts: {data['data']['contacts']}")
        else:
            print(f"      ❌ contacts field not found in serialized data")

        # Test 6: Check for duplicate prevention
        print("\n🧪 Test 6: Duplicate prevention test")
        print("   Trying to set same contacts multiple times...")

        # Try to create the same relationship multiple times
        for i in range(3):
            company.data['contacts'] = [contact1.id, contact2.id]
            operation_manager = RecordOperationManager(company)
            operation_manager.process_record_save(company, user=user)

        # Check that we don't have duplicates
        all_rels = Relationship.objects.filter(
            relationship_type=handler.relationship_type,
            is_deleted=False
        ).filter(
            Q(
                source_record_id=company.id,
                target_record_id=contact1.id
            ) | Q(
                source_record_id=contact1.id,
                target_record_id=company.id
            )
        )

        print(f"   ✅ Relationships between company and contact1: {all_rels.count()}")
        if all_rels.count() > 1:
            print("      ❌ DUPLICATE RELATIONSHIPS FOUND!")
            for rel in all_rels:
                print(f"         - ID {rel.id}: {rel.source_record_id} → {rel.target_record_id}")
        else:
            print("      ✅ No duplicates - bidirectional checking working correctly!")

        print("\n" + "="*80)
        print("✅ BIDIRECTIONAL RELATIONSHIP TESTING COMPLETE")
        print("="*80)


if __name__ == '__main__':
    import sys

    # Clean up first
    cleanup_test_data()

    # Run tests
    test_bidirectional_relationships()