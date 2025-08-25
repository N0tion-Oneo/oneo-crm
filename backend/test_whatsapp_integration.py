#!/usr/bin/env python
"""
Test WhatsApp Integration
Tests the new WhatsApp channel implementation with real API calls and webhook simulation
"""
import os
import sys
import django
import json
import requests
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from communications.channels.whatsapp import (
    WhatsAppClient, WhatsAppService, WhatsAppWebhookHandler, whatsapp_views
)
from communications.models import UserChannelConnection, Channel
from asgiref.sync import async_to_sync

User = get_user_model()


class WhatsAppIntegrationTest:
    """Test WhatsApp integration components"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.setup_test_data()
    
    def setup_test_data(self):
        """Setup test user and connection"""
        # Get or create test user
        self.user, _ = User.objects.get_or_create(
            email='test@demo.com',
            defaults={'username': 'test_user'}
        )
        
        # Get test WhatsApp connection if exists
        self.connection = UserChannelConnection.objects.filter(
            user=self.user,
            channel_type='whatsapp'
        ).first()
        
        if self.connection:
            self.account_id = self.connection.unipile_account_id
            print(f"✅ Using existing WhatsApp connection: {self.account_id}")
        else:
            print("⚠️ No WhatsApp connection found. Some tests will be skipped.")
            self.account_id = None
    
    def test_client(self):
        """Test WhatsApp client"""
        print("\n🔧 Testing WhatsApp Client...")
        
        client = WhatsAppClient()
        print(f"  ✓ Client initialized: {client.channel_type}")
        
        if self.account_id:
            # Test getting conversations
            print("  🔄 Testing get_conversations...")
            try:
                result = async_to_sync(client.get_conversations)(
                    account_id=self.account_id,
                    limit=5
                )
                if result.get('success'):
                    print(f"  ✅ Retrieved {len(result.get('conversations', []))} conversations")
                else:
                    print(f"  ❌ Failed: {result.get('error')}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    def test_service(self):
        """Test WhatsApp service with persistence"""
        print("\n🔧 Testing WhatsApp Service...")
        
        service = WhatsAppService()
        print(f"  ✓ Service initialized: {service.channel_type}")
        
        if self.account_id:
            # Test sync conversations
            print("  🔄 Testing sync_conversations...")
            try:
                result = async_to_sync(service.sync_conversations)(
                    user=self.user,
                    account_id=self.account_id,
                    force_sync=False  # Use cache if available
                )
                print(f"  ✅ Synced {len(result.get('conversations', []))} conversations")
                print(f"     From cache: {result.get('from_cache', False)}")
                print(f"     From local: {result.get('from_local', False)}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    def test_webhook_handler(self):
        """Test WhatsApp webhook handler"""
        print("\n🔧 Testing WhatsApp Webhook Handler...")
        
        handler = WhatsAppWebhookHandler()
        print(f"  ✓ Handler initialized: {handler.channel_type}")
        print(f"  ✓ Supported events: {len(handler.get_supported_events())}")
        
        # Simulate a webhook event
        test_webhook_data = {
            'event': 'message.received',
            'account_id': self.account_id or 'test_account',
            'message': {
                'id': 'msg_test_123',
                'chat_id': 'chat_test_456',
                'text': 'Test message from webhook',
                'from': {
                    'id': 'sender_123',
                    'name': 'Test Sender',
                    'phone': '+1234567890'
                },
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Extract account ID
        account_id = handler.extract_account_id(test_webhook_data)
        print(f"  ✓ Extracted account ID: {account_id}")
        
        # Process webhook
        print("  🔄 Processing test webhook...")
        try:
            result = handler.process_webhook(
                event_type='message.received',
                data=test_webhook_data
            )
            if result.get('success'):
                print(f"  ✅ Webhook processed successfully")
            else:
                print(f"  ⚠️ Webhook processing: {result.get('error')}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    def test_api_endpoints(self):
        """Test WhatsApp API endpoints"""
        print("\n🔧 Testing WhatsApp API Endpoints...")
        
        if not self.account_id:
            print("  ⚠️ Skipping API tests - no WhatsApp connection")
            return
        
        # Test get_whatsapp_chats endpoint
        print("  🔄 Testing GET /whatsapp/chats/...")
        request = self.factory.get(
            '/api/v1/communications/whatsapp/chats/',
            {'account_id': self.account_id, 'limit': 5}
        )
        request.user = self.user
        
        try:
            from communications.channels.whatsapp.views import get_whatsapp_chats
            response = get_whatsapp_chats(request)
            
            if response.status_code == 200:
                data = json.loads(response.content)
                print(f"  ✅ Retrieved {len(data.get('chats', []))} chats")
                print(f"     Cache info: {data.get('cache_info')}")
            else:
                print(f"  ❌ Failed with status: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    def test_attendee_detection(self):
        """Test attendee detection utility"""
        print("\n🔧 Testing Attendee Detection...")
        
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
        print(f"  ✓ Extracted attendee: {attendee_info.get('name')} ({attendee_info.get('phone_number')})")
        
        # Test chat attendees extraction
        chat_data = {
            'participants': [
                {'id': 'p1', 'name': 'Alice', 'phone': '+111'},
                {'id': 'p2', 'name': 'Bob', 'phone': '+222'}
            ]
        }
        
        attendees = detector.extract_chat_attendees(chat_data)
        print(f"  ✓ Extracted {len(attendees)} attendees from chat")
    
    def test_message_formatter(self):
        """Test message formatter utility"""
        print("\n🔧 Testing Message Formatter...")
        
        from communications.channels.whatsapp.utils import WhatsAppMessageFormatter
        
        formatter = WhatsAppMessageFormatter()
        
        # Test outgoing formatting
        text = "Hello World"
        formatted = formatter.format_outgoing_message(text, {'bold': True})
        print(f"  ✓ Formatted outgoing: '{formatted}'")
        
        # Test incoming formatting
        raw_message = {
            'id': 'msg_123',
            'text': 'Test message',
            'timestamp': datetime.now().isoformat()
        }
        
        formatted_msg = formatter.format_incoming_message(raw_message)
        print(f"  ✓ Formatted incoming: {formatted_msg.get('content')}")
        
        # Test conversation naming
        chat_data = {'id': 'chat_123', 'name': 'Test Group'}
        name = formatter.format_conversation_name(chat_data)
        print(f"  ✓ Generated conversation name: '{name}'")
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("🚀 WhatsApp Integration Test Suite")
        print("=" * 60)
        
        self.test_client()
        self.test_service()
        self.test_webhook_handler()
        self.test_api_endpoints()
        self.test_attendee_detection()
        self.test_message_formatter()
        
        print("\n" + "=" * 60)
        print("✅ WhatsApp Integration Tests Complete")
        print("=" * 60)


def test_live_api():
    """Test with live UniPile API if configured"""
    print("\n🌐 Testing Live UniPile API...")
    
    from django.conf import settings
    
    if not hasattr(settings, 'UNIPILE_API_KEY'):
        print("  ⚠️ UNIPILE_API_KEY not configured")
        return
    
    # Get active WhatsApp connections
    connections = UserChannelConnection.objects.filter(
        channel_type='whatsapp',
        is_active=True,
        account_status='active'
    ).first()
    
    if not connections:
        print("  ⚠️ No active WhatsApp connections found")
        return
    
    print(f"  ✓ Found active connection: {connections.account_name}")
    
    # Test API call
    headers = {
        'X-Api-Key': settings.UNIPILE_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Get chats
    url = f"{settings.UNIPILE_BASE_URL}/api/v1/chats"
    params = {
        'account_id': connections.unipile_account_id,
        'limit': 5
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ API call successful: {len(data.get('items', []))} chats")
        else:
            print(f"  ❌ API call failed: {response.status_code}")
    except Exception as e:
        print(f"  ❌ API error: {e}")


def simulate_webhook():
    """Simulate a webhook call to test the handler"""
    print("\n🔔 Simulating Webhook Event...")
    
    from communications.webhooks.handlers.whatsapp import WhatsAppWebhookHandler
    
    handler = WhatsAppWebhookHandler()
    
    # Simulate incoming message webhook
    webhook_data = {
        'event': 'message.received',
        'account_id': 'test_account_123',
        'message': {
            'id': f'msg_{datetime.now().timestamp()}',
            'chat_id': 'chat_test_789',
            'text': f'Test webhook message at {datetime.now()}',
            'from': {
                'id': 'sender_456',
                'name': 'Webhook Test User',
                'phone': '+19995551234',
                'is_self': False
            },
            'timestamp': datetime.now().isoformat()
        },
        'chat': {
            'id': 'chat_test_789',
            'name': 'Test Chat',
            'participants': [
                {'id': 'sender_456', 'name': 'Webhook Test User', 'phone': '+19995551234'},
                {'id': 'self_123', 'name': 'Me', 'phone': '+19995555678', 'is_self': True}
            ]
        }
    }
    
    print(f"  📨 Webhook data: {json.dumps(webhook_data, indent=2)}")
    
    # Process webhook
    result = handler.process_webhook('message.received', webhook_data)
    
    if result.get('success'):
        print(f"  ✅ Webhook processed successfully")
        print(f"     Message ID: {result.get('message_id')}")
        print(f"     Conversation ID: {result.get('conversation_id')}")
    else:
        print(f"  ❌ Webhook failed: {result.get('error')}")


if __name__ == '__main__':
    # Run tests
    tester = WhatsAppIntegrationTest()
    tester.run_all_tests()
    
    # Test live API if available
    test_live_api()
    
    # Simulate webhook
    simulate_webhook()
    
    print("\n✨ All tests completed!")