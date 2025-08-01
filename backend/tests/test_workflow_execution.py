#!/usr/bin/env python
"""
Test workflow execution system - Phase 7
Tests the complete workflow execution pipeline
"""
import os
import sys
import django
import asyncio

# Setup Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Now import after Django is set up
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant
from workflows.models import Workflow, WorkflowExecution, ExecutionStatus
from workflows.engine import workflow_engine
from workflows.tasks import execute_workflow_async

User = get_user_model()


def test_workflow_execution():
    """Test complete workflow execution using Celery"""
    print("🧪 Testing Phase 7 Workflow Execution System (Celery)")
    print("=" * 60)
    
    # Get demo tenant
    tenant = Tenant.objects.get(schema_name='demo')
    
    async def run_async_test():
        with schema_context(tenant.schema_name):
            # Get or create test workflow
            workflow = Workflow.objects.filter(name='CRM Lead Qualification').first()
            if not workflow:
                print("❌ No CRM Lead Qualification workflow found, creating one...")
                try:
                    from workflows.templates import workflow_template_manager
                    
                    workflow = workflow_template_manager.create_workflow_from_template(
                        template_id='crm_lead_qualification',
                        name='CRM Lead Qualification',
                        description='Test workflow for lead qualification',
                        created_by=user
                    )
                    print(f"✅ Created test workflow: {workflow.name}")
                except Exception as create_error:
                    print(f"❌ Failed to create test workflow: {create_error}")
                    return False
                
            print(f"✅ Found workflow: {workflow.name} (ID: {workflow.id})")
            
            # Get or create a test user
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.create_user(
                    username='test_user',
                    email='test@example.com',
                    password='testpass123',
                    is_superuser=True
                )
            
            print(f"✅ Using test user: {user.email}")
            
            # Prepare test trigger data
            trigger_data = {
                'record': {
                    'id': 'test-lead-123',
                    'data': {
                        'name': 'John Doe',
                        'email': 'john.doe@example.com',
                        'company': 'Acme Corp',
                        'industry': 'Technology',
                        'pain_points': 'Need better CRM system',
                        'budget': '$50,000',
                        'timeline': '3 months'
                    }
                },
                'trigger_type': 'test_execution',
                'timestamp': '2025-07-29T13:00:00Z'
            }
            
            print("✅ Prepared test trigger data")
            
            try:
                # Test Celery-based execution (production approach)
                print("\n🔄 Testing Celery workflow execution...")
                
                # Update workflow status to active for testing
                workflow.status = 'active'
                workflow.save()
                
                # Execute workflow using Celery task
                result = execute_workflow_async.delay(
                    tenant_schema=tenant.schema_name,
                    workflow_id=str(workflow.id),
                    trigger_data=trigger_data,
                    triggered_by_id=user.id
                )
                
                print(f"✅ Workflow task dispatched: {result.id}")
                
                # Wait for task completion (with timeout)
                try:
                    task_result = result.get(timeout=30)
                    
                    if task_result.get('success'):
                        print(f"✅ Workflow execution completed!")
                        print(f"   Execution ID: {task_result.get('execution_id')}")
                        print(f"   Status: {task_result.get('status')}")
                        print(f"   Duration: {task_result.get('duration_seconds')} seconds")
                        return True
                    else:
                        print(f"❌ Workflow execution failed: {task_result.get('error')}")
                        return False
                        
                except Exception as task_error:
                    print(f"⚠️  Task execution timeout or error: {task_error}")
                    print("   This may indicate Celery is not running or task queue issues")
                    print("   💡 To run Celery: celery -A oneo_crm worker --loglevel=info")
                    return False
                
            except Exception as e:
                print(f"❌ Workflow execution failed: {e}")
                return False
    
    # Run the async test
    return asyncio.run(run_async_test())


