#!/usr/bin/env python
"""
Test workflow trigger system
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from workflows.models import Workflow, WorkflowTrigger, WorkflowExecution
from pipelines.models import Pipeline, Record
from django.contrib.auth import get_user_model
from workflows.triggers.manager import TriggerManager
from workflows.triggers.types import TriggerEvent
from django.utils import timezone
from asgiref.sync import sync_to_async
import asyncio

User = get_user_model()


async def test_manual_trigger():
    """Test manual workflow trigger"""
    print("\n=== Testing Manual Workflow Trigger ===\n")

    with schema_context('oneotalent'):
        # Get or create a workflow with manual trigger
        workflow = await sync_to_async(Workflow.objects.filter(trigger_type='manual').first)()
        if not workflow:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                print("❌ No superuser found")
                return False

            from workflows.templates import workflow_template_manager
            workflow = workflow_template_manager.create_workflow_from_template(
                template_id='crm_follow_up_sequence',
                name='Manual Test Workflow',
                description='Test manual trigger',
                created_by=user
            )
            # Update to manual trigger
            trigger = workflow.triggers.first()
            if trigger:
                trigger.trigger_type = 'manual'
                trigger.save()

        print(f"✅ Workflow: {workflow.name}")
        print(f"   Status: {workflow.status}")
        print(f"   Triggers: {workflow.triggers.count()}")

        # Activate workflow
        workflow.status = 'active'
        workflow.save()

        # Initialize trigger manager
        trigger_manager = TriggerManager()

        # Create manual trigger event
        event = TriggerEvent(
            event_type='manual',
            event_data={'test': 'data'},
            source='test_script',
            timestamp=timezone.now()
        )

        # Process the event
        print("\n📤 Triggering workflow manually...")
        await trigger_manager.process_event(event)

        # Check for executions
        await asyncio.sleep(2)  # Give it time to process

        executions = WorkflowExecution.objects.filter(workflow=workflow).count()
        print(f"\n📊 Workflow executions: {executions}")

        return executions > 0


async def test_record_trigger():
    """Test record-based workflow trigger"""
    print("\n=== Testing Record-Based Workflow Trigger ===\n")

    with schema_context('oneotalent'):
        # Get the lead qualification workflow we created
        workflow = Workflow.objects.filter(name='Test Lead Qualification').first()
        if not workflow:
            print("❌ No lead qualification workflow found")
            return False

        print(f"✅ Workflow: {workflow.name}")
        print(f"   Status: {workflow.status}")
        print(f"   Trigger Type: {workflow.trigger_type}")

        # Activate workflow
        workflow.status = 'active'
        workflow.save()

        # Activate its triggers
        for trigger in workflow.triggers.all():
            trigger.is_active = True
            trigger.save()
            print(f"   ✅ Activated trigger: {trigger.name}")

        # Create a pipeline for testing
        user = User.objects.filter(is_superuser=True).first()
        pipeline, created = Pipeline.objects.get_or_create(
            name='Test Leads Pipeline',
            defaults={'created_by': user}
        )
        print(f"\n📋 Pipeline: {pipeline.name}")

        # Create a record (should trigger workflow)
        print("\n📝 Creating a record to trigger workflow...")
        record = Record.objects.create(
            pipeline=pipeline,
            data={
                'company': 'Test Company',
                'email': 'test@example.com',
                'status': 'new'
            },
            created_by=user
        )
        print(f"   Created record: {record.id}")

        # Give the trigger system time to process
        await asyncio.sleep(3)

        # Check for executions
        executions = WorkflowExecution.objects.filter(workflow=workflow).count()
        print(f"\n📊 Workflow executions: {executions}")

        return executions > 0


async def main():
    """Run all tests"""
    print("=" * 50)
    print("WORKFLOW TRIGGER SYSTEM TEST")
    print("=" * 50)

    results = []

    # Test manual trigger
    manual_result = await test_manual_trigger()
    results.append(('Manual Trigger', manual_result))

    # Test record trigger
    record_result = await test_record_trigger()
    results.append(('Record Trigger', record_result))

    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)