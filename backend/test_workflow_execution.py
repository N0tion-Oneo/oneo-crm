#!/usr/bin/env python
"""
Test workflow execution with form submission trigger
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import asyncio
import json
from django_tenants.utils import schema_context
from workflows.models import Workflow, WorkflowExecution
from workflows.engine import workflow_engine
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone

async def test_form_submission_workflow():
    """Test form submission workflow execution"""
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_workflow_and_user():
        with schema_context('oneotalent'):
            # Get the test workflow
            workflow = Workflow.objects.filter(name__icontains='test').first()
            # Get a user to trigger the workflow
            user = User.objects.filter(is_superuser=True).first()
            return workflow, user

    workflow, user = await get_workflow_and_user()

    if not workflow:
        print("No test workflow found")
        return

    if not user:
        print("No superuser found")
        return

    print(f"Testing workflow: {workflow.name}")

    # Create test form submission data
    trigger_data = {
        'trigger_type': 'form_submitted',
        'trigger_node_id': 'trigger-form',  # Assuming a trigger node exists
        'trigger_data': {
            'form_data': {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@example.com',
                'company': 'Example Corp',
                'phone': '+1-555-0123',
                'message': 'I am interested in your product',
                'industry': 'Technology',
                'budget': '50000',
                'timeline': '3 months'
            },
            'pipeline_id': str(workflow.id),  # Using workflow ID as pipeline ID for test
            'form_mode': 'create',
            'stage': 'new_lead',
            'submitted_at': timezone.now().isoformat(),
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0 Test'
        }
    }

    print("\nTrigger data:")
    print(json.dumps(trigger_data, indent=2))

    # Execute the workflow
    print("\nStarting workflow execution...")
    try:
        execution = await workflow_engine.execute_workflow(
            workflow=workflow,
            trigger_data=trigger_data,
            triggered_by=user,
            start_node_id='start'  # Start from the first node
        )

        print(f"\n✅ Workflow execution completed: {execution.id}")
        print(f"Status: {execution.status}")

        # Check execution logs
        from workflows.models import WorkflowExecutionLog

        @sync_to_async
        def get_logs():
            with schema_context('oneotalent'):
                logs = list(WorkflowExecutionLog.objects.filter(execution=execution).order_by('started_at'))
                return logs

        logs = await get_logs()

        print(f"\nExecution logs ({len(logs)} nodes):")
        for log in logs:
            print(f"  - {log.node_name:30s} | {log.status:10s} | {log.duration_ms}ms")
            if log.error_details:
                print(f"    ERROR: {log.error_details}")

    except Exception as e:
        print(f"\n❌ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_workflow_with_trigger():
    """Test a simple workflow that starts with a trigger node"""
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get_or_create_workflow():
        with schema_context('oneotalent'):
            # Get a user
            user = User.objects.filter(is_superuser=True).first()

            # Get the tenant
            from tenants.models import Tenant
            tenant = Tenant.objects.get(schema_name='oneotalent')

            # Create a minimal test workflow if needed
            workflow = Workflow.objects.filter(name='Form Test Workflow').first()

            if not workflow and user:
                print("Creating test workflow...")
                workflow = Workflow.objects.create(
                    tenant=tenant,
                    name='Form Test Workflow',
                    description='Test workflow for form submission',
                    status='active',
                    created_by=user,
                    workflow_definition={
                        'nodes': [
                            {
                                'id': 'trigger-form',
                                'type': 'trigger_form_submitted',
                                'data': {
                                    'name': 'Form Submission Trigger',
                                    'config': {
                                        'pipeline_id': 'test-pipeline',
                                        'form_mode': 'create'
                                    }
                                }
                            },
                            {
                                'id': 'create-task',
                                'type': 'create_follow_up_task',
                                'data': {
                                    'name': 'Create Follow-up Task',
                                    'config': {
                                        'task_title': 'Contact {{trigger_data.form_data.first_name}} {{trigger_data.form_data.last_name}}',
                                        'task_description': 'Follow up with {{trigger_data.form_data.company}} - {{trigger_data.form_data.message}}',
                                        'due_in_days': '2',
                                        'priority': 'high',
                                        'assignee_id': '',  # Will be auto-assigned
                                        'pipeline_id': 'test-pipeline'
                                    }
                                }
                            }
                        ],
                        'edges': [
                            {
                                'source': 'trigger-form',
                                'target': 'create-task'
                            }
                        ]
                    }
                )
                print(f"Created workflow: {workflow.name}")
            return workflow, user

    workflow, user = await get_or_create_workflow()

    # Create trigger data
    trigger_data = {
        'trigger_type': 'form_submitted',
        'trigger_node_id': 'trigger-form',
        'trigger_data': {
            'form_data': {
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane.smith@example.com',
                'company': 'Tech Innovations',
                'phone': '+1-555-0456',
                'message': 'Need enterprise features'
            },
            'pipeline_id': 'test-pipeline',
            'form_mode': 'create',
            'submitted_at': timezone.now().isoformat()
        }
    }

    print("\nExecuting workflow with form trigger...")
    try:
        execution = await workflow_engine.execute_workflow(
            workflow=workflow,
            trigger_data=trigger_data,
            triggered_by=user,
            start_node_id='trigger-form'
        )

        print(f"✅ Workflow executed successfully: {execution.id}")

        # Check logs
        from workflows.models import WorkflowExecutionLog

        @sync_to_async
        def get_logs():
            with schema_context('oneotalent'):
                logs = list(WorkflowExecutionLog.objects.filter(execution=execution).order_by('started_at'))
                return logs

        logs = await get_logs()

        for log in logs:
            print(f"\nNode: {log.node_name}")
            print(f"  Status: {log.status}")
            print(f"  Input: {json.dumps(log.input_data, indent=2) if log.input_data else 'None'}")
            print(f"  Output: {json.dumps(log.output_data, indent=2) if log.output_data else 'None'}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 60)
    print("TESTING WORKFLOW EXECUTION WITH FORM SUBMISSION")
    print("=" * 60)

    # Test with existing workflow
    asyncio.run(test_form_submission_workflow())

    print("\n" + "=" * 60)
    print("TESTING SIMPLE WORKFLOW WITH TRIGGER NODE")
    print("=" * 60)

    # Test with simple workflow
    asyncio.run(test_simple_workflow_with_trigger())