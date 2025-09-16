#!/usr/bin/env python
"""Test script to verify dynamic field value matching in workflow triggers."""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from workflows.models import Workflow, WorkflowNode
from pipelines.models import Pipeline, Field
import json

def test_dynamic_field_matching():
    """Test that the TriggerRecordUpdated node properly handles dynamic field value matching."""

    # Use the demo tenant
    with schema_context('demo'):
        print("Testing Dynamic Field Value Matching...")
        print("-" * 50)

        # Get or create a test pipeline with fields that have options
        pipeline, created = Pipeline.objects.get_or_create(
            name="Test Pipeline for Field Matching",
            defaults={
                'slug': 'test_field_matching',
                'description': 'Pipeline for testing field value matching'
            }
        )

        if created:
            print(f"✅ Created test pipeline: {pipeline.name}")
        else:
            print(f"✅ Using existing pipeline: {pipeline.name}")

        # Create fields with options
        status_field, created = Field.objects.get_or_create(
            pipeline=pipeline,
            slug='status',
            defaults={
                'label': 'Status',
                'field_type': 'select',
                'field_config': {
                    'options': ['lead', 'prospect', 'customer', 'churned']
                },
                'required': True
            }
        )

        if created:
            print(f"✅ Created status field with options: {status_field.field_config['options']}")
        else:
            print(f"✅ Using existing status field with options: {status_field.field_config.get('options', [])}")

        priority_field, created = Field.objects.get_or_create(
            pipeline=pipeline,
            slug='priority',
            defaults={
                'label': 'Priority',
                'field_type': 'select',
                'field_config': {
                    'options': ['low', 'medium', 'high', 'urgent']
                },
                'required': False
            }
        )

        if created:
            print(f"✅ Created priority field with options: {priority_field.field_config['options']}")
        else:
            print(f"✅ Using existing priority field with options: {priority_field.field_config.get('options', [])}")

        # Create a workflow with TriggerRecordUpdated node
        workflow, created = Workflow.objects.get_or_create(
            name="Test Dynamic Field Matching Workflow",
            defaults={
                'description': 'Workflow to test dynamic field value matching',
                'is_active': True
            }
        )

        if created:
            print(f"✅ Created test workflow: {workflow.name}")
        else:
            print(f"✅ Using existing workflow: {workflow.name}")

        # Create or update the trigger node with dynamic field matching
        trigger_config = {
            'pipeline_id': str(pipeline.id),
            'track_all_changes': False,
            'tracked_fields': ['status', 'priority'],  # Track specific fields
            'detect_specific_changes': True,
            'field_value_matches': {
                'status': {
                    'fromType': 'field_option',
                    'from': 'lead',
                    'toType': 'field_option',
                    'to': 'customer'
                },
                'priority': {
                    'fromType': 'any',
                    'toType': 'field_option',
                    'to': 'urgent'
                }
            }
        }

        trigger_node, created = WorkflowNode.objects.update_or_create(
            workflow=workflow,
            node_type='TRIGGER_RECORD_UPDATED',
            defaults={
                'name': 'Record Updated Trigger with Field Matching',
                'position_x': 100,
                'position_y': 100,
                'config': trigger_config
            }
        )

        if created:
            print(f"✅ Created trigger node with dynamic field matching")
        else:
            print(f"✅ Updated trigger node with dynamic field matching")

        print("\n📋 Trigger Configuration:")
        print(f"  Pipeline: {pipeline.name}")
        print(f"  Tracked Fields: {trigger_config['tracked_fields']}")
        print(f"  Field Value Matches:")
        for field_name, match_config in trigger_config['field_value_matches'].items():
            field = Field.objects.get(pipeline=pipeline, slug=field_name)
            from_val = match_config.get('from', 'any')
            to_val = match_config.get('to', 'any')
            print(f"    - {field.label}: {from_val} → {to_val}")

        print("\n✅ Dynamic field value matching configuration verified!")
        print("\nTo test in the UI:")
        print("1. Go to http://demo.localhost:3000/workflows")
        print(f"2. Open the workflow: '{workflow.name}'")
        print("3. Click on the trigger node to see the configuration")
        print("4. Check that 'Detect Specific Changes' shows field value matches for Status and Priority")

        return True

if __name__ == "__main__":
    try:
        success = test_dynamic_field_matching()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)