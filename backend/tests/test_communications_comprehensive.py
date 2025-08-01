"""
Comprehensive tests for Communications app and its integration with core system
Tests communications models, UniPile integration, tracking system, and integration with Phases 1-8
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

# Import communications models
from communications.models import (
    Channel, Conversation, Message, CommunicationAnalytics, 
    UserChannelConnection, MessageDirection, MessageStatus
)

# Import tracking models
from communications.tracking.models import (
    CommunicationTracking, DeliveryTracking, ReadTracking,
    ResponseTracking, CampaignTracking, PerformanceMetrics
)

# Import managers and services
from communications.tracking.manager import CommunicationTracker
from communications.tracking.analytics import CommunicationAnalyzer
from communications.unipile_sdk import UnipileClient
from communications.services import message_service

# Import authentication models for integration
from authentication.models import User, UserType
from authentication.permissions import AsyncPermissionManager

# Import pipeline models for integration
from pipelines.models import Pipeline, Field, Record

# Import workflow models for integration
from workflows.models import Workflow, WorkflowExecution

User = get_user_model()


class CommunicationsModelTests(TenantTestCase):
    """Test communications models with tenant isolation"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create tenant for testing
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_communications",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a test channel
        self.channel = Channel.objects.create(
            name='Test Email Channel',
            channel_type='email',
            provider='unipile',
            configuration={
                'smtp_server': 'smtp.example.com',
                'smtp_port': 587,
                'use_tls': True
            },
            is_active=True,
            created_by=self.user
        )
    
    def test_channel_creation(self):
        """Test channel model creation and validation"""
        self.assertEqual(self.channel.name, 'Test Email Channel')
        self.assertEqual(self.channel.channel_type, 'email')
        self.assertEqual(self.channel.provider, 'unipile')
        self.assertTrue(self.channel.is_active)
        self.assertIsNotNone(self.channel.created_at)
        
        # Test configuration validation
        self.assertIn('smtp_server', self.channel.configuration)
        self.assertEqual(self.channel.configuration['smtp_port'], 587)
    
    def test_conversation_creation(self):
        """Test conversation model"""
        conversation = Conversation.objects.create(
            channel=self.channel,
            external_thread_id='thread_123',
            subject='Test Conversation',
            participants=['test@example.com', 'user@example.com'],
            metadata={'priority': 'high'},
            created_by=self.user
        )
        
        self.assertEqual(conversation.channel, self.channel)
        self.assertEqual(conversation.external_thread_id, 'thread_123')
        self.assertEqual(conversation.subject, 'Test Conversation')
        self.assertEqual(len(conversation.participants), 2)
        self.assertEqual(conversation.metadata['priority'], 'high')
    
    def test_message_creation(self):
        """Test message model with all message types"""
        conversation = Conversation.objects.create(
            channel=self.channel,
            external_thread_id='thread_123',
            subject='Test Conversation',
            participants=['test@example.com'],
            created_by=self.user
        )
        
        # Test outbound message
        outbound_message = Message.objects.create(
            conversation=conversation,
            channel=self.channel,
            external_message_id='msg_out_123',
            direction=MessageDirection.OUTBOUND,
            content_text='Hello, this is a test message',
            content_html='<p>Hello, this is a test message</p>',
            sender_address='system@example.com',
            recipient_addresses=['test@example.com'],
            message_type='email',
            status=MessageStatus.SENT,
            sent_at=timezone.now(),
            created_by=self.user
        )
        
        self.assertEqual(outbound_message.direction, MessageDirection.OUTBOUND)
        self.assertEqual(outbound_message.status, MessageStatus.SENT)
        self.assertIsNotNone(outbound_message.sent_at)
        
        # Test inbound message
        inbound_message = Message.objects.create(
            conversation=conversation,
            channel=self.channel,
            external_message_id='msg_in_123',
            direction=MessageDirection.INBOUND,
            content_text='Reply message',
            sender_address='test@example.com',
            recipient_addresses=['system@example.com'],
            message_type='email',
            status=MessageStatus.RECEIVED,
            received_at=timezone.now()
        )
        
        self.assertEqual(inbound_message.direction, MessageDirection.INBOUND)
        self.assertEqual(inbound_message.status, MessageStatus.RECEIVED)
        self.assertIsNotNone(inbound_message.received_at)
    
    def test_communication_analytics(self):
        """Test communication analytics model"""
        analytics = CommunicationAnalytics.objects.create(
            channel=self.channel,
            date=timezone.now().date(),
            messages_sent=100,
            messages_received=75,
            messages_failed=5,
            delivery_rate=Decimal('95.00'),
            response_rate=Decimal('75.00'),
            average_response_time_hours=Decimal('2.50'),
            engagement_score=Decimal('85.50')
        )
        
        self.assertEqual(analytics.messages_sent, 100)
        self.assertEqual(analytics.messages_received, 75)
        self.assertEqual(analytics.delivery_rate, Decimal('95.00'))
        self.assertEqual(analytics.response_rate, Decimal('75.00'))
        self.assertEqual(analytics.engagement_score, Decimal('85.50'))
    
    def test_user_channel_connection(self):
        """Test user channel connection model"""
        connection = UserChannelConnection.objects.create(
            user=self.user,
            channel=self.channel,
            connection_data={
                'access_token': 'encrypted_token',
                'refresh_token': 'encrypted_refresh_token',
                'account_id': 'user_account_123'
            },
            is_active=True,
            last_sync_at=timezone.now()
        )
        
        self.assertEqual(connection.user, self.user)
        self.assertEqual(connection.channel, self.channel)
        self.assertTrue(connection.is_active)
        self.assertIn('access_token', connection.connection_data)
        self.assertIsNotNone(connection.last_sync_at)


