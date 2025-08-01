"""
Comprehensive Integration Tests for Communications and Workflows with Phases 1-8
Tests end-to-end integration across all system components
"""
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

# Import tenant models (Phase 1)
from tenants.models import Tenant

# Import authentication models (Phase 2)
from authentication.models import User, UserType, UserSession
from authentication.permissions import AsyncPermissionManager

# Import pipeline models (Phase 3)
from pipelines.models import Pipeline, Field, Record

# Import relationship models (Phase 4)
from relationships.models import Relationship

# Import API layer (Phase 5)
from api.serializers import DynamicRecordSerializer
from api.views.pipelines import PipelineViewSet

# Import realtime features (Phase 6)
from realtime.consumers import CollaborativeEditingConsumer
from realtime.operational_transform import OperationalTransform

# Import workflow models and components (Phase 7-8)
from workflows.models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog,
    WorkflowStatus, ExecutionStatus, WorkflowTriggerType
)
from workflows.engine import workflow_engine
from workflows.triggers.manager import TriggerManager
from workflows.content.models import ContentLibrary, ContentAsset
from workflows.content.manager import ContentManager
from workflows.recovery.models import WorkflowCheckpoint, RecoveryStrategy
from workflows.recovery.manager import workflow_recovery_manager

# Import communication models
from communications.models import Channel, Conversation, Message
from communications.tracking.models import CommunicationTracking
from communications.tracking.manager import CommunicationTracker

# Import monitoring (Phase 9)
from monitoring.models import SystemHealthCheck, SystemMetrics
from monitoring.health import system_health_checker

User = get_user_model()