def test_celery_task_integration():
    """Test Celery task integration"""
    print("\n🧪 Testing Celery Task Integration")
    print("-" * 40)
    
    tenant = Tenant.objects.get(schema_name='demo')
    
    with schema_context(tenant.schema_name):
        workflow = Workflow.objects.filter(name='CRM Lead Qualification').first()
        user = User.objects.filter(is_superuser=True).first()
        
        # Create test data if missing
        if not user:
            user = User.objects.create_user(
                username='celery_test_user',
                email='celery@test.com',
                password='testpass123',
                is_superuser=True
            )
            print(f"✅ Created test user: {user.email}")
        
        if not workflow:
            print("❌ Missing CRM Lead Qualification workflow, creating test workflow...")
            # Create test workflow using template system
            try:
                from workflows.templates import workflow_template_manager
                
                workflow = workflow_template_manager.create_workflow_from_template(
                    template_id='crm_lead_qualification',
                    name='CRM Lead Qualification',
                    description='Test workflow for lead qualification',
                    created_by=user
                )
                print(f"✅ Created test workflow: {workflow.name}")
            except Exception as create_error:
                print(f"❌ Failed to create test workflow: {create_error}")
                # Try to get any workflow for testing
                workflow = Workflow.objects.first()
                if not workflow:
                    print("❌ No workflows found in tenant")
                    return False
                else:
                    print(f"✅ Using existing workflow: {workflow.name}")
        
        print(f"✅ Test setup complete - User: {user.email}, Workflow: {workflow.name}")
        
        trigger_data = {
            'record': {
                'id': 'celery-test-lead-456',
                'data': {
                    'name': 'Jane Smith',
                    'company': 'Beta Inc',
                    'industry': 'Healthcare',
                    'budget': '$100,000'
                }
            },
            'trigger_type': 'celery_test'
        }
        
        try:
            # Test Celery task dispatch (will run synchronously if Celery not running)
            print("🔄 Dispatching workflow to Celery...")
            
            result = execute_workflow_async.delay(
                tenant_schema=tenant.schema_name,
                workflow_id=str(workflow.id),
                trigger_data=trigger_data,
                triggered_by_id=user.id
            )
            
            print(f"✅ Celery task dispatched: {result.id}")
            print("💡 Note: To see results, start Celery worker with:")
            print("   celery -A oneo_crm worker --loglevel=info")
            
            return True
            
        except Exception as e:
            print(f"❌ Celery task dispatch failed: {e}")
            return False


def test_workflow_validation():
    """Test workflow validation system"""
    print("\n🧪 Testing Workflow Validation")
    print("-" * 40)
    
    tenant = Tenant.objects.get(schema_name='demo')
    
    with schema_context(tenant.schema_name):
        workflow = Workflow.objects.filter(name='CRM Lead Qualification').first()
        
        if not workflow:
            print("❌ No workflow found for validation")
            return False
        
        try:
            from workflows.tasks import validate_workflow_definition
            
            # Test workflow validation
            validation_result = validate_workflow_definition(
                workflow_id=str(workflow.id),
                tenant_schema=tenant.schema_name
            )
            
            print(f"✅ Workflow validation completed")
            print(f"   Valid: {validation_result.get('valid', False)}")
            print(f"   Nodes: {validation_result.get('node_count', 0)}")
            print(f"   Edges: {validation_result.get('edge_count', 0)}")
            
            if validation_result.get('errors'):
                print("   ⚠️  Errors:")
                for error in validation_result['errors']:
                    print(f"      - {error}")
            
            if validation_result.get('warnings'):
                print("   ⚠️  Warnings:")
                for warning in validation_result['warnings']:
                    print(f"      - {warning}")
            
            return validation_result.get('valid', False)
            
        except Exception as e:
            print(f"❌ Workflow validation failed: {e}")
            return False


def main():
    """Run all workflow tests"""
    print("🚀 Starting Phase 7 Workflow System Tests")
    print("=" * 60)
    
    tests = [
        ("Celery Execution", test_workflow_execution),
        ("Celery Integration", test_celery_task_integration), 
        ("Workflow Validation", test_workflow_validation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results[test_name] = False
        print()
    
    # Summary
    print("=" * 60)
    print("📊 WORKFLOW SYSTEM TEST RESULTS:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"📈 SUCCESS RATE: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL WORKFLOW TESTS PASSED!")
        print("🚀 Phase 7 Workflow System is fully operational!")
    else:
        print("⚠️  Some tests need attention")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)