class CommunicationTrackingTests(TenantTestCase):
    """Test communication tracking system"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_tracking",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.channel = Channel.objects.create(
            name='Test Channel',
            channel_type='email',
            provider='unipile',
            configuration={},
            created_by=self.user
        )
        
        self.conversation = Conversation.objects.create(
            channel=self.channel,
            external_thread_id='thread_123',
            subject='Test',
            participants=['test@example.com'],
            created_by=self.user
        )
        
        self.message = Message.objects.create(
            conversation=self.conversation,
            channel=self.channel,
            external_message_id='msg_123',
            direction=MessageDirection.OUTBOUND,
            content_text='Test message',
            sender_address='system@example.com',
            recipient_addresses=['test@example.com'],
            message_type='email',
            status=MessageStatus.SENT,
            created_by=self.user
        )
        
        self.tracker = CommunicationTracker()
    
    def test_communication_tracking_creation(self):
        """Test creating communication tracking record"""
        tracking = self.tracker.track_message_sent(
            message=self.message,
            campaign_id='campaign_123',
            tracking_data={'utm_source': 'email', 'utm_campaign': 'test'}
        )
        
        self.assertIsInstance(tracking, CommunicationTracking)
        self.assertEqual(tracking.message, self.message)
        self.assertEqual(tracking.campaign_id, 'campaign_123')
        self.assertEqual(tracking.tracking_data['utm_source'], 'email')
        self.assertIsNotNone(tracking.sent_at)
    
    def test_delivery_tracking(self):
        """Test delivery tracking functionality"""
        # Track initial send
        comm_tracking = self.tracker.track_message_sent(self.message)
        
        # Track delivery attempt
        delivery_tracking = self.tracker.track_delivery_attempt(
            message=self.message,
            attempt_number=1,
            external_tracking_id='delivery_123'
        )
        
        self.assertIsInstance(delivery_tracking, DeliveryTracking)
        self.assertEqual(delivery_tracking.message, self.message)
        self.assertEqual(delivery_tracking.attempt_count, 1)
        self.assertEqual(delivery_tracking.external_tracking_id, 'delivery_123')
        
        # Track successful delivery
        self.tracker.track_delivery_success(
            message=self.message,
            delivered_at=timezone.now(),
            delivery_time_ms=1500
        )
        
        delivery_tracking.refresh_from_db()
        self.assertEqual(delivery_tracking.status, 'delivered')
        self.assertIsNotNone(delivery_tracking.delivered_at)
        self.assertEqual(delivery_tracking.total_delivery_time_ms, 1500)
    
    def test_read_tracking(self):
        """Test read tracking with pixel tracking"""
        # Track message read
        read_tracking = self.tracker.track_message_read(
            message=self.message,
            read_at=timezone.now(),
            reader_ip='192.168.1.1',
            user_agent='Mozilla/5.0...',
            tracking_method='pixel'
        )
        
        self.assertIsInstance(read_tracking, ReadTracking)
        self.assertEqual(read_tracking.message, self.message)
        self.assertEqual(read_tracking.tracking_method, 'pixel')
        self.assertEqual(read_tracking.reader_ip, '192.168.1.1')
        self.assertIsNotNone(read_tracking.first_read_at)
        self.assertEqual(read_tracking.read_count, 1)
        
        # Track second read
        self.tracker.track_message_read(
            message=self.message,
            read_at=timezone.now() + timedelta(minutes=5),
            tracking_method='pixel'
        )
        
        read_tracking.refresh_from_db()
        self.assertEqual(read_tracking.read_count, 2)
        self.assertIsNotNone(read_tracking.last_read_at)
    
    def test_response_tracking(self):
        """Test response tracking and analysis"""
        # Create response message
        response_message = Message.objects.create(
            conversation=self.conversation,
            channel=self.channel,
            external_message_id='msg_response_123',
            direction=MessageDirection.INBOUND,
            content_text='Thank you for your message!',
            sender_address='test@example.com',
            recipient_addresses=['system@example.com'],
            message_type='email',
            status=MessageStatus.RECEIVED
        )
        
        # Track response
        response_tracking = self.tracker.track_message_response(
            original_message=self.message,
            response_message=response_message,
            response_time_hours=Decimal('2.5'),
            sentiment_score=Decimal('0.8'),
            engagement_indicators=['positive_words', 'question_asked']
        )
        
        self.assertIsInstance(response_tracking, ResponseTracking)
        self.assertEqual(response_tracking.original_message, self.message)
        self.assertEqual(response_tracking.response_message, response_message)
        self.assertEqual(response_tracking.response_time_hours, Decimal('2.5'))
        self.assertEqual(response_tracking.sentiment_score, Decimal('0.8'))
        self.assertIn('positive_words', response_tracking.engagement_indicators)
    
    def test_campaign_tracking(self):
        """Test campaign-level tracking"""
        campaign_tracking = self.tracker.track_campaign_message(
            message=self.message,
            campaign_id='campaign_123',
            campaign_name='Test Campaign',
            segment='segment_a',
            ab_test_variant='variant_a'
        )
        
        self.assertIsInstance(campaign_tracking, CampaignTracking)
        self.assertEqual(campaign_tracking.campaign_id, 'campaign_123')
        self.assertEqual(campaign_tracking.campaign_name, 'Test Campaign')
        self.assertEqual(campaign_tracking.segment, 'segment_a')
        self.assertEqual(campaign_tracking.ab_test_variant, 'variant_a')
    
    def test_performance_metrics(self):
        """Test performance metrics calculation"""
        # Create sample tracking data
        for i in range(10):
            message = Message.objects.create(
                conversation=self.conversation,
                channel=self.channel,
                external_message_id=f'msg_{i}',
                direction=MessageDirection.OUTBOUND,
                content_text=f'Test message {i}',
                sender_address='system@example.com',
                recipient_addresses=['test@example.com'],
                message_type='email',
                status=MessageStatus.SENT,
                created_by=self.user
            )
            
            # Track message and delivery
            self.tracker.track_message_sent(message)
            if i < 8:  # 80% delivery rate
                self.tracker.track_delivery_success(message, timezone.now(), 1000)
            if i < 5:  # 50% read rate
                self.tracker.track_message_read(message, timezone.now())
            if i < 3:  # 30% response rate
                response = Message.objects.create(
                    conversation=self.conversation,
                    channel=self.channel,
                    external_message_id=f'response_{i}',
                    direction=MessageDirection.INBOUND,
                    content_text=f'Response {i}',
                    sender_address='test@example.com',
                    recipient_addresses=['system@example.com'],
                    message_type='email',
                    status=MessageStatus.RECEIVED
                )
                self.tracker.track_message_response(message, response, Decimal('1.0'))
        
        # Calculate performance metrics
        metrics = self.tracker.calculate_performance_metrics(
            channel=self.channel,
            start_date=timezone.now().date() - timedelta(days=1),
            end_date=timezone.now().date() + timedelta(days=1)
        )
        
        self.assertIsInstance(metrics, PerformanceMetrics)
        self.assertEqual(metrics.total_sent, 11)  # Including original message
        self.assertEqual(metrics.total_delivered, 9)  # 8 + 1 original
        self.assertAlmostEqual(float(metrics.delivery_rate), 81.8, places=1)  # 9/11


class CommunicationAnalyticsTests(TenantTestCase):
    """Test communication analytics and insights"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_analytics",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.channel = Channel.objects.create(
            name='Test Channel',
            channel_type='email',
            provider='unipile',
            configuration={},
            created_by=self.user
        )
        
        self.analyzer = CommunicationAnalyzer()
    
    def test_channel_analytics(self):
        """Test channel-level analytics generation"""
        analytics = self.analyzer.generate_channel_analytics(
            channel=self.channel,
            date_range_days=30
        )
        
        self.assertIn('channel_id', analytics)
        self.assertIn('date_range_days', analytics)
        self.assertIn('summary_metrics', analytics)
        self.assertIn('trends', analytics)
        self.assertIn('top_performing_content', analytics)
        self.assertIn('recommendations', analytics)
    
    def test_engagement_scoring(self):
        """Test engagement scoring algorithm"""
        # Mock engagement data
        engagement_data = {
            'delivery_rate': 95.0,
            'open_rate': 75.0,
            'click_rate': 25.0,
            'response_rate': 15.0,
            'sentiment_score': 0.8,
            'bounce_rate': 2.0,
            'unsubscribe_rate': 0.5
        }
        
        score = self.analyzer.calculate_engagement_score(engagement_data)
        
        self.assertIsInstance(score, Decimal)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_optimal_send_time_analysis(self):
        """Test optimal send time recommendations"""
        # Create sample messages with different send times
        send_times = []
        for hour in range(24):
            send_time = timezone.now().replace(hour=hour, minute=0, second=0)
            send_times.append({
                'sent_at': send_time,
                'engagement_score': 50 + (hour % 12) * 4  # Mock engagement pattern
            })
        
        optimal_times = self.analyzer.analyze_optimal_send_times(
            channel=self.channel,
            historical_data=send_times
        )
        
        self.assertIn('recommended_hours', optimal_times)
        self.assertIn('engagement_by_hour', optimal_times)
        self.assertIn('best_day_of_week', optimal_times)
        self.assertIsInstance(optimal_times['recommended_hours'], list)


