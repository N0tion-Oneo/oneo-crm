#!/usr/bin/env python
"""
Comprehensive test for all workflow node processors
Tests that each processor can handle trigger_data and context properly
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
from workflows.models import Workflow
from workflows.engine import workflow_engine
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async
from tenants.models import Tenant

User = get_user_model()


async def create_test_workflow(node_type, node_config):
    """Create a test workflow with a specific node type"""

    @sync_to_async
    def create_workflow():
        with schema_context('oneotalent'):
            user = User.objects.filter(is_superuser=True).first()
            tenant = Tenant.objects.get(schema_name='oneotalent')

            # Create workflow with trigger and test node
            workflow = Workflow.objects.create(
                tenant=tenant,
                name=f'Test {node_type}',
                description=f'Test workflow for {node_type} node',
                status='active',
                created_by=user,
                workflow_definition={
                    'nodes': [
                        {
                            'id': 'trigger',
                            'type': 'trigger_form_submitted',
                            'data': {
                                'name': 'Form Trigger',
                                'config': {
                                    'pipeline_id': 'test-pipeline'
                                }
                            }
                        },
                        {
                            'id': 'test-node',
                            'type': node_type,
                            'data': node_config
                        }
                    ],
                    'edges': [
                        {
                            'source': 'trigger',
                            'target': 'test-node'
                        }
                    ]
                }
            )
            return workflow, user, tenant

    return await create_workflow()


async def test_node_processor(node_type, node_config, test_name):
    """Test a specific node processor"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"Node Type: {node_type}")
    print(f"{'='*60}")

    try:
        # Create test workflow
        workflow, user, tenant = await create_test_workflow(node_type, node_config)

        # Create trigger data with comprehensive test data
        trigger_data = {
            'trigger_type': 'form_submitted',
            'trigger_node_id': 'trigger',
            'trigger_data': {
                'form_data': {
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'email': 'john.doe@example.com',
                    'company': 'Test Company',
                    'phone': '+1-555-0123',
                    'message': 'Test message for workflow'
                },
                'pipeline_id': 'test-pipeline',
                'record_id': 'test-record-123',
                'record_data': {
                    'id': 'test-record-123',
                    'name': 'Test Record',
                    'status': 'new',
                    'value': 1000
                },
                'form_mode': 'create',
                'submitted_at': timezone.now().isoformat()
            }
        }

        # Execute workflow
        execution = await workflow_engine.execute_workflow(
            workflow=workflow,
            trigger_data=trigger_data,
            triggered_by=user,
            start_node_id='trigger'
        )

        # Check results
        from workflows.models import WorkflowExecutionLog

        @sync_to_async
        def get_logs():
            with schema_context('oneotalent'):
                logs = list(WorkflowExecutionLog.objects.filter(
                    execution=execution,
                    node_id='test-node'
                ).order_by('started_at'))
                return logs

        logs = await get_logs()

        if logs:
            log = logs[0]
            if log.status == 'success':
                print(f"✅ SUCCESS - {test_name}")
                if log.output_data:
                    print(f"   Output: {json.dumps(log.output_data, indent=2)[:200]}")
            else:
                print(f"❌ FAILED - {test_name}")
                print(f"   Error: {log.error_details}")
        else:
            print(f"⚠️  NO LOGS - {test_name}")

        # Cleanup
        @sync_to_async
        def cleanup():
            with schema_context('oneotalent'):
                workflow.delete()

        await cleanup()

    except Exception as e:
        print(f"❌ ERROR - {test_name}: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_all_processors():
    """Test all workflow node processors"""

    # Define test cases for each node type
    test_cases = [
        # AI Nodes
        ('ai_prompt', {
            'name': 'Test AI Prompt',
            'config': {
                'prompt_template': 'Summarize: {{trigger_data.form_data.message}}',
                'ai_config': {
                    'model': 'gpt-3.5-turbo',
                    'temperature': 0.7
                }
            }
        }, 'AI Prompt Node'),

        ('ai_analysis', {
            'name': 'Test AI Analysis',
            'config': {
                'analysis_type': 'sentiment',
                'data_source': 'trigger_data.form_data.message'
            }
        }, 'AI Analysis Node'),

        # Data Operations
        ('record_update', {
            'name': 'Test Record Update',
            'config': {
                'record_id_source': 'trigger_data.record_id',
                'update_data': {
                    'status': 'processed',
                    'notes': '{{trigger_data.form_data.message}}'
                }
            }
        }, 'Record Update Node'),

        ('record_create', {
            'name': 'Test Record Create',
            'config': {
                'pipeline_id': 'test-pipeline',
                'record_data': {
                    'name': '{{trigger_data.form_data.first_name}} {{trigger_data.form_data.last_name}}',
                    'email': '{{trigger_data.form_data.email}}',
                    'company': '{{trigger_data.form_data.company}}'
                }
            }
        }, 'Record Create Node'),

        # Control Flow
        ('condition', {
            'name': 'Test Condition',
            'config': {
                'conditions': [
                    {
                        'left': {'context_path': 'trigger_data.form_data.email'},
                        'operator': 'contains',
                        'right': {'value': '@example.com'},
                        'output': 'email_valid'
                    }
                ],
                'default_output': 'email_invalid'
            }
        }, 'Condition Node'),

        # Communication (skip if no API keys)
        ('unipile_send_email', {
            'name': 'Test Email',
            'config': {
                'user_id': '{{trigger_data.user_id}}',
                'recipient_email': '{{trigger_data.form_data.email}}',
                'subject': 'Thank you {{trigger_data.form_data.first_name}}',
                'content': 'We received your message: {{trigger_data.form_data.message}}'
            }
        }, 'Email Node (May fail without UniPile)'),

        # CRM Operations
        ('create_follow_up_task', {
            'name': 'Test Follow-up Task',
            'config': {
                'task_title': 'Follow up with {{trigger_data.form_data.first_name}}',
                'task_description': 'Contact regarding: {{trigger_data.form_data.message}}',
                'due_in_days': '3',
                'priority': 'medium',
                'pipeline_id': 'test-pipeline'
            }
        }, 'Follow-up Task Node'),

        ('update_contact_status', {
            'name': 'Test Contact Status',
            'config': {
                'contact_id_path': 'trigger_data.record_id',
                'new_status': 'qualified',
                'status_reason': 'Form submitted with interest'
            }
        }, 'Contact Status Update Node'),

        # Utility
        ('wait_delay', {
            'name': 'Test Wait',
            'config': {
                'delay_seconds': 1
            }
        }, 'Wait Delay Node'),

        ('task_notify', {
            'name': 'Test Notification',
            'config': {
                'notification_type': 'info',
                'title': 'Form Received',
                'message': 'New submission from {{trigger_data.form_data.first_name}}',
                'recipients': []
            }
        }, 'Task Notification Node'),

        # External
        ('http_request', {
            'name': 'Test HTTP Request',
            'config': {
                'method': 'POST',
                'url': 'https://httpbin.org/post',
                'payload': {
                    'name': '{{trigger_data.form_data.first_name}}',
                    'email': '{{trigger_data.form_data.email}}'
                }
            }
        }, 'HTTP Request Node'),

        ('webhook_out', {
            'name': 'Test Webhook',
            'config': {
                'webhook_url': 'https://httpbin.org/post',
                'payload': {
                    'event': 'form_submitted',
                    'data': '{{trigger_data.form_data}}'
                }
            }
        }, 'Webhook Out Node'),

        # Data Processing
        ('merge_data', {
            'name': 'Test Merge',
            'config': {
                'merge_sources': [
                    'trigger_data.form_data',
                    'trigger_data.record_data'
                ],
                'merge_strategy': 'combine'
            }
        }, 'Merge Data Node'),

        # Additional AI Nodes
        ('ai_message_generator', {
            'name': 'Test AI Message Generator',
            'config': {
                'persona': 'sales_rep',
                'tone': 'friendly',
                'message_type': 'follow_up',
                'context_data': 'trigger_data.form_data'
            }
        }, 'AI Message Generator Node'),

        ('ai_response_evaluator', {
            'name': 'Test Response Evaluator',
            'config': {
                'evaluation_criteria': {
                    'check_sentiment': True,
                    'check_intent': True,
                    'check_completeness': True
                },
                'response_path': 'trigger_data.form_data.message'
            }
        }, 'AI Response Evaluator Node'),

        ('ai_conversation_loop', {
            'name': 'Test AI Conversation',
            'config': {
                'max_iterations': 3,
                'conversation_goal': 'qualification',
                'ai_config': {
                    'model': 'gpt-3.5-turbo',
                    'temperature': 0.7
                }
            }
        }, 'AI Conversation Loop Node'),

        # Control Flow Extensions
        ('workflow_loop_controller', {
            'name': 'Test Workflow Loop',
            'config': {
                'loop_type': 'condition_based',
                'max_iterations': 5,
                'exit_conditions': [
                    {
                        'type': 'field_equals',
                        'field': 'status',
                        'value': 'completed'
                    }
                ]
            }
        }, 'Workflow Loop Controller'),

        ('for_each', {
            'name': 'Test For Each',
            'config': {
                'items_path': 'trigger_data.form_data',
                'max_concurrency': 3,
                'processing_mode': 'parallel'
            }
        }, 'For Each Loop Node'),

        # Communication Extensions
        ('unipile_send_whatsapp', {
            'name': 'Test WhatsApp',
            'config': {
                'user_id': 'test-user',
                'recipient_phone': '{{trigger_data.form_data.phone}}',
                'message': 'Thank you for your interest!'
            }
        }, 'WhatsApp Message Node'),

        ('unipile_send_linkedin', {
            'name': 'Test LinkedIn',
            'config': {
                'user_id': 'test-user',
                'recipient_profile': 'john-doe',
                'message': 'Thanks for connecting!'
            }
        }, 'LinkedIn Message Node'),

        ('unipile_send_sms', {
            'name': 'Test SMS',
            'config': {
                'user_id': 'test-user',
                'recipient_phone': '{{trigger_data.form_data.phone}}',
                'message': 'Your request has been received.'
            }
        }, 'SMS Message Node'),

        ('unipile_sync_messages', {
            'name': 'Test Message Sync',
            'config': {
                'user_id': 'test-user',
                'channels': ['email', 'whatsapp'],
                'sync_mode': 'incremental'
            }
        }, 'Message Sync Node'),

        ('log_communication', {
            'name': 'Test Communication Log',
            'config': {
                'record_id': '{{trigger_data.record_id}}',
                'communication_type': 'form_submission',
                'details': '{{trigger_data.form_data}}'
            }
        }, 'Communication Logging Node'),

        ('analyze_communication', {
            'name': 'Test Communication Analysis',
            'config': {
                'analysis_type': 'sentiment',
                'communication_data': 'trigger_data.form_data.message'
            }
        }, 'Communication Analysis Node'),

        ('score_engagement', {
            'name': 'Test Engagement Score',
            'config': {
                'scoring_method': 'weighted',
                'factors': {
                    'message_count': 0.3,
                    'response_time': 0.3,
                    'sentiment': 0.4
                }
            }
        }, 'Engagement Scoring Node'),

        # Utility Extensions
        ('conversation_state', {
            'name': 'Test Conversation State',
            'config': {
                'action': 'update',
                'state_key': 'test_conversation',
                'update_data': {
                    'last_message': '{{trigger_data.form_data.message}}',
                    'participant': '{{trigger_data.form_data.email}}'
                }
            }
        }, 'Conversation State Node'),

        ('wait_for_response', {
            'name': 'Test Wait Response',
            'config': {
                'timeout_seconds': 300,
                'response_type': 'email',
                'expected_sender': '{{trigger_data.form_data.email}}'
            }
        }, 'Wait for Response Node'),

        ('wait_for_record_event', {
            'name': 'Test Wait Record Event',
            'config': {
                'event_type': 'status_change',
                'record_id': '{{trigger_data.record_id}}',
                'timeout_seconds': 600
            }
        }, 'Wait for Record Event Node'),

        ('wait_for_condition', {
            'name': 'Test Wait Condition',
            'config': {
                'condition': {
                    'field': 'status',
                    'operator': 'equals',
                    'value': 'approved'
                },
                'check_interval_seconds': 60,
                'timeout_seconds': 3600
            }
        }, 'Wait for Condition Node'),

        # CRM Extensions
        ('resolve_contact', {
            'name': 'Test Contact Resolution',
            'config': {
                'email': '{{trigger_data.form_data.email}}',
                'create_if_not_found': True,
                'contact_data': {
                    'first_name': '{{trigger_data.form_data.first_name}}',
                    'last_name': '{{trigger_data.form_data.last_name}}',
                    'company': '{{trigger_data.form_data.company}}'
                }
            }
        }, 'Contact Resolution Node'),

        # Workflow Extensions
        ('sub_workflow', {
            'name': 'Test Sub-Workflow',
            'config': {
                'workflow_id': 'test-sub-workflow',
                'pass_context': True,
                'wait_for_completion': True
            }
        }, 'Sub-Workflow Node'),

        ('approval', {
            'name': 'Test Approval',
            'config': {
                'approval_type': 'single',
                'title': 'Approve form submission',
                'description': 'New submission from {{trigger_data.form_data.first_name}}',
                'assigned_to': 'manager@example.com',
                'timeout_hours': 24
            }
        }, 'Approval Node'),

        # Data Operations Extensions
        ('record_find', {
            'name': 'Test Record Find',
            'config': {
                'pipeline_id': 'test-pipeline',
                'search_criteria': {
                    'email': '{{trigger_data.form_data.email}}'
                },
                'return_first': True
            }
        }, 'Record Find Node'),

        ('record_delete', {
            'name': 'Test Record Delete',
            'config': {
                'record_id': '{{trigger_data.record_id}}',
                'soft_delete': True
            }
        }, 'Record Delete Node'),
    ]

    # Run tests
    print("\n" + "="*60)
    print("TESTING ALL WORKFLOW NODE PROCESSORS")
    print("="*60)

    success_count = 0
    fail_count = 0

    for node_type, config, name in test_cases:
        try:
            await test_node_processor(node_type, config, name)
            success_count += 1
        except Exception as e:
            fail_count += 1
            print(f"❌ Test failed for {name}: {e}")

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {len(test_cases)}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(test_all_processors())