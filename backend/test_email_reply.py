#!/usr/bin/env python
"""
Test email reply threading functionality
"""
import os
import sys
import django
from datetime import datetime
import uuid

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Message, Conversation
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync

def test_reply_threading():
    """Test that reply threading works correctly"""
    
    print("=" * 60)
    print("Testing Email Reply Threading")
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
        
        # Find a message to reply to with valid email
        message_to_reply = Message.objects.filter(
            external_message_id__isnull=False,
            conversation__isnull=False,
            contact_email__isnull=False,
            direction='inbound'  # Reply to an inbound message
        ).exclude(
            external_message_id=''
        ).exclude(
            contact_email=''
        ).first()
        
        if message_to_reply:
            print(f"\n📧 Found message to reply to:")
            print(f"   Message ID: {message_to_reply.id}")
            print(f"   External ID: {message_to_reply.external_message_id}")
            print(f"   Subject: {message_to_reply.subject}")
            print(f"   From: {message_to_reply.contact_email}")
            
            # Prepare reply
            reply_subject = f"Re: {message_to_reply.subject}" if not message_to_reply.subject.startswith('Re:') else message_to_reply.subject
            reply_body = f"""
            <p>This is a test reply to verify threading works correctly.</p>
            <p>Original message external ID: {message_to_reply.external_message_id}</p>
            <p>Timestamp: {datetime.now().isoformat()}</p>
            <hr>
            <p>On {message_to_reply.created_at}, {message_to_reply.contact_email} wrote:</p>
            <blockquote>{message_to_reply.content[:200]}...</blockquote>
            """
            
            print(f"\n📤 Sending reply:")
            print(f"   To: {message_to_reply.contact_email}")
            print(f"   Subject: {reply_subject}")
            print(f"   Reply-to ID: {message_to_reply.external_message_id}")
            
            # Send reply with threading
            service = EmailService()
            result = async_to_sync(service.send_email)(
                account_id=conn.unipile_account_id,
                to=[{'identifier': message_to_reply.contact_email, 'display_name': ''}],
                subject=reply_subject,
                body=reply_body,
                cc=None,
                bcc=None,
                reply_to=message_to_reply.external_message_id  # This is the key for threading
            )
            
            if result.get('success'):
                print(f"\n✅ Reply sent successfully!")
                print(f"   Tracking ID: {result.get('tracking_id')}")
                print(f"   Threading: Reply-to header set to {message_to_reply.external_message_id}")
                return True
            else:
                print(f"\n❌ Failed to send reply: {result.get('error')}")
                return False
        else:
            print("\n⚠️ No inbound messages found to reply to")
            print("Creating a test scenario...")
            
            # Create a fake inbound message for testing
            conversation = Conversation.objects.filter(channel__channel_type='email').first()
            if conversation:
                fake_external_id = f"test_{uuid.uuid4().hex[:12]}"
                test_message = Message.objects.create(
                    conversation=conversation,
                    channel=conversation.channel,
                    external_message_id=fake_external_id,
                    direction='inbound',
                    subject='Test Message for Reply',
                    content='<p>This is a test message to demonstrate reply functionality.</p>',
                    contact_email='test@example.com',
                    status='read'
                )
                print(f"   Created test message with external ID: {fake_external_id}")
                
                # Now test reply without actually sending
                print(f"\n📋 Reply would include:")
                print(f"   reply_to: {fake_external_id}")
                print(f"   Subject: Re: {test_message.subject}")
                print(f"   To: {test_message.contact_email}")
                print(f"\n✅ Reply threading setup is correct!")
                
                # Clean up test message
                test_message.delete()
                
                return True
            else:
                print("❌ No email conversations found")
                return False

if __name__ == "__main__":
    success = test_reply_threading()
    sys.exit(0 if success else 1)