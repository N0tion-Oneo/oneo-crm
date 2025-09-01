#!/usr/bin/env python
"""
Test correct email threading using reply_to parameter
"""
import os
import sys
import django
import json
from datetime import datetime
import time

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

def test_correct_threading():
    """Test email threading using reply_to parameter correctly"""
    
    print("=" * 60)
    print("Testing Correct Email Threading with reply_to")
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
        
        # Get or create channel
        channel = Channel.objects.filter(
            channel_type='gmail',
            unipile_account_id=conn.unipile_account_id
        ).first()
        
        if not channel:
            print("❌ No Gmail channel found")
            return False
            
        # Create a conversation for testing
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=f"test_{datetime.now().timestamp()}",
            subject=f"Threading Test v2 - {datetime.now().strftime('%H:%M:%S')}",
            status='active'
        )
        print(f"✅ Created conversation: {conversation.id}")
        
        # Send first email
        service = EmailService()
        subject = f"Threading Test v2 - {datetime.now().strftime('%H:%M:%S')}"
        
        print(f"\n📧 Step 1: Sending initial email...")
        result1 = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': 'josh@oneodigital.com', 'display_name': 'Josh Cowan'}],
            subject=subject,
            body='<p>First email - this starts a new thread</p>'
        )
        
        if not result1.get('success'):
            print(f"❌ Failed to send first email: {result1.get('error')}")
            return False
            
        # Extract IDs from first email
        unipile_id1 = result1.get('response', {}).get('id')
        provider_id1 = result1.get('response', {}).get('provider_id')
        tracking_id1 = result1.get('tracking_id')
        
        print(f"✅ First email sent")
        print(f"   UniPile ID: {unipile_id1}")
        print(f"   Provider ID: {provider_id1}")
        print(f"   Tracking ID: {tracking_id1}")
        
        # Create message record for first email
        message1 = Message.objects.create(
            conversation=conversation,
            channel=channel,
            external_message_id=unipile_id1,  # Store UniPile ID
            direction='outbound',
            subject=subject,
            content='<p>First email - this starts a new thread</p>',
            contact_email='josh@oneodigital.com',
            status='sent',
            sent_at=timezone.now(),
            metadata={
                'tracking_id': tracking_id1,
                'unipile_id': unipile_id1,
                'provider_id': provider_id1
            }
        )
        print(f"✅ Created message record: {message1.id}")
        
        # Wait a moment
        print("\n⏳ Waiting 3 seconds before sending reply...")
        time.sleep(3)
        
        # Send reply using the provider ID (Gmail Message-ID) as reply_to
        print(f"\n📧 Step 2: Sending reply using reply_to={provider_id1}")
        result2 = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': 'josh@oneodigital.com', 'display_name': 'Josh Cowan'}],
            subject=f"Re: {subject}",
            body='<p>Second email - this should be in the same thread</p>',
            reply_to=provider_id1  # Use the provider ID (Gmail Message-ID) from first email
        )
        
        if not result2.get('success'):
            print(f"❌ Failed to send reply: {result2.get('error')}")
            return False
            
        # Extract IDs from reply
        unipile_id2 = result2.get('response', {}).get('id')
        provider_id2 = result2.get('response', {}).get('provider_id')
        tracking_id2 = result2.get('tracking_id')
        
        print(f"✅ Reply sent")
        print(f"   UniPile ID: {unipile_id2}")
        print(f"   Provider ID: {provider_id2}")
        print(f"   Tracking ID: {tracking_id2}")
        
        # Create message record for reply
        message2 = Message.objects.create(
            conversation=conversation,
            channel=channel,
            external_message_id=unipile_id2,
            direction='outbound',
            subject=f"Re: {subject}",
            content='<p>Second email - this should be in the same thread</p>',
            contact_email='josh@oneodigital.com',
            status='sent',
            sent_at=timezone.now(),
            metadata={
                'tracking_id': tracking_id2,
                'unipile_id': unipile_id2,
                'provider_id': provider_id2,
                'reply_to': provider_id1  # Store provider ID used for threading
            }
        )
        print(f"✅ Created reply message record: {message2.id}")
        
        # Analysis
        print("\n" + "=" * 60)
        print("📊 THREADING ANALYSIS:")
        print("=" * 60)
        print(f"First email provider ID:  {provider_id1}")
        print(f"Reply used reply_to:       {provider_id1}")
        print(f"Reply UniPile ID:        {unipile_id2}")
        print("\n✅ Threading setup completed!")
        print("\n⚠️ IMPORTANT: Check your Gmail to verify if both emails")
        print("   appear in the same conversation thread.")
        print("\n📋 Messages in conversation:")
        
        for msg in Message.objects.filter(conversation=conversation).order_by('created_at'):
            print(f"   - {msg.subject} (ID: {msg.external_message_id})")
        
        return True

if __name__ == "__main__":
    success = test_correct_threading()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ THREADING TEST COMPLETED SUCCESSFULLY")
        print("Please check Gmail to verify threading works")
    else:
        print("❌ THREADING TEST FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)