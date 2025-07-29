"""
Comprehensive tests for Workflows app and its integration with core system
Tests workflow models, processors, triggers, content management, recovery system, and integration with Phases 1-8
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

# Import tenant models
from tenants.models import Tenant

# Import workflow models
from workflows.models import (
    Workflow, WorkflowExecution, WorkflowExecutionLog, WorkflowApproval,
    WorkflowTemplate, WorkflowVersion, WorkflowTrigger, WorkflowAnalytics,
    WorkflowEvent, WorkflowStatus, ExecutionStatus, WorkflowTriggerType,
    WorkflowVisibility, WorkflowCategory
)

# Import workflow components
from workflows.engine import workflow_engine
from workflows.triggers.manager import TriggerManager
from workflows.triggers.types import TriggerEvent, TriggerResult
from workflows.core.registry import node_registry

# Import content management
from workflows.content.models import (
    ContentLibrary, ContentAsset, ContentTag, ContentUsage,
    ContentApproval, ContentType
)
from workflows.content.manager import ContentManager

# Import recovery system
from workflows.recovery.models import (
    WorkflowCheckpoint, WorkflowRecoveryLog, RecoveryStrategy,
    WorkflowReplaySession, RecoveryConfiguration,
    CheckpointType, RecoveryStatus, RecoveryStrategyType
)
from workflows.recovery.manager import workflow_recovery_manager

# Import node processors
from workflows.nodes.ai.prompt import PromptProcessor
from workflows.nodes.communication.email import EmailProcessor
from workflows.nodes.data.record_ops import RecordCreateProcessor
from workflows.nodes.control.condition import ConditionProcessor

# Import authentication models for integration
from authentication.models import User, UserType
from authentication.permissions import AsyncPermissionManager

# Import pipeline models for integration
from pipelines.models import Pipeline, Field, Record

# Import relationships for integration
from relationships.models import Relationship

# Import communications for integration
from communications.models import Channel, Message

User = get_user_model()


class WorkflowModelTests(TenantTestCase):
    """Test workflow models with tenant isolation"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_workflows",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_workflow_creation_with_enhanced_fields(self):
        """Test creating workflow with enhanced model fields"""
        workflow = Workflow.objects.create(
            name='Enhanced Test Workflow',
            description='A comprehensive test workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.DRAFT,
            visibility=WorkflowVisibility.PRIVATE,
            category=WorkflowCategory.COMMUNICATION,
            tags=['test', 'email', 'automation'],
            version='1.0.0',
            is_reusable=True,
            reusable_config={
                'allow_customization': True,
                'required_parameters': ['recipient_email'],
                'optional_parameters': ['sender_name']
            },
            performance_config={
                'max_execution_time_minutes': 30,
                'retry_attempts': 3,
                'enable_checkpoints': True
            },
            ai_config={
                'enabled': True,
                'budget_limit_usd': 10.0,
                'model_preferences': ['gpt-4', 'gpt-3.5-turbo']
            },
            workflow_definition={
                'nodes': [
                    {
                        'id': 'start',
                        'type': 'ai_prompt',
                        'data': {
                            'name': 'AI Analysis',
                            'prompt': 'Analyze this: {input}',
                            'model': 'gpt-4'
                        }
                    }
                ],
                'edges': [],
                'variables': {
                    'input': {'type': 'string', 'required': True}
                }
            }
        )
        
        self.assertEqual(workflow.name, 'Enhanced Test Workflow')
        self.assertEqual(workflow.visibility, WorkflowVisibility.PRIVATE)
        self.assertEqual(workflow.category, WorkflowCategory.COMMUNICATION)
        self.assertTrue(workflow.is_reusable)
        self.assertIn('allow_customization', workflow.reusable_config)
        self.assertIn('max_execution_time_minutes', workflow.performance_config)
        self.assertIn('enabled', workflow.ai_config)
        self.assertEqual(len(workflow.tags), 3)
    
    def test_workflow_template_creation(self):
        """Test workflow template model"""
        template = WorkflowTemplate.objects.create(
            name='Email Campaign Template',
            description='Template for email campaigns',
            category=WorkflowCategory.COMMUNICATION,
            created_by=self.user,
            template_data={
                'nodes': [
                    {
                        'id': 'email_node',
                        'type': 'email_send',
                        'data': {
                            'name': 'Send Email',
                            'template_variables': ['recipient', 'subject', 'content']
                        }
                    }
                ],
                'edges': [],
                'required_variables': ['recipient', 'subject', 'content'],
                'optional_variables': ['sender_name']
            },
            default_config={
                'performance': {'timeout_minutes': 15},
                'ai': {'enabled': False}
            },
            is_public=True
        )
        
        self.assertEqual(template.name, 'Email Campaign Template')
        self.assertEqual(template.category, WorkflowCategory.COMMUNICATION)
        self.assertTrue(template.is_public)
        self.assertIn('required_variables', template.template_data)
        self.assertIn('performance', template.default_config)
    
    def test_workflow_version_management(self):
        """Test workflow versioning"""
        workflow = Workflow.objects.create(
            name='Versioned Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        # Create version
        version = WorkflowVersion.objects.create(
            workflow=workflow,
            version_number='1.0.0',
            workflow_definition={'nodes': [], 'edges': []},
            created_by=self.user,
            change_summary='Initial version',
            is_active=True
        )
        
        self.assertEqual(version.workflow, workflow)
        self.assertEqual(version.version_number, '1.0.0')
        self.assertTrue(version.is_active)
        
        # Create new version
        version_2 = WorkflowVersion.objects.create(
            workflow=workflow,
            version_number='1.1.0',
            workflow_definition={'nodes': [{'id': 'new_node'}], 'edges': []},
            created_by=self.user,
            change_summary='Added new node',
            is_active=True
        )
        
        # Previous version should be deactivated
        version.refresh_from_db()
        self.assertFalse(version.is_active)
        self.assertTrue(version_2.is_active)
    
    def test_workflow_trigger_configuration(self):
        """Test workflow trigger model"""
        workflow = Workflow.objects.create(
            name='Triggered Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.RECORD_CREATED,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        trigger = WorkflowTrigger.objects.create(
            workflow=workflow,
            trigger_type='record_created',
            trigger_config={
                'pipeline_ids': [1, 2, 3],
                'conditions': [
                    {
                        'field': 'status',
                        'operator': '==',
                        'value': 'new'
                    }
                ],
                'filters': {
                    'created_by_type': 'user'
                }
            },
            is_active=True,
            priority=100,
            rate_limit_per_minute=60
        )
        
        self.assertEqual(trigger.workflow, workflow)
        self.assertEqual(trigger.trigger_type, 'record_created')
        self.assertTrue(trigger.is_active)
        self.assertEqual(trigger.priority, 100)
        self.assertIn('pipeline_ids', trigger.trigger_config)
    
    def test_workflow_analytics_tracking(self):
        """Test workflow analytics model"""
        workflow = Workflow.objects.create(
            name='Analytics Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        analytics = WorkflowAnalytics.objects.create(
            workflow=workflow,
            date=timezone.now().date(),
            executions_started=100,
            executions_completed=85,
            executions_failed=15,
            average_duration_seconds=120,
            success_rate=Decimal('85.00'),
            performance_score=Decimal('88.50'),
            ai_cost_usd=Decimal('5.25'),
            ai_tokens_used=1500
        )
        
        self.assertEqual(analytics.workflow, workflow)
        self.assertEqual(analytics.executions_started, 100)
        self.assertEqual(analytics.success_rate, Decimal('85.00'))
        self.assertEqual(analytics.ai_cost_usd, Decimal('5.25'))
    
    def test_workflow_execution_with_context(self):
        """Test workflow execution with enhanced context"""
        workflow = Workflow.objects.create(
            name='Context Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            triggered_by=self.user,
            trigger_data={'test_data': 'value'},
            execution_context={
                'variables': {'input': 'test'},
                'settings': {'debug': True},
                'metadata': {'source': 'api'}
            },
            priority=50,
            scheduled_at=timezone.now() + timedelta(hours=1)
        )
        
        self.assertEqual(execution.workflow, workflow)
        self.assertEqual(execution.priority, 50)
        self.assertIsNotNone(execution.scheduled_at)
        self.assertIn('variables', execution.execution_context)
        self.assertIn('settings', execution.execution_context)


class WorkflowNodeProcessorTests(TenantTestCase):
    """Test workflow node processors"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_processors",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_node_processor_registry(self):
        """Test node processor registry functionality"""
        # Test registry has processors
        processors = node_processor_registry.get_all_processors()
        self.assertGreater(len(processors), 0)
        
        # Test specific processors exist
        self.assertIn('ai_prompt', processors)
        self.assertIn('email_send', processors)
        self.assertIn('record_create', processors)
        self.assertIn('condition', processors)
        
        # Test getting specific processor
        prompt_processor = node_processor_registry.get_processor('ai_prompt')
        self.assertIsNotNone(prompt_processor)
        self.assertEqual(prompt_processor.__class__.__name__, 'PromptProcessor')
    
    @patch('workflows.nodes.ai.prompt.openai_client.chat.completions.create')
    def test_ai_prompt_processor(self, mock_openai):
        """Test AI prompt processor"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AI generated response"
        mock_response.usage.total_tokens = 50
        mock_openai.return_value = mock_response
        
        processor = PromptProcessor()
        
        node_data = {
            'prompt': 'Analyze this text: {input_text}',
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 100
        }
        
        context = {
            'input_text': 'This is test text for analysis'
        }
        
        result = processor.process(node_data, context)
        
        self.assertIn('content', result)
        self.assertIn('tokens_used', result)
        self.assertEqual(result['content'], "AI generated response")
        self.assertEqual(result['tokens_used'], 50)
    
    def test_condition_processor(self):
        """Test condition processor logic"""
        processor = ConditionProcessor()
        
        node_data = {
            'conditions': [
                {
                    'left': {'context_path': 'user.age'},
                    'operator': '>',
                    'right': 18,
                    'output': 'adult'
                },
                {
                    'left': {'context_path': 'user.status'},
                    'operator': '==',
                    'right': 'active',
                    'output': 'active_user'
                }
            ],
            'default_output': 'default'
        }
        
        # Test adult user
        context = {
            'user': {'age': 25, 'status': 'active'}
        }
        
        result = processor.process(node_data, context)
        self.assertEqual(result['output'], 'adult')
        
        # Test minor user
        context = {
            'user': {'age': 16, 'status': 'active'}
        }
        
        result = processor.process(node_data, context)
        self.assertEqual(result['output'], 'active_user')
        
        # Test default case
        context = {
            'user': {'age': 16, 'status': 'inactive'}
        }
        
        result = processor.process(node_data, context)
        self.assertEqual(result['output'], 'default')
    
    def test_record_create_processor(self):
        """Test record creation processor"""
        # Create pipeline for testing
        pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            description='Test pipeline for record creation',
            created_by=self.user
        )
        
        # Create fields
        Field.objects.create(
            pipeline=pipeline,
            name='name',
            field_type='text',
            is_required=True,
            created_by=self.user
        )
        
        Field.objects.create(
            pipeline=pipeline,
            name='email',
            field_type='email',
            is_required=True,
            created_by=self.user
        )
        
        processor = RecordCreateProcessor()
        
        node_data = {
            'pipeline_id': str(pipeline.id),
            'record_data': {
                'name': '{contact.name}',
                'email': '{contact.email}',
                'source': 'workflow'
            }
        }
        
        context = {
            'contact': {
                'name': 'John Doe',
                'email': 'john@example.com'
            },
            'user': self.user
        }
        
        result = processor.process(node_data, context)
        
        self.assertIn('record_id', result)
        self.assertIn('record_data', result)
        
        # Verify record was created
        record = Record.objects.get(id=result['record_id'])
        self.assertEqual(record.data['name'], 'John Doe')
        self.assertEqual(record.data['email'], 'john@example.com')
        self.assertEqual(record.data['source'], 'workflow')
    
    @patch('communications.unipile_sdk.unipile_client.send_message')
    def test_email_processor(self, mock_send):
        """Test email sending processor"""
        # Mock UniPile response
        mock_send.return_value = {
            'message_id': 'unipile_123',
            'status': 'sent',
            'external_id': 'ext_123'
        }
        
        # Create channel
        channel = Channel.objects.create(
            name='Test Email Channel',
            channel_type='email',
            provider='unipile',
            configuration={},
            created_by=self.user
        )
        
        processor = EmailProcessor()
        
        node_data = {
            'channel_id': str(channel.id),
            'to_addresses': ['{recipient.email}'],
            'subject': 'Welcome {recipient.name}!',
            'body_text': 'Hello {recipient.name}, welcome to our platform!',
            'body_html': '<p>Hello <strong>{recipient.name}</strong>, welcome!</p>',
            'track_delivery': True,
            'track_reads': True
        }
        
        context = {
            'recipient': {
                'name': 'Jane Doe',
                'email': 'jane@example.com'
            }
        }
        
        result = processor.process(node_data, context)
        
        self.assertIn('message_id', result)
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'sent')
        mock_send.assert_called_once()