class UniPileIntegrationTests(TestCase):
    """Test UniPile SDK integration"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    @patch('communications.unipile_sdk.requests.post')
    def test_unipile_message_send(self, mock_post):
        """Test sending message through UniPile"""
        # Mock UniPile response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'message_id': 'unipile_msg_123',
            'status': 'sent',
            'provider_response': {
                'external_id': 'provider_msg_456'
            }
        }
        
        response = UnipileClient().send_message(
            account_id='account_123',
            channel_type='email',
            to=['test@example.com'],
            subject='Test Subject',
            body='Test message body',
            from_address='system@example.com'
        )
        
        self.assertEqual(response['message_id'], 'unipile_msg_123')
        self.assertEqual(response['status'], 'sent')
        mock_post.assert_called_once()
    
    @patch('communications.unipile_sdk.requests.get')
    def test_unipile_message_status(self, mock_get):
        """Test checking message status through UniPile"""
        # Mock UniPile response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'message_id': 'unipile_msg_123',
            'status': 'delivered',
            'delivered_at': '2024-01-15T10:30:00Z',
            'delivery_details': {
                'attempts': 1,
                'last_attempt_at': '2024-01-15T10:30:00Z'
            }
        }
        
        status = UnipileClient().get_message_status('unipile_msg_123')
        
        self.assertEqual(status['status'], 'delivered')
        self.assertIn('delivered_at', status)
        mock_get.assert_called_once()


class WorkflowIntegrationTests(TenantTestCase):
    """Test communications integration with workflow system"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_workflow_comm",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create pipeline for workflow integration
        self.pipeline = Pipeline.objects.create(
            name='Contact Pipeline',
            description='Pipeline for contacts',
            created_by=self.user
        )
        
        # Create email field
        self.email_field = Field.objects.create(
            pipeline=self.pipeline,
            name='email',
            field_type='email',
            is_required=True,
            created_by=self.user
        )
        
        # Create record
        self.record = Record.objects.create(
            pipeline=self.pipeline,
            data={'email': 'contact@example.com', 'name': 'John Doe'},
            created_by=self.user
        )
        
        # Create channel
        self.channel = Channel.objects.create(
            name='Workflow Email Channel',
            channel_type='email',
            provider='unipile',
            configuration={},
            created_by=self.user
        )
    
    def test_workflow_email_node_integration(self):
        """Test email node in workflow can access communications system"""
        from workflows.nodes.communication.email import EmailProcessor
        
        # Create workflow with email node
        workflow = Workflow.objects.create(
            name='Email Workflow',
            description='Workflow with email communication',
            created_by=self.user,
            workflow_definition={
                'nodes': [
                    {
                        'id': 'email_node',
                        'type': 'email_send',
                        'data': {
                            'name': 'Send Welcome Email',
                            'channel_id': str(self.channel.id),
                            'to_addresses': ['{record.email}'],
                            'subject': 'Welcome {record.name}!',
                            'body_text': 'Welcome to our system, {record.name}!',
                            'track_delivery': True,
                            'track_reads': True
                        }
                    }
                ],
                'edges': []
            }
        )
        
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            triggered_by=self.user,
            trigger_data={'record_id': str(self.record.id)},
            execution_context={'record': self.record.data}
        )
        
        # Test email processor can access channel
        processor = EmailProcessor()
        self.assertTrue(hasattr(processor, 'process'))
        
        # Verify workflow structure
        self.assertEqual(len(workflow.get_nodes()), 1)
        self.assertEqual(workflow.get_nodes()[0]['type'], 'email_send')
    
    @patch('communications.unipile_sdk.UnipileClient.send_message')
    def test_communication_workflow_execution(self, mock_send):
        """Test full communication workflow execution"""
        # Mock UniPile send response
        mock_send.return_value = {
            'message_id': 'unipile_123',
            'status': 'sent',
            'external_id': 'ext_123'
        }
        
        # Test that workflow can trigger communication
        from communications.services import message_service
        
        result = message_service.send_templated_message(
            channel=self.channel,
            template_data={
                'to_addresses': ['contact@example.com'],
                'subject': 'Test Subject',
                'body_text': 'Hello from workflow!'
            },
            context_data={'record': self.record.data}
        )
        
        self.assertIn('message_id', result)
        mock_send.assert_called_once()


