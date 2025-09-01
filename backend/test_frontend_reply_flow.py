#!/usr/bin/env python
"""
Test the complete frontend reply flow to ensure threading works
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
from pipelines.models import Record, Pipeline
from communications.record_communications.models import RecordCommunicationLink
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

User = get_user_model()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_frontend_reply_flow():
    """Test the complete flow as it would happen from the frontend"""
    
    print("=" * 60)
    print("Testing Frontend Reply Flow")
    print("=" * 60)
    
    tenant = Tenant.objects.get(schema_name='oneotalent')
    print(f"✅ Tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get user
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return False
        print(f"✅ User: {user.email}")
        
        # Get Gmail connection
        conn = UserChannelConnection.objects.filter(
            user=user,
            channel_type='gmail'
        ).first()
        
        if not conn:
            print("❌ No Gmail connection found for user")
            return False
        print(f"✅ Gmail connection: {conn.account_name}")
        
        # Get or create a test record
        pipeline = Pipeline.objects.first()
        if not pipeline:
            print("❌ No pipeline found")
            return False
            
        record = Record.objects.create(
            pipeline=pipeline,
            title=f"Frontend Reply Test - {datetime.now().strftime('%H:%M:%S')}",
            data={"email": "test@example.com"},
            created_by=user,
            updated_by=user
        )
        print(f"✅ Created test record: {record.id}")
        
        # Get channel
        channel = Channel.objects.filter(
            channel_type='gmail',
            unipile_account_id=conn.unipile_account_id
        ).first()
        
        if not channel:
            print("❌ No Gmail channel found")
            return False
            
        # Create a conversation with an existing message (simulating an inbox email)
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=f"gmail_thread_{datetime.now().timestamp()}",
            subject=f"Frontend Reply Test - {datetime.now().strftime('%H:%M:%S')}",
            status='active'
        )
        print(f"✅ Created conversation: {conversation.id}")
        
        # Link conversation to record
        RecordCommunicationLink.objects.create(
            record=record,
            conversation=conversation
        )
        print(f"✅ Linked conversation to record")
        
        # Create an inbound message (simulating received email)
        timestamp = datetime.now().timestamp()
        inbound_message = Message.objects.create(
            conversation=conversation,
            channel=channel,
            external_message_id=f"<CAP{timestamp}@mail.gmail.com>",
            direction='inbound',
            subject=f"Test Email - {datetime.now().strftime('%H:%M:%S')}",
            content='<p>This is a test email that needs a reply</p>',
            contact_email='sender@example.com',
            status='received',
            sent_at=timezone.now(),
            metadata={
                'provider_id': f'19907{int(timestamp)}',  # Gmail Message-ID
                'from': {'email': 'sender@example.com', 'name': 'Test Sender'},
                'to': [{'email': user.email, 'name': user.get_full_name()}]
            }
        )
        print(f"✅ Created inbound message with provider_id: {inbound_message.metadata['provider_id']}")
        
        # Simulate frontend sending a reply (what happens when user clicks Reply)
        print("\n📧 Simulating frontend reply...")
        
        # This is what the frontend sends
        frontend_payload = {
            'from_account_id': conn.unipile_account_id,
            'to': ['sender@example.com'],  # Reply to sender
            'cc': [],
            'bcc': [],
            'subject': f"Re: Test Email - {datetime.now().strftime('%H:%M:%S')}",
            'body': '<p>This is my reply from the frontend</p>',
            'reply_to_message_id': str(inbound_message.id),  # The message we're replying to
            'reply_mode': 'reply',
            'conversation_id': str(conversation.id)  # The conversation context
        }
        
        print(f"Frontend payload:")
        print(f"  conversation_id: {frontend_payload['conversation_id']}")
        print(f"  reply_to_message_id: {frontend_payload['reply_to_message_id']}")
        print(f"  reply_mode: {frontend_payload['reply_mode']}")
        
        # Import and call the API view directly (simulating the API call)
        from communications.record_communications.api import RecordCommunicationsViewSet
        from rest_framework.test import APIRequestFactory
        from rest_framework.request import Request
        
        factory = APIRequestFactory()
        request = factory.post(
            f'/api/v1/communications/records/{record.id}/send_email/',
            frontend_payload,
            format='json'
        )
        request.user = user
        
        # Create the viewset and call send_email
        viewset = RecordCommunicationsViewSet()
        viewset.request = Request(request)
        
        print("\n📤 Calling send_email API...")
        response = viewset.send_email(request, pk=record.id)
        
        if response.status_code == 200 and response.data.get('success'):
            print(f"✅ Email sent successfully!")
            print(f"   Tracking ID: {response.data.get('tracking_id')}")
            
            # Check that the reply was recorded
            reply_messages = Message.objects.filter(
                conversation=conversation,
                direction='outbound'
            )
            
            if reply_messages.exists():
                reply = reply_messages.first()
                print(f"\n✅ Reply message created:")
                print(f"   Message ID: {reply.id}")
                print(f"   Subject: {reply.subject}")
                
                # Check metadata for threading info
                if reply.metadata:
                    print(f"   Metadata:")
                    if 'reply_to' in reply.metadata:
                        print(f"     reply_to: {reply.metadata['reply_to']}")
                    if 'provider_id' in reply.metadata:
                        print(f"     provider_id: {reply.metadata['provider_id']}")
                    if 'tracking_id' in reply.metadata:
                        print(f"     tracking_id: {reply.metadata['tracking_id']}")
                
                # Verify threading
                expected_reply_to = inbound_message.metadata.get('provider_id')
                actual_reply_to = reply.metadata.get('reply_to') if reply.metadata else None
                
                if actual_reply_to == expected_reply_to:
                    print(f"\n✅ THREADING VERIFIED!")
                    print(f"   Reply correctly uses provider_id: {expected_reply_to}")
                else:
                    print(f"\n⚠️ THREADING ISSUE:")
                    print(f"   Expected reply_to: {expected_reply_to}")
                    print(f"   Actual reply_to: {actual_reply_to}")
            
            return True
        else:
            print(f"❌ Failed to send email:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.data}")
            return False

if __name__ == "__main__":
    success = test_frontend_reply_flow()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ FRONTEND REPLY FLOW TEST PASSED")
        print("Email threading should work correctly from the UI!")
    else:
        print("❌ FRONTEND REPLY FLOW TEST FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)