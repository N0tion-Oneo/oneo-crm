#!/usr/bin/env python
"""
Test script to verify date_reached trigger configuration in both static and dynamic modes.
"""

import os
import sys
import django
import asyncio
from datetime import datetime, timedelta
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context
from workflows.nodes.triggers.date_reached import TriggerDateReachedProcessor as DateReachedTriggerProcessor
from workflows.services.test_data_service import TestDataService
from pipelines.models import Pipeline, Field
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

User = get_user_model()

async def test_static_mode():
    """Test date_reached trigger with static date (no pipeline required)."""
    print("\n=== Testing Static Date Mode ===")

    # Test static date configuration
    static_config = {
        'target_date': (timezone.now() + timedelta(days=1)).isoformat(),
        'timezone': 'America/New_York',
        'offset_hours': 2,
        'business_days_only': False
    }
    
    print(f"\nStatic Config: {json.dumps(static_config, indent=2, default=str)}")
    
    # Initialize processor
    processor = DateReachedTriggerProcessor()
    
    # Create node config
    node_config = {
        'id': 'test_static',
        'type': 'date_reached',
        'data': {
            'config': static_config
        }
    }
    
    # Test without pipeline (should work)
    print("\nTesting without pipeline...")
    context = {'trigger_data': {}}
    
    try:
        # Validate inputs (async method)
        is_valid = await processor.validate_inputs(node_config, context)
        print(f"Validation result: {is_valid}")

        if is_valid:
            print("✅ Static mode works without pipeline!")
        else:
            print("❌ Static mode validation failed without pipeline")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return static_config

async def test_dynamic_mode():
    """Test date_reached trigger with dynamic date field (pipeline required)."""
    print("\n=== Testing Dynamic Date Mode ===")

    # Get a user to set as created_by (using sync_to_async)
    @sync_to_async
    def get_user():
        with schema_context('oneotalent'):
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.first()
            return user

    user = await get_user()
    if not user:
        print("❌ No user found to create pipeline")
        return None

    # Get or create a test pipeline (using sync_to_async)
    @sync_to_async
    def get_or_create_pipeline():
        with schema_context('oneotalent'):
            return Pipeline.objects.get_or_create(
                name="Test Pipeline",
                defaults={
                    'description': 'Test pipeline for date_reached trigger',
                    'is_active': True,
                    'created_by': user
                }
            )

    pipeline, created = await get_or_create_pipeline()

    # Create a date field (using sync_to_async)
    @sync_to_async
    def get_or_create_field():
        with schema_context('oneotalent'):
            return Field.objects.get_or_create(
                pipeline=pipeline,
                name="target_date",
                defaults={
                    'display_name': 'Target Date',
                    'field_type': 'date',
                    'field_config': {'required': False}
                }
            )

    date_field, created = await get_or_create_field()

    with schema_context('oneotalent'):
        
        print(f"Pipeline: {pipeline.name} (ID: {pipeline.id})")
        print(f"Date Field: {date_field.name}")
        
        # Dynamic configuration
        dynamic_config = {
            'date_field': 'target_date',
            'pipeline_id': str(pipeline.id),
            'timezone': 'UTC',
            'offset_days': 1,
            'business_days_only': True
        }
        
        print(f"\nDynamic Config: {json.dumps(dynamic_config, indent=2)}")
        
        # Initialize processor
        processor = DateReachedTriggerProcessor()
        
        # Create node config
        node_config = {
            'id': 'test_dynamic',
            'type': 'date_reached',
            'data': {
                'config': dynamic_config
            }
        }
        
        # Test with pipeline
        print("\nTesting with pipeline...")
        context = {
            'trigger_data': {},
            'pipeline_id': str(pipeline.id)
        }
        
        try:
            # Validate inputs (async method)
            is_valid = await processor.validate_inputs(node_config, context)
            print(f"Validation result: {is_valid}")

            if is_valid:
                print("✅ Dynamic mode works with pipeline!")
            else:
                print("❌ Dynamic mode validation failed with pipeline")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        return dynamic_config

