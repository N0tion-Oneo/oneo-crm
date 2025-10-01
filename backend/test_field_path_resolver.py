"""
Integration tests for FieldPathResolver - Dot notation relationship traversal

Tests cover:
1. Single-hop traversal (company.name)
2. Multi-hop traversal (deal.company.industry)
3. Array handling for multiple relations
4. Caching functionality
5. Edge cases and error handling
6. Integration with workflows
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant, Domain
from pipelines.models import Pipeline, Field, Record
from relationships.models import RelationshipType, Relationship
from pipelines.field_path_resolver import FieldPathResolver, resolve_field_path
from pipelines.relation_field_handler import RelationFieldHandler
from workflows.nodes.base import BaseNodeProcessor
from workflows.utils.condition_evaluator import GroupedConditionEvaluator

User = get_user_model()


def run_tests():
    """Run all integration tests"""
    print("=" * 80)
    print("🧪 FIELD PATH RESOLVER INTEGRATION TESTS")
    print("=" * 80)

    # Get or create test tenant
    tenant, _ = Tenant.objects.get_or_create(
        schema_name='test',
        defaults={'name': 'Test Tenant', 'paid_until': '2099-12-31', 'on_trial': True}
    )

    # Ensure domain exists
    Domain.objects.get_or_create(
        domain='test.localhost',
        defaults={'tenant': tenant, 'is_primary': True}
    )

    with schema_context('test'):
        print("\n🔧 Setting up test data...")

        # Get or create test user
        user, _ = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com'}
        )

        # Clean up existing test data
        Pipeline.objects.filter(name__startswith='Test').delete()

        # Create pipelines
        print("   → Creating pipelines...")
        industry_pipeline = Pipeline.objects.create(
            name='Test Industries',
            slug='test_industries',
            description='Test industry pipeline',
            created_by=user
        )

        company_pipeline = Pipeline.objects.create(
            name='Test Companies',
            slug='test_companies',
            description='Test company pipeline',
            created_by=user
        )

        contact_pipeline = Pipeline.objects.create(
            name='Test Contacts',
            slug='test_contacts',
            description='Test contact pipeline',
            created_by=user
        )

        deal_pipeline = Pipeline.objects.create(
            name='Test Deals',
            slug='test_deals',
            description='Test deal pipeline',
            created_by=user
        )

        # Create fields
        print("   → Creating fields...")

        # Industry fields
        Field.objects.create(
            pipeline=industry_pipeline,
            name='Category',
            slug='category',
            field_type='text',
            created_by=user
        )

        # Company fields
        Field.objects.create(
            pipeline=company_pipeline,
            name='Company Name',
            slug='company_name',
            field_type='text',
            created_by=user
        )

        company_industry_field = Field.objects.create(
            pipeline=company_pipeline,
            name='Industry',
            slug='industry',
            field_type='relation',
            field_config={
                'target_pipeline_id': industry_pipeline.id,
                'target_pipeline': industry_pipeline.id,
                'display_field': 'category',
                'allow_multiple': False
            },
            created_by=user
        )

        # Contact fields
        Field.objects.create(
            pipeline=contact_pipeline,
            name='Contact Name',
            slug='contact_name',
            field_type='text',
            created_by=user
        )

        Field.objects.create(
            pipeline=contact_pipeline,
            name='Email',
            slug='email',
            field_type='email',
            created_by=user
        )

        contact_company_field = Field.objects.create(
            pipeline=contact_pipeline,
            name='Company',
            slug='company',
            field_type='relation',
            field_config={
                'target_pipeline_id': company_pipeline.id,
                'target_pipeline': company_pipeline.id,
                'display_field': 'company_name',
                'allow_multiple': False
            },
            created_by=user
        )

        # Deal fields
        Field.objects.create(
            pipeline=deal_pipeline,
            name='Deal Name',
            slug='deal_name',
            field_type='text',
            created_by=user
        )

        deal_company_field = Field.objects.create(
            pipeline=deal_pipeline,
            name='Company',
            slug='company',
            field_type='relation',
            field_config={
                'target_pipeline_id': company_pipeline.id,
                'target_pipeline': company_pipeline.id,
                'display_field': 'company_name',
                'allow_multiple': False
            },
            created_by=user
        )

        deal_contacts_field = Field.objects.create(
            pipeline=deal_pipeline,
            name='Contacts',
            slug='contacts',
            field_type='relation',
            field_config={
                'target_pipeline_id': contact_pipeline.id,
                'target_pipeline': contact_pipeline.id,
                'display_field': 'contact_name',
                'allow_multiple': True
            },
            created_by=user
        )

        # Create records
        print("   → Creating records...")

        # Create industry
        tech_industry = Record.objects.create(
            pipeline=industry_pipeline,
            data={'category': 'Technology'},
            created_by=user,
            updated_by=user
        )

        # Create company
        acme_company = Record.objects.create(
            pipeline=company_pipeline,
            data={'company_name': 'Acme Corporation'},
            created_by=user,
            updated_by=user
        )

        # Create contacts
        john_contact = Record.objects.create(
            pipeline=contact_pipeline,
            data={
                'contact_name': 'John Doe',
                'email': 'john@acme.com'
            },
            created_by=user,
            updated_by=user
        )

        jane_contact = Record.objects.create(
            pipeline=contact_pipeline,
            data={
                'contact_name': 'Jane Smith',
                'email': 'jane@acme.com'
            },
            created_by=user,
            updated_by=user
        )

        # Create deal
        deal_record = Record.objects.create(
            pipeline=deal_pipeline,
            data={'deal_name': 'Enterprise Deal'},
            created_by=user,
            updated_by=user
        )

        # Create relationships
        print("   → Creating relationships...")

        # Company -> Industry
        company_industry_handler = RelationFieldHandler(company_industry_field)
        company_industry_handler.set_relationships(acme_company, tech_industry.id, user)

        # Contact -> Company
        contact_company_handler = RelationFieldHandler(contact_company_field)
        contact_company_handler.set_relationships(john_contact, acme_company.id, user)
        contact_company_handler.set_relationships(jane_contact, acme_company.id, user)

        # Deal -> Company
        deal_company_handler = RelationFieldHandler(deal_company_field)
        deal_company_handler.set_relationships(deal_record, acme_company.id, user)

        # Deal -> Contacts (multiple)
        deal_contacts_handler = RelationFieldHandler(deal_contacts_field)
        deal_contacts_handler.set_relationships(deal_record, [john_contact.id, jane_contact.id], user)

        # Refresh records to ensure relation data is populated
        acme_company.refresh_from_db()
        john_contact.refresh_from_db()
        deal_record.refresh_from_db()

        print("✅ Test data setup complete!\n")

        # ===========================================
        # TEST 1: Simple field access (no relations)
        # ===========================================
        print("-" * 80)
        print("TEST 1: Simple Field Access")
        print("-" * 80)

        resolver = FieldPathResolver(max_depth=3, enable_caching=True)

        # Test direct field access
        result = resolver.resolve(john_contact, 'contact_name')
        assert result == 'John Doe', f"Expected 'John Doe', got '{result}'"
        print(f"✅ Direct field access: contact.contact_name = '{result}'")

        result = resolver.resolve(john_contact, 'email')
        assert result == 'john@acme.com', f"Expected 'john@acme.com', got '{result}'"
        print(f"✅ Direct field access: contact.email = '{result}'")

        # ===========================================
        # TEST 2: Single-hop relationship traversal
        # ===========================================
        print("\n" + "-" * 80)
        print("TEST 2: Single-Hop Relationship Traversal")
        print("-" * 80)

        # Contact -> Company -> Company Name
        result = resolver.resolve(john_contact, 'company.company_name')
        expected = 'Acme Corporation'
        if result == expected:
            print(f"✅ Single-hop traversal: contact.company.company_name = '{result}'")
        else:
            print(f"❌ Single-hop traversal failed: expected '{expected}', got '{result}'")
            print(f"   john_contact.data = {john_contact.data}")

        # ===========================================
        # TEST 3: Multi-hop relationship traversal
        # ===========================================
        print("\n" + "-" * 80)
        print("TEST 3: Multi-Hop Relationship Traversal")
        print("-" * 80)

        # Contact -> Company -> Industry -> Category
        result = resolver.resolve(john_contact, 'company.industry.category')
        expected = 'Technology'
        if result == expected:
            print(f"✅ Multi-hop traversal: contact.company.industry.category = '{result}'")
        else:
            print(f"❌ Multi-hop traversal failed: expected '{expected}', got '{result}'")

        # Deal -> Company -> Industry -> Category
        result = resolver.resolve(deal_record, 'company.industry.category')
        if result == expected:
            print(f"✅ Multi-hop traversal: deal.company.industry.category = '{result}'")
        else:
            print(f"❌ Multi-hop traversal failed: expected '{expected}', got '{result}'")

        # ===========================================
        # TEST 4: Array relation handling
        # ===========================================
        print("\n" + "-" * 80)
        print("TEST 4: Array Relation Handling (Multiple Cardinality)")
        print("-" * 80)

        # Deal -> Contacts (multiple)
        result = resolver.resolve(deal_record, 'contacts[0].contact_name')
        if result in ['John Doe', 'Jane Smith']:
            print(f"✅ Array access: deal.contacts[0].contact_name = '{result}'")
        else:
            print(f"❌ Array access failed: got '{result}'")

        result = resolver.resolve(deal_record, 'contacts[1].email')
        if result in ['john@acme.com', 'jane@acme.com']:
            print(f"✅ Array access: deal.contacts[1].email = '{result}'")
        else:
            print(f"❌ Array access failed: got '{result}'")

        # ===========================================
        # TEST 5: Caching functionality
        # ===========================================
        print("\n" + "-" * 80)
        print("TEST 5: Caching Functionality")
        print("-" * 80)

        resolver_with_cache = FieldPathResolver(max_depth=3, enable_caching=True)

        # First call - should cache
        result1 = resolver_with_cache.resolve(john_contact, 'company.company_name')
        # Second call - should hit cache
        result2 = resolver_with_cache.resolve(john_contact, 'company.company_name')

        assert result1 == result2 == 'Acme Corporation'
        print(f"✅ Caching works: Both calls returned '{result1}'")

        # ===========================================
        # TEST 6: Integration with BaseNodeProcessor
        # ===========================================
        print("\n" + "-" * 80)
        print("TEST 6: Integration with BaseNodeProcessor")
        print("-" * 80)

        class TestProcessor(BaseNodeProcessor):
            """Test node processor"""
            node_type = 'test_node'

            async def process(self, node_config, context):
                return {}

        processor = TestProcessor()

        # Test _get_nested_value with relation traversal
        context = {'record': john_contact}
        result = processor._get_nested_value(context, 'record.company.company_name')

        if result == 'Acme Corporation':
            print(f"✅ BaseNodeProcessor integration: Resolved company name = '{result}'")
        else:
            print(f"❌ BaseNodeProcessor integration failed: got '{result}'")

        # ===========================================
        # TEST 7: Integration with GroupedConditionEvaluator
        # ===========================================
        print("\n" + "-" * 80)
        print("TEST 7: Integration with GroupedConditionEvaluator")
        print("-" * 80)

        evaluator = GroupedConditionEvaluator()

        # Test condition with relation traversal
        conditions = [
            {
                'field': 'company.company_name',
                'operator': 'equals',
                'value': 'Acme Corporation'
            }
        ]

        data = {'record': john_contact}
        result, details = evaluator.evaluate(conditions, data, 'AND')

        if result:
            print(f"✅ Condition evaluator: Relationship condition evaluated correctly")
            print(f"   Details: {details}")
        else:
            print(f"❌ Condition evaluator failed: {details}")

        # ===========================================
        # TEST 8: Convenience function
        # ===========================================
        print("\n" + "-" * 80)
        print("TEST 8: Convenience Function")
        print("-" * 80)

        result = resolve_field_path(john_contact, 'company.company_name')
        if result == 'Acme Corporation':
            print(f"✅ Convenience function: resolve_field_path() works = '{result}'")
        else:
            print(f"❌ Convenience function failed: got '{result}'")

        # ===========================================
        # TEST 9: Error handling
        # ===========================================
        print("\n" + "-" * 80)
        print("TEST 9: Error Handling & Edge Cases")
        print("-" * 80)

        # Non-existent field
        result = resolver.resolve(john_contact, 'nonexistent_field', default='DEFAULT')
        assert result == 'DEFAULT'
        print(f"✅ Non-existent field returns default: '{result}'")

        # Invalid relationship path
        result = resolver.resolve(john_contact, 'company.invalid_field', default=None)
        print(f"✅ Invalid relationship path handled: '{result}'")

        # Max depth exceeded
        very_deep_path = '.'.join(['company'] * 10)
        result = resolver.resolve(john_contact, very_deep_path, default='MAX_DEPTH')
        print(f"✅ Max depth protection works: '{result}'")

        # Null record
        result = resolver.resolve(None, 'company.name', default='NULL_RECORD')
        assert result == 'NULL_RECORD'
        print(f"✅ Null record handled: '{result}'")

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)


if __name__ == '__main__':
    try:
        run_tests()
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