class ComprehensiveIntegrationTests(TenantTestCase):
    """Test comprehensive integration across all phases"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Integration Test Tenant",
            schema_name="test_comprehensive",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        """Set up comprehensive test environment"""
        # Phase 2: Authentication
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123'
        )
        
        self.regular_user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        
        # Create user types
        self.admin_type = UserType.objects.create(
            name='Admin',
            permissions={
                'pipelines': {'can_create': True, 'can_manage_all': True},
                'workflows': {'can_create': True, 'can_execute_all': True},
                'communications': {'can_create_channels': True, 'can_view_analytics': True},
                'relationships': {'can_create': True, 'can_traverse_all': True}
            }
        )
        
        self.admin_user.user_type = self.admin_type
        self.admin_user.save()
        
        # Phase 3: Pipeline System
        self.customer_pipeline = Pipeline.objects.create(
            name='Customer Pipeline',
            description='Customer relationship management',
            created_by=self.admin_user
        )
        
        # Create fields
        self.name_field = Field.objects.create(
            pipeline=self.customer_pipeline,
            name='name',
            field_type='text',
            is_required=True,
            created_by=self.admin_user
        )
        
        self.email_field = Field.objects.create(
            pipeline=self.customer_pipeline,
            name='email',
            field_type='email',
            is_required=True,
            created_by=self.admin_user
        )
        
        self.status_field = Field.objects.create(
            pipeline=self.customer_pipeline,
            name='status',
            field_type='choice',
            field_config={
                'choices': ['new', 'contacted', 'qualified', 'customer']
            },
            created_by=self.admin_user
        )
        
        # Create test customer records
        self.customer1 = Record.objects.create(
            pipeline=self.customer_pipeline,
            data={
                'name': 'John Doe',
                'email': 'john@example.com',
                'status': 'new',
                'company': 'Acme Corp'
            },
            created_by=self.admin_user
        )
        
        self.customer2 = Record.objects.create(
            pipeline=self.customer_pipeline,
            data={
                'name': 'Jane Smith',
                'email': 'jane@example.com',
                'status': 'contacted',
                'company': 'Tech Solutions'
            },
            created_by=self.admin_user
        )
        
        # Phase 4: Relationships
        self.relationship = Relationship.objects.create(
            from_record=self.customer1,
            to_record=self.customer2,
            relationship_type='colleague',
            is_bidirectional=True,
            created_by=self.admin_user
        )
        
        # Phase 8: Communications
        self.email_channel = Channel.objects.create(
            name='Customer Email Channel',
            channel_type='email',
            provider='unipile',
            configuration={
                'smtp_server': 'smtp.example.com',
                'from_email': 'system@example.com'
            },
            is_active=True,
            created_by=self.admin_user
        )
        
        # Phase 7: Workflow Content Management
        self.content_library = ContentLibrary.objects.create(
            name='Customer Communication Library',
            description='Templates for customer communications',
            library_type='templates',
            created_by=self.admin_user
        )
        
        self.content_manager = ContentManager()
        
        self.welcome_template = self.content_manager.create_text_content(
            name='Welcome Email Template',
            content_type='email_template',
            content_text='Welcome {customer_name}! We are excited to work with {company}.',
            library=self.content_library,
            created_by=self.admin_user,
            template_variables=['customer_name', 'company']
        )
        
        # Tracking system
        self.comm_tracker = CommunicationTracker()
    
    def test_end_to_end_customer_onboarding_workflow(self):
        """Test complete customer onboarding workflow integrating all phases"""
        
        # Phase 7: Create comprehensive workflow
        onboarding_workflow = Workflow.objects.create(
            name='Customer Onboarding Workflow',
            description='Complete customer onboarding process',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.RECORD_CREATED,
            status=WorkflowStatus.ACTIVE,
            category='communication',
            trigger_config={
                'pipeline_ids': [str(self.customer_pipeline.id)],
                'conditions': [
                    {
                        'field': 'status',
                        'operator': '==',
                        'value': 'new'
                    }
                ]
            },
            workflow_definition={
                'nodes': [
                    {
                        'id': 'check_customer_type',
                        'type': 'condition',
                        'data': {
                            'name': 'Check Customer Type',
                            'conditions': [
                                {
                                    'left': {'context_path': 'record.company'},
                                    'operator': 'not_empty',
                                    'right': None,
                                    'output': 'business_customer'
                                }
                            ],
                            'default_output': 'individual_customer'
                        }
                    },
                    {
                        'id': 'send_welcome_email',
                        'type': 'email_send',
                        'data': {
                            'name': 'Send Welcome Email',
                            'channel_id': str(self.email_channel.id),
                            'to_addresses': ['{record.email}'],
                            'subject': 'Welcome to our platform!',
                            'content_asset_id': str(self.welcome_template.id),
                            'track_delivery': True,
                            'track_reads': True
                        }
                    },
                    {
                        'id': 'update_status',
                        'type': 'record_update',
                        'data': {
                            'name': 'Update Customer Status',
                            'record_id_source': 'record_id',
                            'update_data': {
                                'status': 'contacted',
                                'contacted_at': '{timestamp}',
                                'contact_method': 'email'
                            }
                        }
                    },
                    {
                        'id': 'create_follow_up_task',
                        'type': 'record_create',
                        'data': {
                            'name': 'Create Follow-up Task',
                            'pipeline_id': str(self.customer_pipeline.id),
                            'record_data': {
                                'name': 'Follow up with {record.name}',
                                'type': 'task',
                                'due_date': '{date_plus_7_days}',
                                'assigned_to': '{workflow.created_by}',
                                'related_customer': '{record.id}'
                            }
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'check_customer_type', 'target': 'send_welcome_email'},
                    {'id': 'e2', 'source': 'send_welcome_email', 'target': 'update_status'},
                    {'id': 'e3', 'source': 'update_status', 'target': 'create_follow_up_task'}
                ]
            }
        )
        
        # Create workflow execution
        execution = WorkflowExecution.objects.create(
            workflow=onboarding_workflow,
            triggered_by=self.admin_user,
            trigger_data={'record_id': str(self.customer1.id)},
            execution_context={
                'record': self.customer1.data,
                'record_id': str(self.customer1.id),
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Test workflow structure
        self.assertEqual(len(onboarding_workflow.get_nodes()), 4)
        self.assertEqual(len(onboarding_workflow.get_edges()), 3)
        
        # Test execution context has all required data
        self.assertIn('record', execution.execution_context)
        self.assertEqual(execution.execution_context['record']['name'], 'John Doe')
        self.assertEqual(execution.execution_context['record']['status'], 'new')
        
        # Verify workflow can access customer data
        self.assertTrue(onboarding_workflow.can_execute())
        self.assertEqual(execution.status, ExecutionStatus.PENDING)
    
    @patch('communications.unipile_sdk.unipile_client.send_message')
    def test_workflow_communication_integration(self, mock_send_message):
        """Test workflow integration with communication system"""
        
        # Mock UniPile response
        mock_send_message.return_value = {
            'message_id': 'unipile_msg_123',
            'status': 'sent',
            'external_id': 'ext_123'
        }
        
        # Create simple email workflow
        email_workflow = Workflow.objects.create(
            name='Email Notification Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'send_notification',
                        'type': 'email_send',
                        'data': {
                            'name': 'Send Notification',
                            'channel_id': str(self.email_channel.id),
                            'to_addresses': ['{recipient.email}'],
                            'subject': 'Notification for {recipient.name}',
                            'body_text': 'Hello {recipient.name}, this is a test notification.',
                            'track_delivery': True
                        }
                    }
                ],
                'edges': []
            }
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=email_workflow,
            triggered_by=self.admin_user,
            trigger_data={
                'recipient': {
                    'name': 'John Doe',
                    'email': 'john@example.com'
                }
            },
            execution_context={
                'recipient': {
                    'name': 'John Doe',
                    'email': 'john@example.com'
                }
            }
        )
        
        # Test that workflow processor can access communication channel
        email_node = email_workflow.get_nodes()[0]
        self.assertEqual(email_node['type'], 'email_send')
        self.assertEqual(email_node['data']['channel_id'], str(self.email_channel.id))
        
        # Test communication tracking integration
        # In real execution, this would be called by the email processor
        conversation = Conversation.objects.create(
            channel=self.email_channel,
            external_thread_id='workflow_thread_123',
            subject='Notification for John Doe',
            participants=['john@example.com'],
            created_by=self.admin_user
        )
        
        message = Message.objects.create(
            conversation=conversation,
            channel=self.email_channel,
            external_message_id='workflow_msg_123',
            direction='outbound',
            content_text='Hello John Doe, this is a test notification.',
            sender_address='system@example.com',
            recipient_addresses=['john@example.com'],
            message_type='email',
            status='sent',
            created_by=self.admin_user
        )
        
        # Track message in workflow context
        tracking = self.comm_tracker.track_message_sent(
            message=message,
            workflow_execution_id=str(execution.id),
            tracking_data={'workflow_node': 'send_notification'}
        )
        
        self.assertIsInstance(tracking, CommunicationTracking)
        self.assertEqual(tracking.workflow_execution_id, str(execution.id))
        self.assertEqual(tracking.tracking_data['workflow_node'], 'send_notification')
    
    def test_pipeline_workflow_relationship_integration(self):
        """Test integration between pipelines, workflows, and relationships"""
        
        # Create relationship-aware workflow
        relationship_workflow = Workflow.objects.create(
            name='Relationship Processing Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'find_related_records',
                        'type': 'relationship_traverse',
                        'data': {
                            'name': 'Find Related Records',
                            'from_record_id': '{input.record_id}',
                            'relationship_types': ['colleague', 'partner'],
                            'max_depth': 2,
                            'return_path': True
                        }
                    },
                    {
                        'id': 'update_related_records',
                        'type': 'record_batch_update',
                        'data': {
                            'name': 'Update Related Records',
                            'record_ids_source': 'node_find_related_records.related_record_ids',
                            'update_data': {
                                'last_relationship_update': '{timestamp}',
                                'updated_via_workflow': True
                            }
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'find_related_records', 'target': 'update_related_records'}
                ]
            }
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=relationship_workflow,
            triggered_by=self.admin_user,
            trigger_data={'record_id': str(self.customer1.id)},
            execution_context={
                'input': {'record_id': str(self.customer1.id)},
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Test that workflow can access relationship data
        self.assertIn('input', execution.execution_context)
        self.assertEqual(execution.execution_context['input']['record_id'], str(self.customer1.id))
        
        # Verify relationship exists
        self.assertEqual(self.relationship.from_record, self.customer1)
        self.assertEqual(self.relationship.to_record, self.customer2)
        self.assertTrue(self.relationship.is_bidirectional)
    
    def test_content_management_workflow_integration(self):
        """Test content management integration with workflows"""
        
        # Create additional content assets
        email_signature = self.content_manager.create_text_content(
            name='Email Signature',
            content_type='text_snippet',
            content_text='\n\nBest regards,\n{sender_name}\n{company_name}',
            library=self.content_library,
            created_by=self.admin_user,
            template_variables=['sender_name', 'company_name']
        )
        
        # Create workflow using content library
        content_workflow = Workflow.objects.create(
            name='Content-Driven Email Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'compose_email',
                        'type': 'content_compose',
                        'data': {
                            'name': 'Compose Email with Templates',
                            'components': [
                                {
                                    'content_asset_id': str(self.welcome_template.id),
                                    'variables': {
                                        'customer_name': '{customer.name}',
                                        'company': '{customer.company}'
                                    }
                                },
                                {
                                    'content_asset_id': str(email_signature.id),
                                    'variables': {
                                        'sender_name': '{sender.name}',
                                        'company_name': 'Our Company'
                                    }
                                }
                            ]
                        }
                    },
                    {
                        'id': 'send_composed_email',
                        'type': 'email_send',
                        'data': {
                            'name': 'Send Composed Email',
                            'channel_id': str(self.email_channel.id),
                            'to_addresses': ['{customer.email}'],
                            'subject': 'Welcome!',
                            'body_text': '{node_compose_email.composed_content}',
                            'track_delivery': True
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'compose_email', 'target': 'send_composed_email'}
                ]
            }
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=content_workflow,
            triggered_by=self.admin_user,
            trigger_data={
                'customer': self.customer1.data,
                'sender': {'name': 'Admin User'}
            },
            execution_context={
                'customer': self.customer1.data,
                'sender': {'name': 'Admin User'}
            }
        )
        
        # Test content usage tracking
        usage = self.content_manager.track_content_usage(
            content_asset=self.welcome_template,
            workflow_id=str(content_workflow.id),
            workflow_name=content_workflow.name,
            node_id='compose_email'
        )
        
        self.assertEqual(usage.workflow_id, str(content_workflow.id))
        self.assertEqual(usage.node_id, 'compose_email')
        
        # Verify template usage count updated
        self.welcome_template.refresh_from_db()
        self.assertEqual(self.welcome_template.usage_count, 1)
    
    def test_workflow_recovery_integration(self):
        """Test workflow recovery system integration"""
        
        # Create workflow with recovery configuration
        recoverable_workflow = Workflow.objects.create(
            name='Recoverable Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            performance_config={
                'enable_checkpoints': True,
                'checkpoint_interval': 2,  # Every 2 nodes
                'max_execution_time_minutes': 30
            },
            workflow_definition={
                'nodes': [
                    {
                        'id': 'step1',
                        'type': 'record_update',
                        'data': {
                            'name': 'Update Record Step 1',
                            'record_id_source': 'record_id',
                            'update_data': {'step1_completed': True}
                        }
                    },
                    {
                        'id': 'step2',
                        'type': 'email_send',
                        'data': {
                            'name': 'Send Notification Step 2',
                            'channel_id': str(self.email_channel.id),
                            'to_addresses': ['admin@example.com'],
                            'subject': 'Step 2 completed',
                            'body_text': 'Step 2 has been completed'
                        }
                    },
                    {
                        'id': 'step3_risky',
                        'type': 'external_api_call',
                        'data': {
                            'name': 'Risky External API Call',
                            'url': 'https://api.example.com/risky-endpoint',
                            'timeout_seconds': 30
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'step1', 'target': 'step2'},
                    {'id': 'e2', 'source': 'step2', 'target': 'step3_risky'}
                ]
            }
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=recoverable_workflow,
            triggered_by=self.admin_user,
            trigger_data={'record_id': str(self.customer1.id)},
            execution_context={'record_id': str(self.customer1.id)}
        )
        
        # Create checkpoint
        checkpoint = workflow_recovery_manager.create_checkpoint(
            execution=execution,
            checkpoint_type='auto',
            node_id='step2',
            description='Checkpoint after step 2'
        )
        
        self.assertEqual(checkpoint.workflow, recoverable_workflow)
        self.assertEqual(checkpoint.execution, execution)
        self.assertEqual(checkpoint.node_id, 'step2')
        
        # Create recovery strategy
        strategy = workflow_recovery_manager.create_recovery_strategy(
            name='API Timeout Recovery',
            strategy_type='retry',
            description='Retry failed external API calls',
            workflow=recoverable_workflow,
            error_patterns=['timeout', 'connection'],
            max_retry_attempts=3,
            user=self.admin_user
        )
        
        self.assertEqual(strategy.workflow, recoverable_workflow)
        self.assertIn('timeout', strategy.error_patterns)
    
    def test_monitoring_integration(self):
        """Test monitoring system integration with workflows and communications"""
        
        # Test system health checks include workflow and communication components
        health_results = system_health_checker.run_all_checks()
        
        # Verify health checks cover integrated systems
        component_names = [result.component_name for result in health_results]
        
        # Should include core components
        self.assertIn('database', component_names)
        self.assertIn('cache', component_names)
        
        # Test workflow-specific metrics
        workflow_metrics = SystemMetrics.objects.create(
            metric_name='workflows.active_executions',
            metric_type='business',
            value=5,
            unit='count',
            tags={'component': 'workflow_engine'},
            metadata={'timestamp': timezone.now().isoformat()}
        )
        
        self.assertEqual(workflow_metrics.metric_name, 'workflows.active_executions')
        self.assertEqual(workflow_metrics.value, 5)
        
        # Test communication metrics
        comm_metrics = SystemMetrics.objects.create(
            metric_name='communications.messages_sent',
            metric_type='business',
            value=25,
            unit='count',
            tags={'channel_type': 'email'},
            metadata={'channel_id': str(self.email_channel.id)}
        )
        
        self.assertEqual(comm_metrics.metric_name, 'communications.messages_sent')
        self.assertEqual(comm_metrics.tags['channel_type'], 'email')
    
    def test_authentication_integration_across_systems(self):
        """Test authentication and permissions across all integrated systems"""
        
        # Test user can access workflow based on permissions
        admin_perms = self.admin_user.user_type.permissions
        
        # Workflow permissions
        self.assertTrue(admin_perms['workflows']['can_create'])
        self.assertTrue(admin_perms['workflows']['can_execute_all'])
        
        # Communication permissions
        self.assertTrue(admin_perms['communications']['can_create_channels'])
        self.assertTrue(admin_perms['communications']['can_view_analytics'])
        
        # Pipeline permissions
        self.assertTrue(admin_perms['pipelines']['can_create'])
        self.assertTrue(admin_perms['pipelines']['can_manage_all'])
        
        # Relationship permissions
        self.assertTrue(admin_perms['relationships']['can_create'])
        self.assertTrue(admin_perms['relationships']['can_traverse_all'])
        
        # Test session tracking
        session = UserSession.objects.create(
            user=self.admin_user,
            session_key='test_session_123',
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        self.assertEqual(session.user, self.admin_user)
        self.assertFalse(session.is_expired())
    
    @patch('workflows.nodes.ai.prompt.openai_client.chat.completions.create')
    @patch('communications.unipile_sdk.unipile_client.send_message')
    def test_ai_workflow_communication_integration(self, mock_send, mock_ai):
        """Test AI-powered workflow with communication integration"""
        
        # Mock AI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This customer appears to be interested in premium services based on their inquiry."
        mock_response.usage.total_tokens = 75
        mock_ai.return_value = mock_response
        
        # Mock communication response
        mock_send.return_value = {
            'message_id': 'ai_msg_123',
            'status': 'sent'
        }
        
        # Create AI-powered communication workflow
        ai_workflow = Workflow.objects.create(
            name='AI Customer Analysis and Response',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            ai_config={
                'enabled': True,
                'budget_limit_usd': 10.0,
                'model_preferences': ['gpt-4']
            },
            workflow_definition={
                'nodes': [
                    {
                        'id': 'analyze_customer',
                        'type': 'ai_prompt',
                        'data': {
                            'name': 'Analyze Customer Intent',
                            'prompt': 'Analyze this customer inquiry: {customer_message}. Customer details: {customer_data}',
                            'model': 'gpt-4',
                            'temperature': 0.3,
                            'max_tokens': 200
                        }
                    },
                    {
                        'id': 'update_customer_profile',
                        'type': 'record_update',
                        'data': {
                            'name': 'Update Customer Profile',
                            'record_id_source': 'customer_id',
                            'update_data': {
                                'ai_analysis': '{node_analyze_customer.content}',
                                'analysis_date': '{timestamp}',
                                'tokens_used': '{node_analyze_customer.tokens_used}'
                            }
                        }
                    },
                    {
                        'id': 'send_personalized_response',
                        'type': 'email_send',
                        'data': {
                            'name': 'Send AI-Personalized Response',
                            'channel_id': str(self.email_channel.id),
                            'to_addresses': ['{customer_email}'],
                            'subject': 'Re: Your Inquiry',
                            'body_text': 'Thank you for your message. {node_analyze_customer.content}',
                            'track_delivery': True,
                            'track_reads': True
                        }
                    }
                ],
                'edges': [
                    {'id': 'e1', 'source': 'analyze_customer', 'target': 'update_customer_profile'},
                    {'id': 'e2', 'source': 'update_customer_profile', 'target': 'send_personalized_response'}
                ]
            }
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=ai_workflow,
            triggered_by=self.admin_user,
            trigger_data={
                'customer_id': str(self.customer1.id),
                'customer_email': self.customer1.data['email'],
                'customer_message': 'I am interested in your premium services',
                'customer_data': self.customer1.data
            },
            execution_context={
                'customer_id': str(self.customer1.id),
                'customer_email': self.customer1.data['email'],
                'customer_message': 'I am interested in your premium services',
                'customer_data': self.customer1.data,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Test AI configuration
        self.assertTrue(ai_workflow.ai_config['enabled'])
        self.assertEqual(ai_workflow.ai_config['budget_limit_usd'], 10.0)
        
        # Test workflow structure integrates AI, pipeline updates, and communication
        nodes = ai_workflow.get_nodes()
        self.assertEqual(len(nodes), 3)
        
        ai_node = nodes[0]
        update_node = nodes[1]
        email_node = nodes[2]
        
        self.assertEqual(ai_node['type'], 'ai_prompt')
        self.assertEqual(update_node['type'], 'record_update')
        self.assertEqual(email_node['type'], 'email_send')
        
        # Test data flow between nodes
        self.assertIn('customer_message', ai_node['data']['prompt'])
        self.assertIn('node_analyze_customer.content', update_node['data']['update_data']['ai_analysis'])
        self.assertIn('node_analyze_customer.content', email_node['data']['body_text'])
    
    def test_real_time_collaboration_integration(self):
        """Test real-time features integration with workflows and communications"""
        
        # Test operational transform for workflow collaboration
        ot = OperationalTransform()
        
        # Simulate concurrent workflow editing
        original_workflow_def = {
            'nodes': [
                {'id': 'node1', 'type': 'condition', 'data': {'name': 'Check Status'}}
            ],
            'edges': []
        }
        
        # Operation 1: Add new node
        op1 = {
            'type': 'INSERT',
            'position': 1,
            'content': {'id': 'node2', 'type': 'email_send', 'data': {'name': 'Send Email'}}
        }
        
        # Operation 2: Modify existing node (concurrent)
        op2 = {
            'type': 'REPLACE',
            'position': 0,
            'content': {'id': 'node1', 'type': 'condition', 'data': {'name': 'Check Customer Status'}}
        }
        
        # Transform operations
        transformed_ops = ot.transform_operations([op1, op2])
        
        self.assertEqual(len(transformed_ops), 2)
        self.assertIn('type', transformed_ops[0])
        
        # Test that workflow can be updated through real-time collaboration
        workflow_collab = Workflow.objects.create(
            name='Collaborative Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition=original_workflow_def
        )
        
        self.assertEqual(len(workflow_collab.get_nodes()), 1)
        self.assertEqual(workflow_collab.get_nodes()[0]['data']['name'], 'Check Status')
    
    def test_api_layer_integration(self):
        """Test API layer integration across all systems"""
        
        # Test that workflow data can be serialized through API layer
        from workflows.serializers import WorkflowSerializer
        
        workflow = Workflow.objects.create(
            name='API Test Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        serializer = WorkflowSerializer(workflow)
        workflow_data = serializer.data
        
        self.assertEqual(workflow_data['name'], 'API Test Workflow')
        self.assertIn('workflow_definition', workflow_data)
        
        # Test pipeline API integration
        pipeline_serializer = DynamicRecordSerializer(self.customer1, context={'pipeline': self.customer_pipeline})
        record_data = pipeline_serializer.data
        
        self.assertEqual(record_data['name'], 'John Doe')
        self.assertEqual(record_data['email'], 'john@example.com')
        
        # Test communication API integration
        from communications.serializers import ChannelSerializer
        
        channel_serializer = ChannelSerializer(self.email_channel)
        channel_data = channel_serializer.data
        
        self.assertEqual(channel_data['name'], 'Customer Email Channel')
        self.assertEqual(channel_data['channel_type'], 'email')


class PerformanceIntegrationTests(TenantTestCase):
    """Test performance across integrated systems"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Performance Test Tenant",
            schema_name="test_performance",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='perf@example.com',
            password='testpass123'
        )
    
    def test_bulk_workflow_execution_performance(self):
        """Test performance with multiple concurrent workflow executions"""
        import time
        
        # Create simple workflow
        workflow = Workflow.objects.create(
            name='Performance Test Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'simple_condition',
                        'type': 'condition',
                        'data': {
                            'name': 'Simple Check',
                            'conditions': [
                                {
                                    'left': {'context_path': 'input.value'},
                                    'operator': '>',
                                    'right': 0,
                                    'output': 'positive'
                                }
                            ],
                            'default_output': 'negative'
                        }
                    }
                ],
                'edges': []
            }
        )
        
        # Create multiple executions
        start_time = time.time()
        
        executions = []
        for i in range(50):
            execution = WorkflowExecution.objects.create(
                workflow=workflow,
                triggered_by=self.user,
                trigger_data={'input': {'value': i}},
                execution_context={'input': {'value': i}}
            )
            executions.append(execution)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 50 executions in under 2 seconds
        self.assertLess(creation_time, 2.0)
        self.assertEqual(len(executions), 50)
        
        # Test all executions have correct data
        for i, execution in enumerate(executions):
            self.assertEqual(execution.execution_context['input']['value'], i)
    
    def test_communication_tracking_performance(self):
        """Test communication tracking performance with large datasets"""
        import time
        
        # Create channel and conversations
        channel = Channel.objects.create(
            name='Performance Channel',
            channel_type='email',
            provider='unipile',
            configuration={},
            created_by=self.user
        )
        
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id='perf_conversation',
            subject='Performance Test',
            participants=['test@example.com'],
            created_by=self.user
        )
        
        # Create messages and track them
        tracker = CommunicationTracker()
        
        start_time = time.time()
        
        for i in range(100):
            message = Message.objects.create(
                conversation=conversation,
                channel=channel,
                external_message_id=f'perf_msg_{i}',
                direction='outbound',
                content_text=f'Performance test message {i}',
                sender_address='system@example.com',
                recipient_addresses=['test@example.com'],
                message_type='email',
                status='sent',
                created_by=self.user
            )
            
            # Track message
            tracker.track_message_sent(message)
            tracker.track_delivery_success(message, timezone.now(), 1000)
        
        end_time = time.time()
        tracking_time = end_time - start_time
        
        # Should process 100 messages with tracking in under 3 seconds
        self.assertLess(tracking_time, 3.0)
        
        # Verify all tracking records created
        self.assertEqual(CommunicationTracking.objects.count(), 100)


if __name__ == '__main__':
    import django
    django.setup()
    
    # Run tests
    import unittest
    unittest.main()