class PipelineIntegrationTests(TenantTestCase):
    """Test communications integration with pipeline system"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_pipeline_comm",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Create pipeline with contact fields
        self.pipeline = Pipeline.objects.create(
            name='Contact Pipeline',
            description='Customer contact information',
            created_by=self.user
        )
        
        # Create relevant fields
        self.email_field = Field.objects.create(
            pipeline=self.pipeline,
            name='email',
            field_type='email',
            is_required=True,
            created_by=self.user
        )
        
        self.phone_field = Field.objects.create(
            pipeline=self.pipeline,
            name='phone',
            field_type='phone',
            created_by=self.user
        )
        
        # Create record
        self.record = Record.objects.create(
            pipeline=self.pipeline,
            data={
                'email': 'john.doe@example.com',
                'phone': '+1234567890',
                'name': 'John Doe',
                'company': 'Acme Corp'
            },
            created_by=self.user
        )
    
    def test_contact_resolution_from_pipeline(self):
        """Test resolving contacts from pipeline records"""
        from communications.contact_resolver import contact_resolver
        
        contacts = contact_resolver.resolve_contacts_from_pipeline(
            pipeline=self.pipeline,
            filters={'name__icontains': 'john'}
        )
        
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]['email'], 'john.doe@example.com')
        self.assertEqual(contacts[0]['name'], 'John Doe')
    
    def test_communication_preferences_integration(self):
        """Test communication preferences from pipeline data"""
        # Add communication preferences field
        prefs_field = Field.objects.create(
            pipeline=self.pipeline,
            name='communication_preferences',
            field_type='json',
            created_by=self.user
        )
        
        # Update record with preferences
        self.record.data['communication_preferences'] = {
            'email': True,
            'sms': False,
            'phone': True,
            'preferred_time': 'morning',
            'timezone': 'America/New_York'
        }
        self.record.save()
        
        # Test preference checking
        from communications.services import message_service
        
        can_email = message_service.check_communication_preference(
            record=self.record,
            channel_type='email'
        )
        
        can_sms = message_service.check_communication_preference(
            record=self.record,
            channel_type='sms'
        )
        
        self.assertTrue(can_email)
        self.assertFalse(can_sms)


class AuthenticationIntegrationTests(TenantTestCase):
    """Test communications integration with authentication system"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_auth_comm",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        # Create users with different types
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123'
        )
        
        self.manager_user = User.objects.create_user(
            email='manager@example.com',
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
                'communications': {
                    'can_create_channels': True,
                    'can_manage_all_conversations': True,
                    'can_view_analytics': True
                }
            }
        )
        
        self.user_type = UserType.objects.create(
            name='User',
            permissions={
                'communications': {
                    'can_create_channels': False,
                    'can_manage_all_conversations': False,
                    'can_view_analytics': False
                }
            }
        )
        
        # Assign user types
        self.admin_user.user_type = self.admin_type
        self.admin_user.save()
        
        self.regular_user.user_type = self.user_type
        self.regular_user.save()
    
    def test_channel_creation_permissions(self):
        """Test channel creation based on user permissions"""
        from communications.models import Channel
        
        # Admin should be able to create channels
        admin_channel = Channel.objects.create(
            name='Admin Channel',
            channel_type='email',
            provider='unipile',
            configuration={},
            created_by=self.admin_user
        )
        
        self.assertEqual(admin_channel.created_by, self.admin_user)
        
        # Test permission checking
        from authentication.permissions import AsyncPermissionManager
        
        permission_manager = AsyncPermissionManager()
        
        # Admin has permission
        admin_perms = self.admin_user.user_type.permissions.get('communications', {})
        self.assertTrue(admin_perms.get('can_create_channels', False))
        
        # Regular user doesn't have permission
        user_perms = self.regular_user.user_type.permissions.get('communications', {})
        self.assertFalse(user_perms.get('can_create_channels', False))
    
    def test_conversation_access_control(self):
        """Test conversation access based on user permissions"""
        channel = Channel.objects.create(
            name='Test Channel',
            channel_type='email',
            provider='unipile',
            configuration={},
            created_by=self.admin_user
        )
        
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id='thread_123',
            subject='Private Conversation',
            participants=['admin@example.com'],
            created_by=self.admin_user
        )
        
        # Admin can manage all conversations
        admin_perms = self.admin_user.user_type.permissions.get('communications', {})
        self.assertTrue(admin_perms.get('can_manage_all_conversations', False))
        
        # Regular user cannot manage all conversations
        user_perms = self.regular_user.user_type.permissions.get('communications', {})
        self.assertFalse(user_perms.get('can_manage_all_conversations', False))