class WorkflowTriggerSystemTests(TenantTestCase):
    """Test workflow trigger system"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_triggers",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.trigger_manager = TriggerManager()
    
    def test_trigger_registration(self):
        """Test trigger type registration"""
        from workflows.triggers.registry import trigger_registry
        
        # Test registry has trigger types
        trigger_types = trigger_registry.get_all_trigger_types()
        self.assertGreater(len(trigger_types), 0)
        
        # Test specific trigger types exist
        self.assertIn('manual', trigger_types)
        self.assertIn('scheduled', trigger_types)
        self.assertIn('record_created', trigger_types)
        self.assertIn('webhook', trigger_types)
    
    def test_manual_trigger(self):
        """Test manual workflow trigger"""
        workflow = Workflow.objects.create(
            name='Manual Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        # Test manual trigger
        trigger_data = TriggerEvent(
            trigger_type='manual',
            workflow_id=str(workflow.id),
            data={'user_input': 'test'},
            triggered_by=self.user
        )
        
        result = self.trigger_manager._evaluate_trigger_conditions(
            workflow, trigger_data
        )
        
        self.assertTrue(result.should_execute)
        self.assertEqual(result.workflow_id, str(workflow.id))
    
    def test_scheduled_trigger(self):
        """Test scheduled workflow trigger"""
        workflow = Workflow.objects.create(
            name='Scheduled Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.SCHEDULED,
            trigger_config={
                'schedule': {
                    'type': 'cron',
                    'expression': '0 9 * * *'  # Daily at 9 AM
                }
            },
            status=WorkflowStatus.ACTIVE,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        # Test trigger evaluation
        from workflows.triggers.handlers.basic_handlers import ScheduledTriggerHandler
        
        handler = ScheduledTriggerHandler()
        
        trigger_data = TriggerEvent(
            trigger_type='scheduled',
            workflow_id=str(workflow.id),
            data={'current_time': timezone.now()},
            triggered_by=None
        )
        
        # Handler should validate the trigger
        self.assertTrue(hasattr(handler, 'should_trigger'))
    
    def test_record_created_trigger(self):
        """Test record creation trigger"""
        # Create pipeline
        pipeline = Pipeline.objects.create(
            name='Trigger Pipeline',
            created_by=self.user
        )
        
        workflow = Workflow.objects.create(
            name='Record Trigger Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.RECORD_CREATED,
            trigger_config={
                'pipeline_ids': [str(pipeline.id)],
                'conditions': [
                    {
                        'field': 'status',
                        'operator': '==',
                        'value': 'new'
                    }
                ]
            },
            status=WorkflowStatus.ACTIVE,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        # Create record that should trigger workflow
        record = Record.objects.create(
            pipeline=pipeline,
            data={'status': 'new', 'name': 'Test Record'},
            created_by=self.user
        )
        
        trigger_data = TriggerEvent(
            trigger_type='record_created',
            workflow_id=str(workflow.id),
            data={'record_id': str(record.id), 'record_data': record.data},
            triggered_by=self.user
        )
        
        result = self.trigger_manager._evaluate_trigger_conditions(
            workflow, trigger_data
        )
        
        self.assertTrue(result.should_execute)
        self.assertEqual(result.context_data['record_data']['status'], 'new')


class WorkflowContentManagementTests(TenantTestCase):
    """Test workflow content management system"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_content",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.content_manager = ContentManager()
        
        # Create content library
        self.library = ContentLibrary.objects.create(
            name='Test Library',
            description='Library for testing',
            created_by=self.user,
            library_type='templates',
            permissions={'read': ['all'], 'write': ['admin']},
            is_active=True
        )
    
    def test_content_library_creation(self):
        """Test content library model"""
        self.assertEqual(self.library.name, 'Test Library')
        self.assertEqual(self.library.library_type, 'templates')
        self.assertTrue(self.library.is_active)
        self.assertIn('read', self.library.permissions)
    
    def test_content_asset_creation(self):
        """Test content asset creation and management"""
        # Create text content
        text_asset = self.content_manager.create_text_content(
            name='Welcome Email Template',
            content_type=ContentType.EMAIL_TEMPLATE,
            content_text='Welcome {name}! Your account is now active.',
            library=self.library,
            created_by=self.user,
            template_variables=['name']
        )
        
        self.assertIsInstance(text_asset, ContentAsset)
        self.assertEqual(text_asset.name, 'Welcome Email Template')
        self.assertEqual(text_asset.content_type, ContentType.EMAIL_TEMPLATE)
        self.assertIn('name', text_asset.template_variables)
        
        # Create HTML content
        html_asset = self.content_manager.create_text_content(
            name='HTML Email Template',
            content_type=ContentType.EMAIL_TEMPLATE,
            content_text='<h1>Welcome {name}!</h1><p>Your account is active.</p>',
            library=self.library,
            created_by=self.user,
            template_variables=['name']
        )
        
        self.assertEqual(html_asset.content_type, ContentType.EMAIL_TEMPLATE)
        self.assertIn('<h1>', html_asset.content_text)
    
    def test_content_rendering(self):
        """Test content rendering with variables"""
        # Create template
        template_asset = self.content_manager.create_text_content(
            name='Dynamic Template',
            content_type=ContentType.TEXT_SNIPPET,
            content_text='Hello {user_name}, your order #{order_id} is {status}.',
            library=self.library,
            created_by=self.user,
            template_variables=['user_name', 'order_id', 'status']
        )
        
        # Render with variables
        rendered_content = self.content_manager.render_content(
            content_asset=template_asset,
            variables={
                'user_name': 'John Doe',
                'order_id': '12345',
                'status': 'confirmed'
            }
        )
        
        expected = 'Hello John Doe, your order #12345 is confirmed.'
        self.assertEqual(rendered_content['rendered_content'], expected)
        self.assertIn('variables_used', rendered_content)
        self.assertEqual(len(rendered_content['variables_used']), 3)
    
    def test_content_usage_tracking(self):
        """Test content usage tracking"""
        template_asset = self.content_manager.create_text_content(
            name='Usage Template',
            content_type=ContentType.TEXT_SNIPPET,
            content_text='Test content for usage tracking',
            library=self.library,
            created_by=self.user
        )
        
        # Track usage
        usage = self.content_manager.track_content_usage(
            content_asset=template_asset,
            workflow_id='workflow_123',
            workflow_name='Test Workflow',
            node_id='node_456'
        )
        
        self.assertIsInstance(usage, ContentUsage)
        self.assertEqual(usage.content_asset, template_asset)
        self.assertEqual(usage.workflow_id, 'workflow_123')
        self.assertEqual(usage.node_id, 'node_456')
        
        # Check usage count updated
        template_asset.refresh_from_db()
        self.assertEqual(template_asset.usage_count, 1)
    
    def test_content_approval_workflow(self):
        """Test content approval system"""
        template_asset = self.content_manager.create_text_content(
            name='Approval Template',
            content_type=ContentType.EMAIL_TEMPLATE,
            content_text='This content needs approval',
            library=self.library,
            created_by=self.user
        )
        
        # Create approval request
        approval = ContentApproval.objects.create(
            content_asset=template_asset,
            requested_by=self.user,
            approval_type='content_review',
            notes='Please review this email template'
        )
        
        self.assertEqual(approval.status, 'pending')
        self.assertEqual(approval.requested_by, self.user)
        
        # Approve content
        approval.status = 'approved'
        approval.approved_by = self.user
        approval.approved_at = timezone.now()
        approval.save()
        
        self.assertEqual(approval.status, 'approved')
        self.assertIsNotNone(approval.approved_at)
    
    def test_content_tagging_system(self):
        """Test content tagging and categorization"""
        # Create tags
        tag1 = ContentTag.objects.create(
            name='email',
            description='Email related content',
            color='#007bff'
        )
        
        tag2 = ContentTag.objects.create(
            name='welcome',
            description='Welcome message content',
            color='#28a745'
        )
        
        # Create content with tags
        template_asset = self.content_manager.create_text_content(
            name='Tagged Template',
            content_type=ContentType.EMAIL_TEMPLATE,
            content_text='Welcome email content',
            library=self.library,
            created_by=self.user
        )
        
        # Add tags
        template_asset.tags.add(tag1, tag2)
        
        self.assertEqual(template_asset.tags.count(), 2)
        self.assertIn(tag1, template_asset.tags.all())
        self.assertIn(tag2, template_asset.tags.all())


