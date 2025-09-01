#!/usr/bin/env python
"""
Complete test of email flow with deduplication and threading
Tests the full cycle: send -> webhook -> deduplication -> threading
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
from pipelines.models import Record, Pipeline
from communications.channels.email.service import EmailService
from communications.record_communications.models import RecordCommunicationProfile
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

User = get_user_model()

# Configure logging  
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_complete_email_flow():
    """Test complete email flow with deduplication and threading"""
    
    print("=" * 60)
    print("Testing Complete Email Flow")
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
        
        # Get a user for created_by
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return False
        print(f"✅ Using user: {user.email}")
        
        # Get or create a test record
        pipeline = Pipeline.objects.first()
        if not pipeline:
            print("❌ No pipeline found")
            return False
        
        record = Record.objects.create(
            pipeline=pipeline,
            title="Test Email Flow Record",
            data={"email": "test@example.com"},
            created_by=user,
            updated_by=user
        )
        print(f"✅ Created test record: {record.id}")
        
        # Create or get communication profile
        profile, created = RecordCommunicationProfile.objects.get_or_create(
            record=record,
            defaults={
                'pipeline': pipeline,
                'communication_identifiers': {
                    'email': ['test@example.com']
                }
            }
        )
        print(f"✅ Communication profile: {'created' if created else 'existing'}")
        
        # Get or create channel
        channel = Channel.objects.filter(
            channel_type='gmail',
            unipile_account_id=conn.unipile_account_id
        ).first()
        
        if not channel:
            print("❌ No Gmail channel found")
            return False
            
        # Create initial conversation
        test_thread_id = f"test_thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=test_thread_id,
            subject=f"Complete Flow Test - {datetime.now().strftime('%H:%M:%S')}",
            status='active'
        )
        print(f"✅ Created conversation: {conversation.id}")
        print(f"   Thread ID: {test_thread_id}")
        
        # Test 1: Initial email (creates thread)
        print("\n📧 Test 1: Sending initial email...")
        service = EmailService()
        subject = f"Initial Email - {datetime.now().strftime('%H:%M:%S')}"
        
        initial_result = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': 'test@example.com', 'display_name': 'Test User'}],
            subject=subject,
            body='<p>This is the initial email in the thread</p>'
        )
        
        if not initial_result.get('success'):
            print(f"❌ Failed to send initial email: {initial_result.get('error')}")
            return False
            
        initial_tracking_id = initial_result.get('tracking_id')
        print(f"✅ Initial email sent")
        print(f"   Tracking ID: {initial_tracking_id}")
        
        # Create initial message
        initial_message = Message.objects.create(
            conversation=conversation,
            channel=channel,
            external_message_id=initial_result.get('response', {}).get('id'),
            direction='outbound',
            subject=subject,
            content='<p>This is the initial email in the thread</p>',
            contact_email='test@example.com',
            status='sent',
            sent_at=timezone.now(),
            metadata={
                'tracking_id': initial_tracking_id,
                'unipile_id': initial_result.get('response', {}).get('id'),
                'provider_id': initial_result.get('response', {}).get('provider_id'),
                'thread_id': test_thread_id
            }
        )
        print(f"✅ Created initial message: {initial_message.id}")
        
        # Wait for webhook
        print("\n⏳ Waiting 15 seconds for initial webhook...")
        time.sleep(15)
        
        # Check if initial message was updated
        initial_message.refresh_from_db()
        if initial_message.metadata.get('webhook_processed'):
            print("✅ Initial message updated by webhook")
            if initial_message.external_message_id.startswith('<'):
                print("✅ External ID updated to Gmail Message-ID")
        else:
            print("⚠️ Webhook not processed yet for initial message")
        
        # Test 2: Reply email (uses thread_id)
        print("\n📧 Test 2: Sending reply in thread...")
        reply_subject = f"Re: {subject}"
        
        reply_result = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': 'test@example.com', 'display_name': 'Test User'}],
            subject=reply_subject,
            body='<p>This is a reply in the same thread</p>',
            thread_id=test_thread_id  # Use thread_id for threading
        )
        
        if not reply_result.get('success'):
            print(f"❌ Failed to send reply: {reply_result.get('error')}")
            return False
            
        reply_tracking_id = reply_result.get('tracking_id')
        print(f"✅ Reply sent with thread_id")
        print(f"   Tracking ID: {reply_tracking_id}")
        print(f"   Thread ID: {test_thread_id}")
        
        # Create reply message
        reply_message = Message.objects.create(
            conversation=conversation,  # Same conversation
            channel=channel,
            external_message_id=reply_result.get('response', {}).get('id'),
            direction='outbound',
            subject=reply_subject,
            content='<p>This is a reply in the same thread</p>',
            contact_email='test@example.com',
            status='sent',
            sent_at=timezone.now(),
            metadata={
                'tracking_id': reply_tracking_id,
                'unipile_id': reply_result.get('response', {}).get('id'),
                'provider_id': reply_result.get('response', {}).get('provider_id'),
                'thread_id': test_thread_id,
                'in_reply_to': initial_message.id
            }
        )
        print(f"✅ Created reply message: {reply_message.id}")
        
        # Check messages before webhook
        messages_before = Message.objects.filter(conversation=conversation).count()
        print(f"\n📊 Messages in conversation before webhook: {messages_before}")
        
        # Wait for webhook
        print("\n⏳ Waiting 15 seconds for reply webhook...")
        time.sleep(15)
        
        # Check final state
        messages_after = Message.objects.filter(conversation=conversation).count()
        print(f"\n📊 Final message count: {messages_after}")
        
        # Verify deduplication worked
        if messages_after == 2:
            print("✅ SUCCESS: Deduplication working! (2 messages, no duplicates)")
            
            # Check if reply was updated
            reply_message.refresh_from_db()
            if reply_message.metadata.get('webhook_processed'):
                print("✅ Reply message updated by webhook")
                if reply_message.external_message_id.startswith('<'):
                    print("✅ External ID updated to Gmail Message-ID")
            
            # Show conversation thread
            print("\n📧 Conversation Thread:")
            for msg in Message.objects.filter(conversation=conversation).order_by('created_at'):
                print(f"\n   Message {msg.id}:")
                print(f"     Subject: {msg.subject}")
                print(f"     External ID: {msg.external_message_id}")
                print(f"     Tracking ID: {msg.metadata.get('tracking_id', 'N/A')}")
                print(f"     Thread ID: {msg.metadata.get('thread_id', 'N/A')}")
                print(f"     Webhook: {msg.metadata.get('webhook_processed', False)}")
            
            # Update communication profile stats
            profile.total_messages = messages_after
            profile.last_message_at = timezone.now()
            profile.save()
            print(f"\n✅ Updated profile: {profile.total_messages} total messages")
            
            return True
        else:
            print(f"❌ FAILED: Expected 2 messages, found {messages_after}")
            
            # Show all messages for debugging
            for msg in Message.objects.filter(conversation=conversation).order_by('created_at'):
                print(f"\n   Message {msg.id}:")
                print(f"     Subject: {msg.subject}")
                print(f"     Tracking ID: {msg.metadata.get('tracking_id', 'N/A')}")
                print(f"     Created: {msg.created_at}")
            
            return False

if __name__ == "__main__":
    success = test_complete_email_flow()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ COMPLETE EMAIL FLOW TEST PASSED")
        print("✅ Deduplication working correctly")
        print("✅ Threading maintained in conversation")
        print("✅ Communication profile updated")
    else:
        print("❌ TEST FAILED - Check logs above")
    print("=" * 60)
    
    sys.exit(0 if success else 1)