#!/usr/bin/env python
"""
Test complete email threading functionality
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Conversation, Message
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_threading_complete():
    """Test complete email threading with thread_id"""
    
    print("=" * 60)
    print("Testing Complete Email Threading")
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
        
        # Find a conversation with messages
        conversation = Conversation.objects.filter(
            external_thread_id__isnull=False,
            channel__channel_type='gmail',
            messages__isnull=False
        ).exclude(external_thread_id='').first()
        
        if conversation:
            print(f"\n📧 Found conversation with thread:")
            print(f"   Conversation ID: {conversation.id}")
            print(f"   Thread ID: {conversation.external_thread_id}")
            print(f"   Subject: {conversation.subject}")
            print(f"   Messages: {conversation.messages.count()}")
            
            # Get a message from this conversation
            message = conversation.messages.filter(
                contact_email__isnull=False
            ).exclude(contact_email='').first()
            
            if message:
                print(f"\n📨 Found message in thread:")
                print(f"   Message ID: {message.id}")
                print(f"   External ID: {message.external_message_id}")
                print(f"   Contact: {message.contact_email}")
                
                # Test sending with thread_id to maintain thread
                print(f"\n📤 Sending reply with thread_id...")
                
                service = EmailService()
                
                # Prepare reply
                test_to = [{'identifier': message.contact_email, 'display_name': ''}]
                reply_subject = f"Re: {conversation.subject}" if not conversation.subject.startswith('Re:') else conversation.subject
                reply_body = f"""
                <p>Testing thread continuity with thread_id.</p>
                <p>Thread ID: {conversation.external_thread_id}</p>
                <p>Conversation: {conversation.id}</p>
                <p>Time: {datetime.now().isoformat()}</p>
                """
                
                # Send with thread_id
                result = async_to_sync(service.send_email)(
                    account_id=conn.unipile_account_id,
                    to=test_to,
                    subject=reply_subject,
                    body=reply_body,
                    thread_id=conversation.external_thread_id  # This maintains the thread
                )
                
                if result.get('success'):
                    print(f"✅ Reply sent with thread_id!")
                    print(f"   Tracking ID: {result.get('tracking_id')}")
                    print(f"   UniPile ID: {result.get('response', {}).get('id')}")
                    print(f"   Provider ID: {result.get('response', {}).get('provider_id')}")
                    print(f"\n✅ Email should appear in the same thread!")
                else:
                    print(f"❌ Failed: {result.get('error')}")
                    return False
            else:
                print("⚠️ No messages with contact email in conversation")
        else:
            print("⚠️ No conversations with threads found")
            
        print("\n" + "=" * 60)
        print("Threading test complete!")
        print("Note: Check your email client to verify the message")
        print("appears in the same conversation thread.")
        print("=" * 60)
        return True

if __name__ == "__main__":
    test_threading_complete()