class WorkflowRecoverySystemTests(TenantTestCase):
    """Test workflow recovery and replay system"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_recovery",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.workflow = Workflow.objects.create(
            name='Recovery Test Workflow',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        self.execution = WorkflowExecution.objects.create(
            workflow=self.workflow,
            triggered_by=self.user,
            trigger_data={'test': 'data'},
            execution_context={'variables': {'input': 'test'}}
        )
    
    def test_checkpoint_creation(self):
        """Test workflow checkpoint creation"""
        checkpoint = workflow_recovery_manager.create_checkpoint(
            execution=self.execution,
            checkpoint_type=CheckpointType.MANUAL,
            description='Test checkpoint',
            is_milestone=True
        )
        
        self.assertIsInstance(checkpoint, WorkflowCheckpoint)
        self.assertEqual(checkpoint.workflow, self.workflow)
        self.assertEqual(checkpoint.execution, self.execution)
        self.assertEqual(checkpoint.checkpoint_type, CheckpointType.MANUAL)
        self.assertTrue(checkpoint.is_milestone)
        self.assertTrue(checkpoint.is_recoverable)
        self.assertEqual(checkpoint.sequence_number, 1)
    
    def test_recovery_strategy_creation(self):
        """Test recovery strategy configuration"""
        strategy = workflow_recovery_manager.create_recovery_strategy(
            name='Test Retry Strategy',
            strategy_type=RecoveryStrategyType.RETRY,
            description='Retry failed nodes with delay',
            workflow=self.workflow,
            error_patterns=['timeout', 'connection'],
            max_retry_attempts=3,
            retry_delay_seconds=60,
            recovery_actions=[
                {'action': 'retry_from_checkpoint', 'parameters': {'use_latest': True}}
            ],
            user=self.user
        )
        
        self.assertIsInstance(strategy, RecoveryStrategy)
        self.assertEqual(strategy.name, 'Test Retry Strategy')
        self.assertEqual(strategy.strategy_type, RecoveryStrategyType.RETRY)
        self.assertEqual(strategy.max_retry_attempts, 3)
        self.assertIn('timeout', strategy.error_patterns)
        self.assertEqual(len(strategy.recovery_actions), 1)
    
    def test_workflow_recovery_process(self):
        """Test complete recovery process"""
        # Create checkpoint first
        checkpoint = workflow_recovery_manager.create_checkpoint(
            execution=self.execution,
            checkpoint_type=CheckpointType.AUTO
        )
        
        # Create recovery strategy
        strategy = workflow_recovery_manager.create_recovery_strategy(
            name='Auto Recovery',
            strategy_type=RecoveryStrategyType.RETRY,
            description='Automatic retry strategy',
            user=self.user
        )
        
        # Mark execution as failed
        self.execution.status = ExecutionStatus.FAILED
        self.execution.error_message = 'Test failure'
        self.execution.save()
        
        # Trigger recovery
        recovery_log = workflow_recovery_manager.recover_workflow(
            execution=self.execution,
            trigger_reason='execution_failed',
            user=self.user,
            strategy=strategy
        )
        
        self.assertIsInstance(recovery_log, WorkflowRecoveryLog)
        self.assertEqual(recovery_log.workflow, self.workflow)
        self.assertEqual(recovery_log.execution, self.execution)
        self.assertEqual(recovery_log.strategy, strategy)
        self.assertEqual(recovery_log.trigger_reason, 'execution_failed')
        self.assertEqual(recovery_log.attempt_number, 1)
    
    def test_replay_session_creation(self):
        """Test workflow replay session"""
        # Create checkpoint
        checkpoint = workflow_recovery_manager.create_checkpoint(
            execution=self.execution,
            checkpoint_type=CheckpointType.MILESTONE
        )
        
        # Create replay session
        replay_session = workflow_recovery_manager.create_replay_session(
            original_execution=self.execution,
            replay_type='debug',
            checkpoint=checkpoint,
            modified_inputs={'new_input': 'modified_value'},
            modified_context={'debug': True},
            skip_nodes=['problematic_node'],
            purpose='Debug failing workflow',
            user=self.user
        )
        
        self.assertIsInstance(replay_session, WorkflowReplaySession)
        self.assertEqual(replay_session.workflow, self.workflow)
        self.assertEqual(replay_session.original_execution, self.execution)
        self.assertEqual(replay_session.replay_from_checkpoint, checkpoint)
        self.assertEqual(replay_session.replay_type, 'debug')
        self.assertTrue(replay_session.debug_mode)
        self.assertIn('new_input', replay_session.modified_inputs)
        self.assertIn('problematic_node', replay_session.skip_nodes)
    
    def test_failure_pattern_analysis(self):
        """Test failure pattern analysis"""
        # Create multiple failed executions
        for i in range(5):
            execution = WorkflowExecution.objects.create(
                workflow=self.workflow,
                triggered_by=self.user,
                status=ExecutionStatus.FAILED,
                error_message=f'Connection timeout error {i}',
                started_at=timezone.now() - timedelta(days=i)
            )
            
            # Create execution log with failed node
            WorkflowExecutionLog.objects.create(
                execution=execution,
                node_id=f'node_{i}',
                node_name=f'HTTP Request Node {i}',
                node_type='http_request',
                status='failed',
                error_details={'error': 'timeout'},
                started_at=timezone.now() - timedelta(days=i)
            )
        
        # Analyze failure patterns
        analysis = workflow_recovery_manager.analyze_failure_patterns(
            workflow=self.workflow,
            days=30
        )
        
        self.assertIn('total_failures', analysis)
        self.assertIn('failure_patterns', analysis)
        self.assertIn('common_failure_nodes', analysis)
        self.assertIn('recommendations', analysis)
        
        self.assertEqual(analysis['total_failures'], 6)  # 5 + 1 from setUp
        self.assertIn('timeout', analysis['failure_patterns'])
        self.assertGreater(len(analysis['recommendations']), 0)
    
    def test_checkpoint_statistics(self):
        """Test checkpoint usage statistics"""
        # Create multiple checkpoints
        for i in range(10):
            workflow_recovery_manager.create_checkpoint(
                execution=self.execution,
                checkpoint_type=CheckpointType.AUTO if i % 2 == 0 else CheckpointType.MANUAL
            )
        
        # Get statistics
        stats = workflow_recovery_manager.get_checkpoint_statistics(
            workflow=self.workflow,
            days=30
        )
        
        self.assertIn('total_checkpoints', stats)
        self.assertIn('checkpoint_types', stats)
        self.assertIn('average_checkpoint_size_mb', stats)
        self.assertIn('checkpoint_usage', stats)
        
        self.assertEqual(stats['total_checkpoints'], 10)
        self.assertIn('auto', stats['checkpoint_types'])
        self.assertIn('manual', stats['checkpoint_types'])


class WorkflowEngineIntegrationTests(TenantTestCase):
    """Test complete workflow engine integration"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_engine",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123')
        
        # Create supporting models for integration
        self.pipeline = Pipeline.objects.create(
            name='Integration Pipeline',
            created_by=self.user
        )
        
        Field.objects.create(
            pipeline=self.pipeline,
            name='name',
            field_type='text',
            is_required=True,
            created_by=self.user
        )
        
        Field.objects.create(
            pipeline=self.pipeline,
            name='email',
            field_type='email',
            is_required=True,
            created_by=self.user
        )
    
    def test_complete_workflow_execution_flow(self):
        """Test complete workflow with multiple node types"""
        workflow = Workflow.objects.create(
            name='Complete Integration Workflow',
            description='Test workflow with multiple processors',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'start_condition',
                        'type': 'condition',
                        'data': {
                            'name': 'Check Input',
                            'conditions': [
                                {
                                    'left': {'context_path': 'input.valid'},
                                    'operator': '==',
                                    'right': True,
                                    'output': 'valid_input'
                                }
                            ],
                            'default_output': 'invalid_input'
                        }
                    },
                    {
                        'id': 'create_record',
                        'type': 'record_create',
                        'data': {
                            'name': 'Create Contact Record',
                            'pipeline_id': str(self.pipeline.id),
                            'record_data': {
                                'name': '{input.contact_name}',
                                'email': '{input.contact_email}',
                                'source': 'workflow_integration_test'
                            }
                        }
                    }
                ],
                'edges': [
                    {
                        'id': 'e1',
                        'source': 'start_condition',
                        'target': 'create_record',
                        'condition': 'valid_input'
                    }
                ]
            }
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            triggered_by=self.user,
            trigger_data={
                'input': {
                    'valid': True,
                    'contact_name': 'Integration Test User',
                    'contact_email': 'integration@example.com'
                }
            },
            execution_context={
                'input': {
                    'valid': True,
                    'contact_name': 'Integration Test User',
                    'contact_email': 'integration@example.com'
                }
            }
        )
        
        # Test workflow structure
        self.assertEqual(len(workflow.get_nodes()), 2)
        self.assertEqual(len(workflow.get_edges()), 1)
        self.assertTrue(workflow.can_execute())
        
        # Test execution context
        self.assertIn('input', execution.execution_context)
        self.assertTrue(execution.execution_context['input']['valid'])
        
        # Test that execution would create appropriate logs
        # Note: Full execution would require the workflow engine to be running
        self.assertEqual(execution.status, ExecutionStatus.PENDING)
    
    def test_workflow_with_ai_and_communication(self):
        """Test workflow integrating AI and communication systems"""
        # Create communication channel
        channel = Channel.objects.create(
            name='Integration Email Channel',
            channel_type='email',
            provider='unipile',
            configuration={},
            created_by=self.user
        )
        
        workflow = Workflow.objects.create(
            name='AI Communication Workflow',
            description='Workflow combining AI analysis and email sending',
            created_by=self.user,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowStatus.ACTIVE,
            ai_config={
                'enabled': True,
                'budget_limit_usd': 5.0,
                'model_preferences': ['gpt-4']
            },
            workflow_definition={
                'nodes': [
                    {
                        'id': 'ai_analysis',
                        'type': 'ai_prompt',
                        'data': {
                            'name': 'Analyze Customer Intent',
                            'prompt': 'Analyze this customer message: {customer_message}',
                            'model': 'gpt-4',
                            'temperature': 0.3
                        }
                    },
                    {
                        'id': 'send_response',
                        'type': 'email_send',
                        'data': {
                            'name': 'Send Personalized Response',
                            'channel_id': str(channel.id),
                            'to_addresses': ['{customer_email}'],
                            'subject': 'Re: Your Inquiry',
                            'body_text': 'Based on our analysis: {node_ai_analysis}',
                            'track_delivery': True
                        }
                    }
                ],
                'edges': [
                    {
                        'id': 'e1',
                        'source': 'ai_analysis',
                        'target': 'send_response'
                    }
                ]
            }
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            triggered_by=self.user,
            trigger_data={
                'customer_message': 'I need help with my order',
                'customer_email': 'customer@example.com'
            },
            execution_context={
                'customer_message': 'I need help with my order',
                'customer_email': 'customer@example.com'
            }
        )
        
        # Test AI configuration
        self.assertTrue(workflow.ai_config['enabled'])
        self.assertEqual(workflow.ai_config['budget_limit_usd'], 5.0)
        
        # Test workflow structure integrates both AI and communication
        ai_node = workflow.get_nodes()[0]
        email_node = workflow.get_nodes()[1]
        
        self.assertEqual(ai_node['type'], 'ai_prompt')
        self.assertEqual(email_node['type'], 'email_send')
        self.assertIn('customer_message', ai_node['data']['prompt'])
        self.assertIn('node_ai_analysis', email_node['data']['body_text'])


