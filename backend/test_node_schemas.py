#!/usr/bin/env python
"""
Test script for workflow node schemas API endpoint
Run this to verify all node processors have valid CONFIG_SCHEMA definitions
"""

import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from workflows.processors import get_all_node_processors


def test_node_schemas():
    """Test that all node processors have valid CONFIG_SCHEMA"""

    print("=" * 60)
    print("WORKFLOW NODE SCHEMA TEST")
    print("=" * 60)

    # Get all processors
    processors = get_all_node_processors()
    print(f"\n✅ Found {len(processors)} node processors")

    # Track statistics
    stats = {
        'total': len(processors),
        'with_schema': 0,
        'without_schema': 0,
        'with_errors': 0,
        'processors_with_schema': [],
        'processors_without_schema': [],
        'processors_with_errors': []
    }

    # Test each processor
    print("\nTesting each processor:")
    print("-" * 40)

    for node_type, processor_class in processors.items():
        try:
            # Instantiate processor
            processor = processor_class()

            # Check for CONFIG_SCHEMA
            has_schema = hasattr(processor, 'CONFIG_SCHEMA')

            if has_schema:
                schema = processor.CONFIG_SCHEMA
                if schema and isinstance(schema, dict):
                    properties = schema.get('properties', {})
                    required = schema.get('required', [])

                    print(f"✅ {node_type:30} - Schema with {len(properties):2} properties, {len(required):2} required")
                    stats['with_schema'] += 1
                    stats['processors_with_schema'].append(node_type)
                else:
                    print(f"⚠️  {node_type:30} - Schema exists but empty or invalid")
                    stats['without_schema'] += 1
                    stats['processors_without_schema'].append(node_type)
            else:
                print(f"❌ {node_type:30} - No CONFIG_SCHEMA")
                stats['without_schema'] += 1
                stats['processors_without_schema'].append(node_type)

        except Exception as e:
            print(f"🔥 {node_type:30} - Error: {str(e)[:50]}")
            stats['with_errors'] += 1
            stats['processors_with_errors'].append(node_type)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"\n📊 Statistics:")
    print(f"   Total Processors:     {stats['total']}")
    print(f"   With Schema:         {stats['with_schema']} ({stats['with_schema']*100//stats['total']}%)")
    print(f"   Without Schema:      {stats['without_schema']} ({stats['without_schema']*100//stats['total']}%)")
    print(f"   With Errors:         {stats['with_errors']}")

    if stats['processors_without_schema']:
        print(f"\n⚠️  Processors without schema:")
        for p in stats['processors_without_schema']:
            print(f"   - {p}")

    if stats['processors_with_errors']:
        print(f"\n🔥 Processors with errors:")
        for p in stats['processors_with_errors']:
            print(f"   - {p}")

    # Show sample schema
    print("\n" + "=" * 60)
    print("SAMPLE SCHEMA (EMAIL processor)")
    print("=" * 60)

    if 'EMAIL' in processors:
        try:
            email_processor = processors['EMAIL']()
            if hasattr(email_processor, 'CONFIG_SCHEMA'):
                schema = email_processor.CONFIG_SCHEMA
                print(json.dumps(schema, indent=2)[:500] + "...")
        except Exception as e:
            print(f"Could not show sample: {e}")

    return stats


def test_api_endpoint():
    """Test the actual API endpoint"""

    print("\n" + "=" * 60)
    print("API ENDPOINT TEST")
    print("=" * 60)

    try:
        from django.test import RequestFactory
        from django.contrib.auth import get_user_model
        from workflows.views_original import WorkflowViewSet

        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/api/v1/workflows/node-schemas/')

        # Mock user
        User = get_user_model()
        request.user = User.objects.first()

        if not request.user:
            print("Creating test user...")
            request.user = User.objects.create_user(
                username='test_schemas',
                email='test_schemas@example.com',
                password='test'
            )

        # Create viewset instance
        viewset = WorkflowViewSet()
        viewset.request = request

        # Call the action
        response = viewset.node_schemas(request)

        print(f"\n✅ API Response Status: {response.status_code}")
        print(f"✅ Found {len(response.data)} node types in response")

        # Show sample response structure
        if response.data:
            sample_key = list(response.data.keys())[0]
            sample = response.data[sample_key]

            print(f"\n📋 Sample Response Structure ({sample_key}):")
            print(f"   - node_type: {sample.get('node_type')}")
            print(f"   - display_name: {sample.get('display_name')}")
            print(f"   - supports_replay: {sample.get('supports_replay')}")
            print(f"   - supports_checkpoints: {sample.get('supports_checkpoints')}")
            print(f"   - has config_schema: {sample.get('config_schema') is not None}")

            if sample.get('config_schema'):
                schema = sample['config_schema']
                props = schema.get('properties', {})
                print(f"   - schema properties: {list(props.keys())[:5]}...")

        return True

    except Exception as e:
        print(f"\n❌ API Endpoint Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Starting Workflow Node Schema Tests...\n")

    # Test processors
    stats = test_node_schemas()

    # Test API endpoint
    api_success = test_api_endpoint()

    # Final verdict
    print("\n" + "=" * 60)
    print("FINAL VERDICT")
    print("=" * 60)

    if stats['with_schema'] > 30 and api_success:
        print("\n✅ SUCCESS! Migration is complete and working!")
        print(f"   - {stats['with_schema']} processors have schemas")
        print("   - API endpoint is functional")
        print("   - Backend is ready to serve as single source of truth")
    else:
        print("\n⚠️  Some issues found:")
        if stats['with_schema'] <= 30:
            print(f"   - Only {stats['with_schema']} processors have schemas (expected 30+)")
        if not api_success:
            print("   - API endpoint test failed")

    print("\n")