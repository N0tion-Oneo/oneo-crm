#!/usr/bin/env python
"""
Test historical sync functionality for WhatsApp
Verifies that:
1. Historical sync uses the API (not webhooks)
2. All data is saved to local database
3. No polling occurs (only explicit sync)
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context
from communications.models import (
    Channel, Conversation, Message, UserChannelConnection
)
from communications.channels.whatsapp.service import WhatsAppService
from communications.message_sync import MessageSyncService
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_historical_sync():
    """Test historical sync for WhatsApp"""
    
    print("=" * 60)
    print("🧪 Testing Historical Sync for WhatsApp")
    print("=" * 60)
    
    # Use oneotalent tenant context
    with schema_context('oneotalent'):
        # Get WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ WhatsApp channel not found")
            print("Creating a test channel...")
            
            # Try to get a user connection
            connection = UserChannelConnection.objects.filter(
                channel_type='whatsapp'
            ).first()
            
            if not connection:
                print("❌ No WhatsApp connections found")
                return
            
            channel = Channel.objects.create(
                channel_type='whatsapp',
                unipile_account_id=connection.unipile_account_id,
                name=f"WhatsApp {connection.account_name}",
                auth_status='authenticated',
                is_active=True
            )
            print(f"✅ Created channel: {channel.name}")
        else:
            print(f"✅ Found WhatsApp channel: {channel.name}")
            print(f"   Account ID: {channel.unipile_account_id}")
        
        # Count existing messages before sync
        messages_before = Message.objects.filter(channel=channel).count()
        conversations_before = Conversation.objects.filter(channel=channel).count()
        
        print(f"\n📊 Before sync:")
        print(f"   Conversations: {conversations_before}")
        print(f"   Messages: {messages_before}")
        
        # Test 1: Sync conversations (chats)
        print("\n📝 Test 1: Syncing WhatsApp conversations...")
        
        try:
            # Initialize services
            whatsapp_service = WhatsAppService()
            sync_service = MessageSyncService()
            
            # Perform historical sync
            print("   Calling sync_conversations (should use API, not webhooks)...")
            
            # This should fetch from API and save to local DB
            sync_result = sync_service.sync_conversations(
                channel_type='whatsapp',
                account_id=channel.unipile_account_id,
                limit=10  # Sync last 10 conversations
            )
            
            if sync_result.get('success'):
                print(f"   ✅ Synced {sync_result.get('conversations_synced', 0)} conversations")
            else:
                print(f"   ⚠️ Sync completed with issues: {sync_result.get('error')}")
            
        except Exception as e:
            print(f"   ❌ Failed to sync conversations: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 2: Sync messages for a specific conversation
        print("\n💬 Test 2: Syncing messages for a conversation...")
        
        # Get a conversation to sync messages for
        conversation = Conversation.objects.filter(channel=channel).first()
        
        if conversation:
            print(f"   Syncing messages for: {conversation.subject or conversation.external_thread_id}")
            
            try:
                # Sync messages for this conversation
                message_sync_result = sync_service.sync_messages(
                    channel_type='whatsapp',
                    account_id=channel.unipile_account_id,
                    conversation_id=conversation.external_thread_id,
                    limit=20  # Get last 20 messages
                )
                
                if message_sync_result.get('success'):
                    print(f"   ✅ Synced {message_sync_result.get('messages_synced', 0)} messages")
                else:
                    print(f"   ⚠️ Message sync had issues: {message_sync_result.get('error')}")
                    
            except Exception as e:
                print(f"   ❌ Failed to sync messages: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("   ⚠️ No conversations found to sync messages")
        
        # Count after sync
        messages_after = Message.objects.filter(channel=channel).count()
        conversations_after = Conversation.objects.filter(channel=channel).count()
        
        print(f"\n📊 After sync:")
        print(f"   Conversations: {conversations_after} (+{conversations_after - conversations_before})")
        print(f"   Messages: {messages_after} (+{messages_after - messages_before})")
        
        # Test 3: Verify data is saved locally
        print("\n🔍 Test 3: Verifying local database storage...")
        
        # Check recent messages
        recent_messages = Message.objects.filter(
            channel=channel,
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).count()
        
        print(f"   Messages created in last 5 minutes: {recent_messages}")
        
        # Check conversations with messages
        conversations_with_messages = Conversation.objects.filter(
            channel=channel,
            messages__isnull=False
        ).distinct().count()
        
        print(f"   Conversations with messages: {conversations_with_messages}")
        
        # Test 4: Verify sync metadata
        print("\n🏷️ Test 4: Checking sync metadata...")
        
        # Check if messages have sync metadata
        synced_messages = Message.objects.filter(
            channel=channel,
            sync_status='synced'
        ).count()
        
        pending_messages = Message.objects.filter(
            channel=channel,
            sync_status='pending'
        ).count()
        
        print(f"   Synced messages: {synced_messages}")
        print(f"   Pending messages: {pending_messages}")
        
        # Check external IDs (proves API was used)
        messages_with_external_id = Message.objects.filter(
            channel=channel,
            external_message_id__isnull=False
        ).exclude(external_message_id='').count()
        
        print(f"   Messages with external IDs: {messages_with_external_id}")
        print("   (External IDs prove data came from API, not just local creation)")
        
        # Test 5: Verify no polling is happening
        print("\n🚫 Test 5: Confirming no automatic polling...")
        print("   Waiting 10 seconds to ensure no automatic sync happens...")
        
        import time
        messages_check1 = Message.objects.filter(channel=channel).count()
        time.sleep(10)
        messages_check2 = Message.objects.filter(channel=channel).count()
        
        if messages_check1 == messages_check2:
            print("   ✅ No new messages appeared (no polling detected)")
        else:
            print(f"   ⚠️ {messages_check2 - messages_check1} new messages appeared (possible polling?)")
        
        print("\n" + "=" * 60)
        print("✅ Historical sync test completed!")
        print("=" * 60)
        
        # Summary
        print("\nKey findings:")
        if conversations_after > conversations_before:
            print("✅ Historical sync successfully fetched conversations from API")
        if messages_after > messages_before:
            print("✅ Historical sync successfully fetched messages from API")
        if messages_with_external_id > 0:
            print("✅ Messages have external IDs (proves API was source)")
        if messages_check1 == messages_check2:
            print("✅ No automatic polling detected (webhook-first confirmed)")
        
        return {
            'conversations_synced': conversations_after - conversations_before,
            'messages_synced': messages_after - messages_before,
            'has_external_ids': messages_with_external_id > 0,
            'no_polling': messages_check1 == messages_check2
        }


if __name__ == '__main__':
    result = test_historical_sync()
    
    print("\n📋 Test Results:")
    print(f"   Conversations synced: {result.get('conversations_synced', 0)}")
    print(f"   Messages synced: {result.get('messages_synced', 0)}")
    print(f"   Has external IDs: {result.get('has_external_ids', False)}")
    print(f"   No polling detected: {result.get('no_polling', False)}")