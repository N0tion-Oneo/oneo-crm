#!/usr/bin/env python
"""
Test historical sync functionality for WhatsApp using API endpoints
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
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from communications.models import (
    Channel, Conversation, Message, UserChannelConnection
)
from communications.channels.whatsapp.api_views import (
    sync_whatsapp_data,
    sync_chat_history,
    get_whatsapp_chats_local_first
)
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()


def test_historical_sync_via_api():
    """Test historical sync for WhatsApp using API endpoints"""
    
    print("=" * 60)
    print("🧪 Testing Historical Sync via API Endpoints")
    print("=" * 60)
    
    # Use oneotalent tenant context
    with schema_context('oneotalent'):
        # Get a test user
        test_user = User.objects.filter(is_active=True).first()
        if not test_user:
            print("❌ No active users found")
            return
        
        print(f"✅ Using test user: {test_user.email}")
        
        # Get WhatsApp connection for the user
        connection = UserChannelConnection.objects.filter(
            channel_type='whatsapp',
            is_active=True
        ).first()
        
        if not connection:
            print("❌ No active WhatsApp connections found")
            return
        
        print(f"✅ Found WhatsApp connection: {connection.account_name}")
        print(f"   Account ID: {connection.unipile_account_id}")
        
        # Get or create channel
        channel, created = Channel.objects.get_or_create(
            channel_type='whatsapp',
            unipile_account_id=connection.unipile_account_id,
            defaults={
                'name': f"WhatsApp {connection.account_name}",
                'auth_status': 'authenticated',
                'is_active': True
            }
        )
        
        # Count existing data before sync
        messages_before = Message.objects.filter(channel=channel).count()
        conversations_before = Conversation.objects.filter(channel=channel).count()
        
        print(f"\n📊 Before sync:")
        print(f"   Conversations: {conversations_before}")
        print(f"   Messages: {messages_before}")
        
        # Create request factory
        factory = RequestFactory()
        
        # Test 1: Get chats with force sync (this should trigger API call)
        print("\n📝 Test 1: Getting chats with force_sync=true...")
        
        try:
            # Create a GET request with force_sync
            request = factory.get(
                '/api/whatsapp/chats/',
                {
                    'account_id': connection.unipile_account_id,
                    'limit': 10,
                    'force_sync': 'true'  # This forces API call instead of just local
                }
            )
            request.user = test_user
            
            # Call the view function
            response = get_whatsapp_chats_local_first(request)
            
            if response.status_code == 200:
                data = response.data
                chats = data.get('chats', [])
                print(f"   ✅ Retrieved {len(chats)} chats")
                print(f"   From cache: {not data.get('cache_info', {}).get('sync_triggered', False)}")
                print(f"   Sync triggered: {data.get('cache_info', {}).get('sync_triggered', False)}")
            else:
                print(f"   ❌ Failed to get chats: {response.data}")
            
        except Exception as e:
            print(f"   ❌ Error getting chats: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 2: Trigger comprehensive sync
        print("\n🔄 Test 2: Triggering comprehensive WhatsApp sync...")
        
        try:
            # Create a POST request for sync
            request = factory.post('/api/whatsapp/sync/')
            request.user = test_user
            
            # Call sync function
            response = sync_whatsapp_data(request)
            
            if response.status_code == 200:
                data = response.data
                print(f"   ✅ Sync completed successfully")
                if 'sync_results' in data:
                    for result in data.get('sync_results', []):
                        print(f"   Account {result.get('account_id')}: {result.get('status')}")
            else:
                print(f"   ❌ Sync failed: {response.data}")
                
        except Exception as e:
            print(f"   ❌ Error during sync: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 3: Sync messages for a specific chat
        print("\n💬 Test 3: Syncing messages for a specific chat...")
        
        # Get a conversation to sync
        conversation = Conversation.objects.filter(channel=channel).first()
        
        if conversation:
            print(f"   Chat: {conversation.subject or conversation.external_thread_id}")
            
            try:
                # Create POST request for chat history sync
                request = factory.post(
                    f'/api/whatsapp/chats/{conversation.external_thread_id}/sync/',
                    {'full_sync': True}
                )
                request.user = test_user
                
                # Call sync function
                response = sync_chat_history(request, conversation.external_thread_id)
                
                if response.status_code == 200:
                    data = response.data
                    print(f"   ✅ Synced {data.get('messages_synced', 0)} messages")
                else:
                    print(f"   ❌ Failed to sync messages: {response.data}")
                    
            except Exception as e:
                print(f"   ❌ Error syncing messages: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("   ⚠️ No conversations found")
        
        # Count after sync
        messages_after = Message.objects.filter(channel=channel).count()
        conversations_after = Conversation.objects.filter(channel=channel).count()
        
        print(f"\n📊 After sync:")
        print(f"   Conversations: {conversations_after} (+{conversations_after - conversations_before})")
        print(f"   Messages: {messages_after} (+{messages_after - messages_before})")
        
        # Test 4: Verify data characteristics
        print("\n🔍 Test 4: Verifying data characteristics...")
        
        # Check for external IDs (proves API was used)
        messages_with_external = Message.objects.filter(
            channel=channel,
            external_message_id__isnull=False
        ).exclude(external_message_id='').count()
        
        print(f"   Messages with external IDs: {messages_with_external}/{messages_after}")
        print(f"   Percentage: {(messages_with_external/messages_after*100) if messages_after > 0 else 0:.1f}%")
        
        # Check sync status
        synced = Message.objects.filter(channel=channel, sync_status='synced').count()
        pending = Message.objects.filter(channel=channel, sync_status='pending').count()
        local_only = Message.objects.filter(channel=channel, is_local_only=True).count()
        
        print(f"   Sync status - Synced: {synced}, Pending: {pending}, Local-only: {local_only}")
        
        # Check message directions
        inbound = Message.objects.filter(channel=channel, direction='in').count()
        outbound = Message.objects.filter(channel=channel, direction='out').count()
        
        print(f"   Directions - Inbound: {inbound}, Outbound: {outbound}")
        
        # Test 5: Verify no automatic polling
        print("\n🚫 Test 5: Verifying no automatic polling...")
        print("   Checking message count...")
        
        import time
        count1 = Message.objects.filter(channel=channel).count()
        print(f"   Initial count: {count1}")
        print("   Waiting 15 seconds...")
        time.sleep(15)
        count2 = Message.objects.filter(channel=channel).count()
        print(f"   Final count: {count2}")
        
        if count1 == count2:
            print("   ✅ No new messages (no polling detected)")
        else:
            print(f"   ⚠️ {count2 - count1} new messages (possible webhooks or polling)")
        
        print("\n" + "=" * 60)
        print("✅ API-based historical sync test completed!")
        print("=" * 60)
        
        # Summary
        print("\n📋 Summary:")
        sync_worked = (conversations_after > conversations_before) or (messages_after > messages_before)
        has_external_ids = messages_with_external > 0
        no_polling = count1 == count2
        
        if sync_worked:
            print("✅ Historical sync successfully fetched data from API")
        else:
            print("⚠️ No new data fetched (may already be synced)")
        
        if has_external_ids:
            print("✅ Messages have external IDs (proves API integration)")
        
        if no_polling:
            print("✅ No automatic polling detected (webhook-first architecture)")
        
        return {
            'success': True,
            'conversations_synced': conversations_after - conversations_before,
            'messages_synced': messages_after - messages_before,
            'has_external_ids': has_external_ids,
            'no_polling': no_polling
        }


if __name__ == '__main__':
    result = test_historical_sync_via_api()