#!/usr/bin/env python3
"""
Monitor complete message flow from webhook to frontend WebSocket
"""
import os
import sys
import django
import asyncio
import json
import time
from django.conf import settings

# Add the project directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import tenant_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Message, MessageDirection
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

# Set up logging to see real-time events
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_websocket_monitoring():
    """Setup monitoring for WebSocket message flow"""
    print("🔌 Setting up WebSocket Message Flow Monitoring")
    print("=" * 60)
    
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with tenant_context(tenant):
        connection = UserChannelConnection.objects.filter(channel_type='whatsapp').first()
        
        if not connection:
            print("❌ No WhatsApp connection found")
            return
        
        print(f"🔗 Monitoring connection: {connection.account_name}")
        print(f"   Business Phone: +{connection.connection_config.get('phone_number')}")
        print()
        
        # Get the most recent conversation ID
        recent_conversation = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).order_by('-created_at').first()
        
        if recent_conversation:
            conv_id = recent_conversation.conversation.id
            print(f"📱 Monitoring conversation: {recent_conversation.conversation.subject}")
            print(f"   Conversation ID: {conv_id}")
            print(f"   WebSocket room: conversation_{conv_id}")
            print()
        
        print("🎯 What to expect when you send a WhatsApp message:")
        print("   1. UniPile receives your message")
        print("   2. UniPile sends webhook to our system") 
        print("   3. Webhook handler processes message (~200ms)")
        print("   4. Message saved to database")
        print("   5. WebSocket broadcast to conversation_{conv_id}")
        print("   6. Frontend receives 'new_message' event")
        print("   7. Frontend updates message list")
        print()
        
        print("🔍 To test:")
        print("   1. Connect frontend WebSocket to conversation room")
        print("   2. Send a message from your WhatsApp")
        print("   3. Watch backend logs for webhook processing")
        print("   4. Watch frontend for real-time message arrival")
        print()
        
        # Test WebSocket channel layer
        channel_layer = get_channel_layer()
        if channel_layer:
            print("✅ WebSocket channel layer is available")
            
            # Test broadcasting a sample message
            test_message = {
                'type': 'new_message',
                'message': {
                    'id': 'test_message_123',
                    'content': 'Test WebSocket message',
                    'direction': 'out',
                    'created_at': time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    'status': 'delivered'
                }
            }
            
            print(f"🧪 Testing WebSocket broadcast to room: conversation_{conv_id}")
            
            try:
                async_to_sync(channel_layer.group_send)(
                    f"conversation_{conv_id}",
                    test_message
                )
                print("✅ Test WebSocket broadcast sent successfully")
            except Exception as e:
                print(f"❌ WebSocket broadcast failed: {e}")
        else:
            print("❌ WebSocket channel layer not available")
        
        print()
        print("📋 READY FOR LIVE TEST:")
        print("   1. Frontend should connect to WebSocket")
        print("   2. Subscribe to conversation room")
        print("   3. Send WhatsApp message from your phone")
        print("   4. Message should appear instantly via WebSocket")
        
        return conv_id

def monitor_recent_messages():
    """Monitor recent messages for debugging"""
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with tenant_context(tenant):
        print("\n📊 Recent Message Analysis:")
        print("-" * 40)
        
        # Get messages from last 10 minutes
        from django.utils import timezone
        recent_cutoff = timezone.now() - timezone.timedelta(minutes=10)
        
        recent_messages = Message.objects.filter(
            channel__channel_type='whatsapp',
            created_at__gte=recent_cutoff
        ).order_by('-created_at')[:10]
        
        print(f"Found {recent_messages.count()} messages in last 10 minutes:")
        
        for msg in recent_messages:
            direction_icon = '📤' if msg.direction == MessageDirection.OUTBOUND else '📥'
            processing_method = "webhook" if msg.metadata.get('webhook_received') else "direct_api"
            
            print(f"  {direction_icon} {msg.created_at.strftime('%H:%M:%S')} - {msg.content[:30]}...")
            print(f"      Method: {processing_method}")
            print(f"      Conversation: {msg.conversation.id}")
            print(f"      Status: {msg.status}")
            print()

if __name__ == "__main__":
    conv_id = setup_websocket_monitoring()
    monitor_recent_messages()
    
    print("\n🚀 WEBSOCKET MONITORING READY!")
    print("Send a WhatsApp message now and watch for real-time delivery...")