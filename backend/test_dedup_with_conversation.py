#!/usr/bin/env python
"""
Test email deduplication with conversation context
"""
import os
import sys
import django
import json
from datetime import datetime, timedelta
import time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Conversation, Message, Channel
from pipelines.models import Record
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
import logging

# Configure logging  
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dedup_with_conversation():
    """Test deduplication when sending from record context"""
    
    print("=" * 60)
    print("Testing Email Deduplication with Conversation")
    print("=" * 60)
    
    # Get tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    print(f"✅ Tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get Gmail connection
        conn = UserChannelConnection.objects.filter(channel_type='gmail').first()
        if not conn:
            print("❌ No Gmail connection found")
            return False
        print(f"✅ Gmail: {conn.account_name}")
        
        # Get or create a test conversation
        channel = Channel.objects.filter(
            channel_type='gmail',
            unipile_account_id=conn.unipile_account_id
        ).first()
        
        if not channel:
            print("❌ No Gmail channel found")
            return False
            
        # Create a test conversation with a known thread_id
        test_thread_id = f"test_thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=test_thread_id,
            subject=f"Dedup Test Conversation - {datetime.now().strftime('%H:%M:%S')}",
            status='active'
        )
        print(f"✅ Created test conversation: {conversation.id}")
        print(f"   Thread ID: {test_thread_id}")
        
        # Count messages before
        before_count = Message.objects.filter(conversation=conversation).count()
        
        # Send email using the API logic (simulated)
        from communications.channels.email.service import EmailService
        from communications.record_communications.models import RecordCommunicationProfile
        
        service = EmailService()
        subject = f"Dedup Test - {datetime.now().strftime('%H:%M:%S')}"
        to = ['test@example.com']
        body = '<p>Testing deduplication with tracking_id in conversation context</p>'
        
        print(f"\n📧 Sending email: {subject}")
        
        # Send with thread_id from conversation
        result = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': email, 'display_name': ''} for email in to],
            subject=subject,
            body=body,
            thread_id=conversation.external_thread_id  # Use conversation's thread_id
        )
        
        if result.get('success'):
            tracking_id = result.get('tracking_id')
            unipile_id = result.get('response', {}).get('id')
            provider_id = result.get('response', {}).get('provider_id')
            
            print(f"✅ Email sent successfully")
            print(f"   Tracking ID: {tracking_id}")
            print(f"   UniPile ID: {unipile_id}")
            print(f"   Provider ID: {provider_id}")
            
            # Create message like the API does
            message = Message.objects.create(
                conversation=conversation,
                channel=conversation.channel,
                external_message_id=unipile_id,
                direction='outbound',
                subject=subject,
                content=body,
                contact_email=to[0],
                status='sent',
                sent_at=timezone.now(),
                metadata={
                    'from': {'email': conn.user.email, 'name': conn.user.get_full_name()},
                    'to': [{'email': email, 'name': ''} for email in to],
                    'tracking_id': tracking_id,
                    'unipile_id': unipile_id,
                    'provider_id': provider_id,
                    'thread_id': conversation.external_thread_id,
                    'sent_via': 'test_script'
                }
            )
            print(f"✅ Created message: {message.id}")
            
            # Check count after creation
            after_send = Message.objects.filter(conversation=conversation).count()
            print(f"\n📊 Message count in conversation:")
            print(f"   Before: {before_count}")
            print(f"   After send: {after_send}")
            print(f"   Messages created: {after_send - before_count}")
            
            # Wait for webhook
            print(f"\n⏳ Waiting 20 seconds for webhook...")
            time.sleep(20)
            
            # Check final count
            after_webhook = Message.objects.filter(conversation=conversation).count()
            
            print(f"\n📊 Final count:")
            print(f"   After webhook: {after_webhook}")
            print(f"   Total messages: {after_webhook}")
            
            # Check for our message
            our_message = Message.objects.get(id=message.id)
            print(f"\n🔍 Our message status:")
            print(f"   External ID: {our_message.external_message_id}")
            print(f"   Has webhook data: {'raw_webhook_data' in (our_message.metadata or {})}")
            print(f"   Webhook processed: {our_message.metadata.get('webhook_processed', False) if our_message.metadata else False}")
            
            if our_message.metadata and 'raw_webhook_data' in our_message.metadata:
                webhook_data = our_message.metadata['raw_webhook_data']
                print(f"   Webhook tracking_id: {webhook_data.get('tracking_id')}")
                print(f"   Webhook message_id: {webhook_data.get('message_id')}")
            
            # Check if deduplication worked
            if after_webhook == 1:
                print(f"\n✅ SUCCESS: Only 1 message in conversation (deduplication working!)")
                
                # Check if it was updated
                if our_message.metadata.get('webhook_processed'):
                    print("✅ Message was updated with webhook data")
                    if our_message.external_message_id.startswith('<'):
                        print("✅ External ID updated to Gmail Message-ID")
                return True
            else:
                print(f"\n❌ FAILED: {after_webhook} messages in conversation (expected 1)")
                
                # Show all messages
                for msg in Message.objects.filter(conversation=conversation):
                    print(f"\n   Message {msg.id}:")
                    print(f"     External ID: {msg.external_message_id}")
                    print(f"     tracking_id: {msg.metadata.get('tracking_id') if msg.metadata else 'N/A'}")
                    print(f"     Created: {msg.created_at}")
                
                return False
        else:
            print(f"❌ Failed to send email: {result.get('error')}")
            return False

if __name__ == "__main__":
    from django.utils import timezone
    success = test_dedup_with_conversation()
    sys.exit(0 if success else 1)