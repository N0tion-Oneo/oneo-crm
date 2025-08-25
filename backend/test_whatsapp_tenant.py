#!/usr/bin/env python
"""
Test WhatsApp Integration with Tenant Context
Tests the new WhatsApp channel implementation within a tenant schema
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, get_tenant_model
from communications.channels.whatsapp import (
    WhatsAppClient, WhatsAppService, WhatsAppWebhookHandler
)
from communications.models import UserChannelConnection, Channel
from asgiref.sync import async_to_sync

User = get_user_model()
Tenant = get_tenant_model()


class WhatsAppTenantTest:
    """Test WhatsApp integration within tenant context"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.setup_tenant()
    
    def setup_tenant(self):
        """Setup tenant and test data"""
        # Get any available tenant (prefer oneotalent for real data, then demo, then any)
        try:
            # Try to get oneotalent tenant first (has real WhatsApp data)
            self.tenant = Tenant.objects.filter(schema_name='oneotalent').first()
            
            # If not, try demo
            if not self.tenant:
                self.tenant = Tenant.objects.filter(schema_name='demo').first()
            
            # If still not, get any tenant that's not public
            if not self.tenant:
                self.tenant = Tenant.objects.exclude(schema_name='public').first()
            
            if self.tenant:
                print(f"✅ Using tenant: {self.tenant.name} (schema: {self.tenant.schema_name})")
            else:
                print("❌ No tenant found. Creating test tenant...")
                # Create a test tenant
                from tenants.models import Domain
                self.tenant = Tenant.objects.create(
                    schema_name='test',
                    name='Test Tenant'
                )
                Domain.objects.create(
                    domain='test.localhost',
                    tenant=self.tenant,
                    is_primary=True
                )
                print(f"✅ Created tenant: {self.tenant.name} (schema: {self.tenant.schema_name})")
                
        except Exception as e:
            print(f"❌ Error setting up tenant: {e}")
            sys.exit(1)
    
    def run_in_tenant(self, func, *args, **kwargs):
        """Run a function within tenant schema context"""
        with schema_context(self.tenant.schema_name):
            return func(*args, **kwargs)
    
    def setup_test_data(self):
        """Setup test user and connection within tenant"""
        # Get or create test user in tenant schema
        self.user, created = User.objects.get_or_create(
            email='test@demo.com',
            defaults={'username': 'test_user'}
        )
        
        if created:
            print(f"  ✓ Created test user: {self.user.email}")
        else:
            print(f"  ✓ Using existing user: {self.user.email}")
        
        # Look for the real WhatsApp connection with actual UniPile account
        self.connection = UserChannelConnection.objects.filter(
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA',  # Real UniPile account ID
            channel_type='whatsapp'
        ).first()
        
        if not self.connection:
            # If not found, try to get any active WhatsApp connection
            self.connection = UserChannelConnection.objects.filter(
                channel_type='whatsapp',
                is_active=True
            ).exclude(
                unipile_account_id__in=['test_account_123', 'test-account-123']
            ).first()
        
        if self.connection:
            self.account_id = self.connection.unipile_account_id
            print(f"  ✓ Found real WhatsApp connection: {self.account_id}")
            print(f"    Name: {self.connection.account_name}")
            if self.connection.provider_config:
                phone = self.connection.provider_config.get('phone_number', 'N/A')
                print(f"    Phone: {phone}")
        else:
            print("  ⚠️ No real WhatsApp connection found. Creating mock connection...")
            # Create a mock connection for testing
            self.connection = UserChannelConnection.objects.create(
                user=self.user,
                channel_type='whatsapp',
                unipile_account_id='test_account_123',
                account_name='Test WhatsApp',
                account_status='active',
                is_active=True,
                # Store phone in provider_config
                provider_config={'phone': '+1234567890'}
            )
            self.account_id = self.connection.unipile_account_id
            print(f"  ✓ Created mock connection: {self.account_id}")
    
    def test_client(self):
        """Test WhatsApp client"""
        print("\n🔧 Testing WhatsApp Client...")
        
        try:
            client = WhatsAppClient()
            print(f"  ✓ Client initialized: {client.channel_type}")
            
            # Test account info method
            result = async_to_sync(client.get_account_info)(self.account_id)
            print(f"  ✓ Account info method works: {result.get('success', False)}")
            
        except Exception as e:
            print(f"  ❌ Client error: {e}")
    
    def test_service(self):
        """Test WhatsApp service with persistence"""
        print("\n🔧 Testing WhatsApp Service...")
        
        try:
            service = WhatsAppService()
            print(f"  ✓ Service initialized: {service.channel_type}")
            
            # Test getting or creating channel
            channel = async_to_sync(service.get_or_create_channel)(
                self.account_id, self.user
            )
            print(f"  ✓ Channel created/retrieved: {channel.id}")
            
            # Test conversation sync (will use local data)
            result = async_to_sync(service.sync_conversations)(
                user=self.user,
                account_id=self.account_id,
                force_sync=False
            )
            print(f"  ✓ Conversation sync works")
            print(f"    - Conversations: {len(result.get('conversations', []))}")
            print(f"    - From cache: {result.get('from_cache', False)}")
            print(f"    - From local: {result.get('from_local', False)}")
            
        except Exception as e:
            print(f"  ❌ Service error: {e}")
    
    def test_webhook_handler(self):
        """Test WhatsApp webhook handler"""
        print("\n🔧 Testing WhatsApp Webhook Handler...")
        
        try:
            handler = WhatsAppWebhookHandler()
            print(f"  ✓ Handler initialized: {handler.channel_type}")
            print(f"  ✓ Supported events: {len(handler.get_supported_events())}")
            
            # Create a test webhook payload
            test_webhook = {
                'event': 'message.received',
                'account_id': self.account_id,
                'message': {
                    'id': f'msg_test_{datetime.now().timestamp()}',
                    'chat_id': 'chat_test_456',
                    'text': f'Test message at {datetime.now()}',
                    'from': {
                        'id': 'sender_123',
                        'name': 'Test Sender',
                        'phone': '+1234567890',
                        'is_self': False
                    },
                    'timestamp': datetime.now().isoformat()
                },
                'chat': {
                    'id': 'chat_test_456',
                    'name': 'Test Chat',
                    'participants': [
                        {'id': 'sender_123', 'name': 'Test Sender', 'phone': '+1234567890'},
                        {'id': 'self_123', 'name': 'Me', 'phone': '+9876543210', 'is_self': True}
                    ]
                }
            }
            
            # Process webhook
            result = handler.process_webhook('message.received', test_webhook)
            
            if result.get('success'):
                print(f"  ✅ Webhook processed successfully")
                print(f"    - Message ID: {result.get('message_id')}")
                print(f"    - Conversation ID: {result.get('conversation_id')}")
            else:
                print(f"  ⚠️ Webhook processing: {result.get('error')}")
                
        except Exception as e:
            print(f"  ❌ Webhook error: {e}")
    
    def test_database_models(self):
        """Test database models are accessible"""
        print("\n🔧 Testing Database Models...")
        
        try:
            from communications.models import (
                Channel, Conversation, Message, ChatAttendee,
                UserChannelConnection
            )
            
            # Test counting records
            channels = Channel.objects.count()
            conversations = Conversation.objects.count()
            messages = Message.objects.count()
            attendees = ChatAttendee.objects.count()
            connections = UserChannelConnection.objects.count()
            
            print(f"  ✓ Database accessible in schema '{self.tenant.schema_name}':")
            print(f"    - Channels: {channels}")
            print(f"    - Conversations: {conversations}")
            print(f"    - Messages: {messages}")
            print(f"    - Attendees: {attendees}")
            print(f"    - Connections: {connections}")
            
        except Exception as e:
            print(f"  ❌ Database error: {e}")
    
    def test_attendee_detection(self):
        """Test attendee detection utility"""
        print("\n🔧 Testing Attendee Detection...")
        
        try:
            from communications.channels.whatsapp.utils import WhatsAppAttendeeDetector
            
            detector = WhatsAppAttendeeDetector()
            
            # Test webhook data extraction
            test_data = {
                'message': {
                    'from': {
                        'id': 'user_123',
                        'name': 'John Doe',
                        'phone': '+1234567890'
                    },
                    'chat_id': 'chat_456'
                }
            }
            
            attendee_info = detector.extract_attendee_from_webhook(test_data)
            print(f"  ✓ Extracted attendee: {attendee_info.get('name')}")
            print(f"    - Phone: {attendee_info.get('phone_number')}")
            print(f"    - External ID: {attendee_info.get('external_id')}")
            
            # Test creating attendee in database
            channel = Channel.objects.filter(channel_type='whatsapp').first()
            if channel:
                attendee = detector.create_or_update_attendee(
                    attendee_info, 'chat_456', channel
                )
                if attendee:
                    print(f"  ✓ Created/updated attendee in DB: {attendee.name}")
            
        except Exception as e:
            print(f"  ❌ Attendee detection error: {e}")
    
    def test_api_views(self):
        """Test API views"""
        print("\n🔧 Testing API Views...")
        
        try:
            from communications.channels.whatsapp.views import (
                get_whatsapp_accounts, get_whatsapp_chats
            )
            
            # Create a mock request
            request = self.factory.get(
                '/api/v1/communications/whatsapp/accounts/'
            )
            request.user = self.user
            
            # Test get accounts
            response = get_whatsapp_accounts(request)
            
            if response.status_code == 200:
                data = json.loads(response.content)
                print(f"  ✓ Get accounts endpoint works")
                print(f"    - Accounts: {len(data.get('accounts', []))}")
            else:
                print(f"  ⚠️ Get accounts returned: {response.status_code}")
            
        except Exception as e:
            print(f"  ❌ API views error: {e}")
    
    def run_all_tests(self):
        """Run all tests within tenant context"""
        print("=" * 60)
        print(f"🚀 WhatsApp Integration Tests (Tenant: {self.tenant.name})")
        print("=" * 60)
        
        # All tests run within tenant schema
        with schema_context(self.tenant.schema_name):
            self.setup_test_data()
            self.test_database_models()
            self.test_client()
            self.test_service()
            self.test_webhook_handler()
            self.test_attendee_detection()
            self.test_api_views()
        
        print("\n" + "=" * 60)
        print("✅ WhatsApp Tenant Tests Complete")
        print("=" * 60)


def check_current_schema():
    """Check which schema we're currently in"""
    from django.db import connection
    
    print(f"\n📍 Current database schema: {connection.schema_name}")
    
    # List all schemas
    with connection.cursor() as cursor:
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema'")
        schemas = cursor.fetchall()
        print(f"📍 Available schemas: {[s[0] for s in schemas]}")


if __name__ == '__main__':
    # Check current schema
    check_current_schema()
    
    # Run tests
    tester = WhatsAppTenantTest()
    tester.run_all_tests()
    
    print("\n✨ All tests completed!")