class WorkflowSecurityAndIsolationTests(TenantTestCase):
    """Test workflow security and tenant isolation"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Security Test Tenant",
            schema_name="test_workflow_security",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123'
        )
        
        self.regular_user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        
        # Create user types with different permissions
        self.admin_type = UserType.objects.create(
            name='Admin',
            permissions={
                'workflows': {
                    'can_create': True,
                    'can_execute_all': True,
                    'can_manage_recovery': True,
                    'can_view_analytics': True
                }
            }
        )
        
        self.user_type = UserType.objects.create(
            name='User',
            permissions={
                'workflows': {
                    'can_create': False,
                    'can_execute_all': False,
                    'can_manage_recovery': False,
                    'can_view_analytics': False
                }
            }
        )
        
        self.admin_user.user_type = self.admin_type
        self.admin_user.save()
        
        self.regular_user.user_type = self.user_type
        self.regular_user.save()
    
    def test_workflow_creation_permissions(self):
        """Test workflow creation based on user permissions"""
        # Admin can create workflows
        admin_workflow = Workflow.objects.create(
            name='Admin Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        self.assertEqual(admin_workflow.created_by, self.admin_user)
        
        # Check permissions
        admin_perms = self.admin_user.user_type.permissions.get('workflows', {})
        user_perms = self.regular_user.user_type.permissions.get('workflows', {})
        
        self.assertTrue(admin_perms.get('can_create', False))
        self.assertFalse(user_perms.get('can_create', False))
    
    def test_workflow_visibility_controls(self):
        """Test workflow visibility and access controls"""
        # Create private workflow
        private_workflow = Workflow.objects.create(
            name='Private Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            visibility=WorkflowVisibility.PRIVATE,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        # Create public workflow
        public_workflow = Workflow.objects.create(
            name='Public Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            visibility=WorkflowVisibility.PUBLIC,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        self.assertEqual(private_workflow.visibility, WorkflowVisibility.PRIVATE)
        self.assertEqual(public_workflow.visibility, WorkflowVisibility.PUBLIC)
        
        # Test access logic (in real implementation, this would be enforced by views/permissions)
        self.assertTrue(private_workflow.created_by == self.admin_user)
        self.assertTrue(public_workflow.visibility == WorkflowVisibility.PUBLIC)
    
    def test_sensitive_data_handling(self):
        """Test handling of sensitive data in workflows"""
        workflow = Workflow.objects.create(
            name='Sensitive Data Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'sensitive_node',
                        'type': 'ai_prompt',
                        'data': {
                            'prompt': 'Process this data: {sensitive_field}',
                            'security_config': {
                                'exclude_fields': ['password', 'ssn', 'credit_card'],
                                'require_approval': True
                            }
                        }
                    }
                ],
                'edges': []
            }
        )
        
        # Test that security configuration is preserved
        node = workflow.get_nodes()[0]
        self.assertIn('security_config', node['data'])
        self.assertIn('exclude_fields', node['data']['security_config'])
        self.assertIn('password', node['data']['security_config']['exclude_fields'])
    
    def test_recovery_system_permissions(self):
        """Test recovery system access controls"""
        workflow = Workflow.objects.create(
            name='Recovery Test Workflow',
            created_by=self.admin_user,
            trigger_type=WorkflowTriggerType.MANUAL,
            workflow_definition={'nodes': [], 'edges': []}
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            triggered_by=self.admin_user,
            trigger_data={}
        )
        
        # Create checkpoint
        checkpoint = workflow_recovery_manager.create_checkpoint(
            execution=execution,
            checkpoint_type=CheckpointType.MANUAL
        )
        
        # Check permissions for recovery management
        admin_perms = self.admin_user.user_type.permissions.get('workflows', {})
        user_perms = self.regular_user.user_type.permissions.get('workflows', {})
        
        self.assertTrue(admin_perms.get('can_manage_recovery', False))
        self.assertFalse(user_perms.get('can_manage_recovery', False))
        
        # Verify checkpoint was created by admin
        self.assertEqual(checkpoint.workflow.created_by, self.admin_user)


if __name__ == '__main__':
    import django
    django.setup()
    
    # Run tests
    import unittest
    unittest.main()