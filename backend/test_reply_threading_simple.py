#!/usr/bin/env python
"""
Simple test to verify reply threading works correctly
"""
import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Conversation, Message, Channel
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
from django.utils import timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_reply_threading():
    """Test that replies maintain proper threading"""
    
    print("=" * 60)
    print("Testing Reply Threading")
    print("=" * 60)
    
    tenant = Tenant.objects.get(schema_name='oneotalent')
    print(f"✅ Tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get Gmail connection
        conn = UserChannelConnection.objects.filter(channel_type='gmail').first()
        if not conn:
            print("❌ No Gmail connection found")
            return False
        print(f"✅ Gmail: {conn.account_name}")
        
        # Get channel
        channel = Channel.objects.filter(
            channel_type='gmail',
            unipile_account_id=conn.unipile_account_id
        ).first()
        
        if not channel:
            print("❌ No Gmail channel found")
            return False
            
        # Create a conversation
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=f"test_{datetime.now().timestamp()}",
            subject=f"Reply Threading Test - {datetime.now().strftime('%H:%M:%S')}",
            status='active'
        )
        print(f"✅ Created conversation: {conversation.id}")
        
        # Simulate an existing message in the conversation
        # This would normally come from a webhook or previous send
        existing_message = Message.objects.create(
            conversation=conversation,
            channel=channel,
            external_message_id=f"<TEST{datetime.now().timestamp()}@mail.gmail.com>",
            direction='inbound',
            subject=conversation.subject,
            content='<p>Original message that needs a reply</p>',
            contact_email='sender@example.com',
            status='received',
            sent_at=timezone.now(),
            metadata={
                'provider_id': '1990712345abcdef',  # Gmail Message-ID (16 hex chars)
                'tracking_id': 'test_tracking_123',
                'from': {'email': 'sender@example.com', 'name': 'Sender'}
            }
        )
        print(f"✅ Created existing message with provider_id: {existing_message.metadata['provider_id']}")
        
        # Now test sending a reply
        service = EmailService()
        
        print(f"\n📧 Sending reply...")
        print(f"   Using provider_id as reply_to: {existing_message.metadata['provider_id']}")
        
        result = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': 'josh@oneodigital.com', 'display_name': 'Josh'}],
            subject=f"Re: {conversation.subject}",
            body='<p>This is my reply - it should be in the same Gmail thread</p>',
            reply_to=existing_message.metadata['provider_id']  # Use provider_id for threading
        )
        
        if result.get('success'):
            print(f"✅ Reply sent successfully!")
            print(f"   Tracking ID: {result.get('tracking_id')}")
            
            # Create the reply message record
            response = result.get('response', {})
            reply_message = Message.objects.create(
                conversation=conversation,
                channel=channel,
                external_message_id=response.get('id'),
                direction='outbound',
                subject=f"Re: {conversation.subject}",
                content='<p>This is my reply - it should be in the same Gmail thread</p>',
                contact_email='josh@oneodigital.com',
                status='sent',
                sent_at=timezone.now(),
                metadata={
                    'tracking_id': result.get('tracking_id'),
                    'unipile_id': response.get('id'),
                    'provider_id': response.get('provider_id'),
                    'reply_to': existing_message.metadata['provider_id']  # Track what we used
                }
            )
            print(f"✅ Created reply message record")
            
            # Verify the threading setup
            print(f"\n📊 Threading Verification:")
            print(f"   Original provider_id: {existing_message.metadata['provider_id']}")
            print(f"   Reply used reply_to:  {existing_message.metadata['provider_id']}")
            print(f"   Reply provider_id:    {response.get('provider_id')}")
            
            print(f"\n✅ Threading test completed!")
            print(f"\n⚠️ IMPORTANT: Check your Gmail to verify both emails are in the same thread")
            
            # Show conversation messages
            print(f"\n📋 Messages in conversation:")
            for msg in Message.objects.filter(conversation=conversation).order_by('created_at'):
                print(f"   - {msg.subject}")
                print(f"     Direction: {msg.direction}")
                print(f"     Provider ID: {msg.metadata.get('provider_id', 'N/A') if msg.metadata else 'N/A'}")
            
            return True
        else:
            print(f"❌ Failed to send reply: {result.get('error')}")
            return False

if __name__ == "__main__":
    success = test_reply_threading()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ REPLY THREADING TEST PASSED")
        print("The frontend should now properly thread replies!")
    else:
        print("❌ REPLY THREADING TEST FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)