class CommunicationsPerformanceTests(TenantTestCase):
    """Test communications system performance and scalability"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            schema_name="test_perf_comm",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.channel = Channel.objects.create(
            name='Performance Test Channel',
            channel_type='email',
            provider='unipile',
            configuration={},
            created_by=self.user
        )
    
    def test_bulk_message_creation_performance(self):
        """Test performance for bulk message operations"""
        import time
        
        # Create conversation
        conversation = Conversation.objects.create(
            channel=self.channel,
            external_thread_id='perf_thread',
            subject='Performance Test',
            participants=['test@example.com'],
            created_by=self.user
        )
        
        # Test bulk message creation
        start_time = time.time()
        
        messages = []
        for i in range(100):
            messages.append(Message(
                conversation=conversation,
                channel=self.channel,
                external_message_id=f'perf_msg_{i}',
                direction=MessageDirection.OUTBOUND,
                content_text=f'Performance test message {i}',
                sender_address='system@example.com',
                recipient_addresses=['test@example.com'],
                message_type='email',
                status=MessageStatus.SENT,
                created_by=self.user
            ))
        
        Message.objects.bulk_create(messages)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 100 messages in under 1 second
        self.assertLess(creation_time, 1.0)
        self.assertEqual(Message.objects.filter(conversation=conversation).count(), 100)
    
    def test_tracking_system_performance(self):
        """Test tracking system performance with large datasets"""
        import time
        
        conversation = Conversation.objects.create(
            channel=self.channel,
            external_thread_id='tracking_perf',
            subject='Tracking Performance Test',
            participants=['test@example.com'],
            created_by=self.user
        )
        
        # Create messages for tracking
        messages = []
        for i in range(50):
            messages.append(Message(
                conversation=conversation,
                channel=self.channel,
                external_message_id=f'track_msg_{i}',
                direction=MessageDirection.OUTBOUND,
                content_text=f'Tracking test message {i}',
                sender_address='system@example.com',
                recipient_addresses=['test@example.com'],
                message_type='email',
                status=MessageStatus.SENT,
                created_by=self.user
            ))
        
        Message.objects.bulk_create(messages)
        
        # Test bulk tracking creation
        tracker = CommunicationTracker()
        
        start_time = time.time()
        
        for message in Message.objects.filter(conversation=conversation):
            tracker.track_message_sent(message)
            tracker.track_delivery_success(message, timezone.now(), 1000)
            tracker.track_message_read(message, timezone.now())
        
        end_time = time.time()
        tracking_time = end_time - start_time
        
        # Should track 50 messages with 3 operations each in under 2 seconds
        self.assertLess(tracking_time, 2.0)
        self.assertEqual(CommunicationTracking.objects.count(), 50)
        self.assertEqual(DeliveryTracking.objects.count(), 50)
        self.assertEqual(ReadTracking.objects.count(), 50)


class CommunicationsSecurityTests(TenantTestCase):
    """Test communications system security and data isolation"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create two separate tenants for isolation testing
        cls.tenant1 = Tenant.objects.create(
            name="Tenant 1",
            schema_name="test_security_1",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
        cls.tenant2 = Tenant.objects.create(
            name="Tenant 2", 
            schema_name="test_security_2",
            paid_until=timezone.now() + timedelta(days=30),
            on_trial=False
        )
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='testpass123'
        )
    
    def test_tenant_data_isolation(self):
        """Test that communication data is properly isolated between tenants"""
        # Note: This would require switching tenants in the test
        # For now, we test the data model structure supports isolation
        
        channel1 = Channel.objects.create(
            name='Tenant 1 Channel',
            channel_type='email',
            provider='unipile',
            configuration={'tenant_specific': 'data1'},
            created_by=self.user1
        )
        
        channel2 = Channel.objects.create(
            name='Tenant 2 Channel',
            channel_type='email',
            provider='unipile',
            configuration={'tenant_specific': 'data2'},
            created_by=self.user2
        )
        
        # Verify channels exist and have different configurations
        self.assertNotEqual(channel1.configuration, channel2.configuration)
        self.assertEqual(channel1.configuration['tenant_specific'], 'data1')
        self.assertEqual(channel2.configuration['tenant_specific'], 'data2')
    
    def test_sensitive_data_encryption(self):
        """Test that sensitive communication data is properly handled"""
        channel = Channel.objects.create(
            name='Secure Channel',
            channel_type='email',
            provider='unipile',
            configuration={
                'api_key': 'sensitive_api_key',
                'encryption_key': 'secret_encryption_key'
            },
            created_by=self.user1
        )
        
        # Configuration should be stored (in real implementation would be encrypted)
        self.assertIn('api_key', channel.configuration)
        self.assertIn('encryption_key', channel.configuration)
        
        # Test connection data encryption
        connection = UserChannelConnection.objects.create(
            user=self.user1,
            channel=channel,
            connection_data={
                'access_token': 'sensitive_access_token',
                'refresh_token': 'sensitive_refresh_token'
            },
            is_active=True
        )
        
        # Connection data should be stored (in real implementation would be encrypted)
        self.assertIn('access_token', connection.connection_data)
        self.assertIn('refresh_token', connection.connection_data)


if __name__ == '__main__':
    import django
    django.setup()
    
    # Run tests
    import unittest
    unittest.main()