#!/usr/bin/env python
"""
Test script to verify trigger configurations work with all field types
"""

import os
import sys
import django
import json
from datetime import datetime

# Add the backend directory to the Python path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from workflows.models import Workflow, WorkflowNode, WorkflowEdge, WorkflowTriggerType
from pipelines.models import Pipeline, Field
from workflows.triggers.registry import TriggerRegistry

def test_trigger_configurations():
    """Test trigger configurations with different field types"""

    print("=" * 80)
    print("Testing Trigger Configurations with All Field Types")
    print("=" * 80 + "\n")

    # Use the test tenant
    tenant_schema = 'oneodigital'

    with schema_context(tenant_schema):
        # Initialize trigger registry
        registry = TriggerRegistry()

        # Get a test pipeline with various field types
        try:
            pipeline = Pipeline.objects.first()
            if not pipeline:
                print("❌ No pipelines found in test tenant")
                return False

            print(f"✅ Using pipeline: {pipeline.name}")

            # Get fields from the pipeline
            fields = Field.objects.filter(pipeline=pipeline, is_deleted=False)
            print(f"✅ Found {fields.count()} fields in pipeline")

            # Group fields by type
            field_types = {}
            for field in fields:
                field_type = field.field_type
                if field_type not in field_types:
                    field_types[field_type] = []
                field_types[field_type].append(field)

            print("\nField Types Available:")
            for field_type, field_list in field_types.items():
                print(f"  - {field_type}: {len(field_list)} fields")

            # Test TRIGGER_RECORD_UPDATED configuration
            print("\n" + "=" * 50)
            print("Testing TRIGGER_RECORD_UPDATED")
            print("=" * 50)

            record_updated_configs = [
                {
                    "name": "Watch all fields",
                    "config": {
                        "pipeline_ids": [str(pipeline.id)],
                        "watch_all_fields": True,
                        "require_actual_changes": True
                    }
                },
                {
                    "name": "Watch specific fields",
                    "config": {
                        "pipeline_ids": [str(pipeline.id)],
                        "watch_all_fields": False,
                        "specific_fields": [f.slug for f in fields[:3]],  # First 3 fields
                        "require_actual_changes": True
                    }
                },
                {
                    "name": "With ignored fields",
                    "config": {
                        "pipeline_ids": [str(pipeline.id)],
                        "watch_all_fields": True,
                        "ignore_fields": [f.slug for f in fields[:2]],  # Ignore first 2
                        "require_actual_changes": True
                    }
                },
                {
                    "name": "With field conditions",
                    "config": {
                        "pipeline_ids": [str(pipeline.id)],
                        "watch_all_fields": True,
                        "field_filters": {
                            fields.first().slug: {
                                "operator": "equals",
                                "value": "test_value"
                            }
                        } if fields.exists() else {},
                        "require_actual_changes": True
                    }
                }
            ]

            for test_config in record_updated_configs:
                print(f"\n  Testing: {test_config['name']}")
                trigger = registry.get_trigger('TRIGGER_RECORD_UPDATED')
                if trigger:
                    is_valid = trigger.validate_config(test_config['config'])
                    if is_valid:
                        print(f"    ✅ Configuration valid")
                    else:
                        print(f"    ❌ Configuration invalid")
                else:
                    print(f"    ❌ Trigger not found in registry")

            # Test TRIGGER_FIELD_CHANGED configuration
            print("\n" + "=" * 50)
            print("Testing TRIGGER_FIELD_CHANGED")
            print("=" * 50)

            # Test with different field types
            for field_type, field_list in field_types.items():
                if not field_list:
                    continue

                test_field = field_list[0]
                print(f"\n  Testing with {field_type} field: {test_field.name}")

                # Create appropriate test configurations based on field type
                if field_type == 'number':
                    configs = [
                        {
                            "name": "Any change",
                            "config": {
                                "pipeline_ids": [str(pipeline.id)],
                                "watched_fields": [test_field.slug],
                                "change_types": ["any"]
                            }
                        },
                        {
                            "name": "Value increases",
                            "config": {
                                "pipeline_ids": [str(pipeline.id)],
                                "watched_fields": [test_field.slug],
                                "change_types": ["increases"],
                                "change_threshold": 10
                            }
                        },
                        {
                            "name": "Value decreases",
                            "config": {
                                "pipeline_ids": [str(pipeline.id)],
                                "watched_fields": [test_field.slug],
                                "change_types": ["decreases"],
                                "change_threshold": 5
                            }
                        }
                    ]
                elif field_type == 'select':
                    configs = [
                        {
                            "name": "Changes to specific value",
                            "config": {
                                "pipeline_ids": [str(pipeline.id)],
                                "watched_fields": [test_field.slug],
                                "change_types": ["specific_change"],
                                "value_filters": {
                                    test_field.slug: {"to": "option1"}
                                }
                            }
                        },
                        {
                            "name": "Changes from one to another",
                            "config": {
                                "pipeline_ids": [str(pipeline.id)],
                                "watched_fields": [test_field.slug],
                                "change_types": ["from_to"],
                                "value_filters": {
                                    test_field.slug: {"from": "option1", "to": "option2"}
                                }
                            }
                        }
                    ]
                elif field_type == 'boolean':
                    configs = [
                        {
                            "name": "Changes to true",
                            "config": {
                                "pipeline_ids": [str(pipeline.id)],
                                "watched_fields": [test_field.slug],
                                "change_types": ["specific_change"],
                                "value_filters": {
                                    test_field.slug: {"to": True}
                                }
                            }
                        }
                    ]
                else:
                    # Default config for other field types
                    configs = [
                        {
                            "name": "Any change",
                            "config": {
                                "pipeline_ids": [str(pipeline.id)],
                                "watched_fields": [test_field.slug],
                                "change_types": ["any"],
                                "ignore_null_changes": True
                            }
                        }
                    ]

                for config in configs:
                    print(f"    - {config['name']}: ", end='')
                    trigger = registry.get_trigger('TRIGGER_FIELD_CHANGED')
                    if trigger:
                        is_valid = trigger.validate_config(config['config'])
                        if is_valid:
                            print("✅")
                        else:
                            print("❌")
                    else:
                        print("❌ (trigger not found)")

            # Create a test workflow with triggers
            print("\n" + "=" * 50)
            print("Creating Test Workflow with Triggers")
            print("=" * 50)

            # Create workflow definition
            workflow = Workflow.objects.create(
                name=f"Test Trigger Workflow {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Test workflow for trigger configurations",
                is_active=True,
                is_template=False
            )
            print(f"✅ Created workflow: {workflow.name}")

            # Create trigger nodes
            trigger_nodes = []

            # Record Updated Trigger
            node1 = WorkflowNode.objects.create(
                workflow=workflow,
                node_type=WorkflowTriggerType.TRIGGER_RECORD_UPDATED,
                position={'x': 100, 'y': 100},
                data={
                    'label': 'Record Updated',
                    'pipeline_ids': [str(pipeline.id)],
                    'watch_all_fields': True,
                    'require_actual_changes': True
                }
            )
            trigger_nodes.append(node1)
            print(f"✅ Created TRIGGER_RECORD_UPDATED node")

            # Field Changed Trigger
            if fields.exists():
                node2 = WorkflowNode.objects.create(
                    workflow=workflow,
                    node_type=WorkflowTriggerType.TRIGGER_FIELD_CHANGED,
                    position={'x': 100, 'y': 200},
                    data={
                        'label': 'Field Changed',
                        'pipeline_ids': [str(pipeline.id)],
                        'watched_fields': [fields.first().slug],
                        'change_types': ['any'],
                        'ignore_null_changes': True
                    }
                )
                trigger_nodes.append(node2)
                print(f"✅ Created TRIGGER_FIELD_CHANGED node")

            # Validate all trigger configurations
            print("\n" + "=" * 50)
            print("Validating Workflow Trigger Configurations")
            print("=" * 50)

            all_valid = True
            for node in trigger_nodes:
                trigger = registry.get_trigger(node.node_type)
                if trigger:
                    is_valid = trigger.validate_config(node.data)
                    status = "✅" if is_valid else "❌"
                    print(f"  {node.node_type}: {status}")
                    if not is_valid:
                        all_valid = False
                else:
                    print(f"  {node.node_type}: ❌ (not in registry)")
                    all_valid = False

            print("\n" + "=" * 80)
            if all_valid:
                print("✅ All trigger configurations are valid!")
            else:
                print("❌ Some trigger configurations failed validation")
            print("=" * 80)

            return all_valid

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_trigger_configurations()
    sys.exit(0 if success else 1)