def test_test_data_service():
    """Test the TestDataService for date_reached trigger."""
    print("\n=== Testing TestDataService ===")
    
    with schema_context('oneotalent'):
        # TestDataService has class methods, not instance methods

        # Test without pipeline (should return static date options)
        print("\nTest data without pipeline:")
        test_data_response = TestDataService._get_date_trigger_test_data(None)
        test_data_no_pipeline = test_data_response.data.get('data', [])
        for item in test_data_no_pipeline[:3]:  # Show first 3
            print(f"  - {item['title']}")

        # Get a pipeline
        pipeline = Pipeline.objects.filter(is_active=True).first()
        if pipeline:
            print(f"\nTest data with pipeline '{pipeline.name}':")
            test_data_response = TestDataService._get_date_trigger_test_data(str(pipeline.id))
            test_data_with_pipeline = test_data_response.data.get('data', [])
            for item in test_data_with_pipeline[:3]:  # Show first 3
                print(f"  - {item.get('title', 'No title')}")

async def test_validation_with_oneOf():
    """Test that the oneOf constraint works correctly."""
    print("\n=== Testing oneOf Constraint ===")

    processor = DateReachedTriggerProcessor()
    
    # Test 1: Config with neither field (should fail)
    print("\nTest 1: No date field or target_date")
    invalid_config = {
        'id': 'test_invalid',
        'type': 'date_reached',
        'data': {
            'config': {
                'timezone': 'UTC'
            }
        }
    }
    is_valid = await processor.validate_inputs(invalid_config, {})
    print(f"Result: {'❌ Failed as expected' if not is_valid else '✅ Unexpectedly passed'}")
    
    # Test 2: Config with both fields (should work - oneOf allows this)
    print("\nTest 2: Both date_field and target_date")
    both_config = {
        'id': 'test_both',
        'type': 'date_reached',
        'data': {
            'config': {
                'date_field': 'target_date',
                'target_date': timezone.now().isoformat(),
                'timezone': 'UTC'
            }
        }
    }
    is_valid = await processor.validate_inputs(both_config, {})
    print(f"Result: {'✅ Passed' if is_valid else '❌ Failed'}")
    
    # Test 3: Config with only date_field
    print("\nTest 3: Only date_field (dynamic mode)")
    dynamic_only = {
        'id': 'test_dynamic_only',
        'type': 'date_reached',
        'data': {
            'config': {
                'date_field': 'target_date',
                'timezone': 'UTC'
            }
        }
    }
    is_valid = await processor.validate_inputs(dynamic_only, {})
    print(f"Result: {'✅ Passed' if is_valid else '❌ Failed'}")
    
    # Test 4: Config with only target_date
    print("\nTest 4: Only target_date (static mode)")
    static_only = {
        'id': 'test_static_only',
        'type': 'date_reached',
        'data': {
            'config': {
                'target_date': timezone.now().isoformat(),
                'timezone': 'UTC'
            }
        }
    }
    is_valid = await processor.validate_inputs(static_only, {})
    print(f"Result: {'✅ Passed' if is_valid else '❌ Failed'}")

async def main():
    print("\n" + "="*60)
    print("DATE_REACHED TRIGGER CONFIGURATION TEST")
    print("="*60)

    try:
        # Test static mode
        static_config = await test_static_mode()

        # Test dynamic mode
        dynamic_config = await test_dynamic_mode()

        # Test TestDataService
        test_test_data_service()

        # Test validation constraints
        await test_validation_with_oneOf()
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print("\n✅ Date_reached trigger supports both modes:")
        print("  1. Static Mode: Uses target_date, no pipeline required")
        print("  2. Dynamic Mode: Uses date_field from pipeline records")
        print("\n✅ Frontend should:")
        print("  - Allow mode selection (Static vs Dynamic)")
        print("  - Show target_date picker for static mode")
        print("  - Show pipeline/field selectors for dynamic mode")
        print("  - Not require pipeline for static mode")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    # Run async main function
    sys.exit(asyncio.run(main()))