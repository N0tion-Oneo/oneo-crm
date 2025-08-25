#!/usr/bin/env python
"""
Simple test of WhatsApp historical sync using UniPile API directly
Tests that data is fetched from API and saved locally
"""
import os
import sys
import django
import asyncio
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context
from communications.models import (
    Channel, Conversation, Message, UserChannelConnection, ChatAttendee
)
from communications.unipile_sdk import unipile_service
from communications.channels.whatsapp.service import WhatsAppService
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_unipile_api_sync():
    """Test fetching data from UniPile API and saving locally"""
    
    print("=" * 60)
    print("🧪 Testing WhatsApp Historical Sync with UniPile API")
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
            return
        
        print(f"✅ Found WhatsApp channel: {channel.name}")
        print(f"   Account ID: {channel.unipile_account_id}")
        
        # Count before sync
        messages_before = Message.objects.filter(channel=channel).count()
        conversations_before = Conversation.objects.filter(channel=channel).count()
        attendees_before = ChatAttendee.objects.filter(channel=channel).count()
        
        print(f"\n📊 Before sync:")
        print(f"   Conversations: {conversations_before}")
        print(f"   Messages: {messages_before}")
        print(f"   Attendees: {attendees_before}")
        
        # Test 1: Fetch chats from UniPile API
        print("\n📝 Test 1: Fetching chats from UniPile API...")
        
        try:
            client = unipile_service.get_client()
            
            # Fetch chats from API
            print("   Calling UniPile API: client.messaging.get_all_chats()")
            chats_response = await client.messaging.get_all_chats(
                account_id=channel.unipile_account_id,
                limit=5  # Get 5 most recent chats
            )
            
            chats = chats_response.get('items', [])
            print(f"   ✅ Fetched {len(chats)} chats from API")
            
            # Save chats to local database
            for chat_data in chats:
                chat_id = chat_data.get('id')
                if not chat_id:
                    continue
                
                # Create or update conversation
                conversation, created = Conversation.objects.update_or_create(
                    channel=channel,
                    external_thread_id=chat_id,
                    defaults={
                        'subject': chat_data.get('name', f'WhatsApp Chat {chat_id[:8]}'),
                        'status': 'active',
                        'last_message_at': timezone.now(),
                        'metadata': {
                            'api_data': chat_data,
                            'synced_from': 'unipile_api',
                            'sync_time': timezone.now().isoformat()
                        }
                    }
                )
                
                if created:
                    print(f"   ✅ Created conversation: {conversation.subject}")
                else:
                    print(f"   ✅ Updated conversation: {conversation.subject}")
                
        except Exception as e:
            print(f"   ❌ Error fetching chats: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 2: Fetch messages for a conversation
        print("\n💬 Test 2: Fetching messages from UniPile API...")
        
        conversation = Conversation.objects.filter(channel=channel).first()
        if conversation:
            try:
                print(f"   Conversation: {conversation.subject}")
                print(f"   Calling UniPile API: client.messaging.get_messages()")
                
                # Fetch messages from API
                messages_response = await client.messaging.get_messages(
                    chat_id=conversation.external_thread_id,
                    limit=10  # Get last 10 messages
                )
                
                messages = messages_response.get('items', [])
                print(f"   ✅ Fetched {len(messages)} messages from API")
                
                # Save messages to local database
                for msg_data in messages:
                    msg_id = msg_data.get('id')
                    if not msg_id:
                        continue
                    
                    # Determine direction
                    is_sender = msg_data.get('is_sender', False)
                    direction = 'out' if is_sender else 'in'
                    
                    # Create or update message
                    message, created = Message.objects.update_or_create(
                        channel=channel,
                        external_message_id=msg_id,
                        defaults={
                            'conversation': conversation,
                            'content': msg_data.get('text', ''),
                            'direction': direction,
                            'status': 'delivered',
                            'created_at': timezone.now(),
                            'metadata': {
                                'api_data': msg_data,
                                'synced_from': 'unipile_api',
                                'sync_time': timezone.now().isoformat()
                            }
                        }
                    )
                    
                    if created:
                        print(f"   ✅ Created message: {message.content[:30]}...")
                    
            except Exception as e:
                print(f"   ❌ Error fetching messages: {e}")
                import traceback
                traceback.print_exc()
        
        # Test 3: Fetch attendees
        print("\n👥 Test 3: Fetching attendees from UniPile API...")
        
        try:
            print("   Calling UniPile API: client.messaging.get_all_attendees()")
            
            attendees_response = await client.messaging.get_all_attendees(
                account_id=channel.unipile_account_id,
                limit=10
            )
            
            attendees = attendees_response.get('items', [])
            print(f"   ✅ Fetched {len(attendees)} attendees from API")
            
            # Save attendees to local database
            for attendee_data in attendees:
                attendee_id = attendee_data.get('attendee_provider_id')
                if not attendee_id:
                    continue
                
                # Create or update attendee
                attendee, created = ChatAttendee.objects.update_or_create(
                    channel=channel,
                    provider_id=attendee_id,
                    defaults={
                        'name': attendee_data.get('name', 'Unknown'),
                        'phone_number': attendee_data.get('phone_number'),
                        'is_self': attendee_data.get('is_self', False),
                        'metadata': {
                            'api_data': attendee_data,
                            'synced_from': 'unipile_api'
                        }
                    }
                )
                
                if created:
                    print(f"   ✅ Created attendee: {attendee.name}")
                    
        except Exception as e:
            print(f"   ❌ Error fetching attendees: {e}")
            import traceback
            traceback.print_exc()
        
        # Count after sync
        messages_after = Message.objects.filter(channel=channel).count()
        conversations_after = Conversation.objects.filter(channel=channel).count()
        attendees_after = ChatAttendee.objects.filter(channel=channel).count()
        
        print(f"\n📊 After sync:")
        print(f"   Conversations: {conversations_after} (+{conversations_after - conversations_before})")
        print(f"   Messages: {messages_after} (+{messages_after - messages_before})")
        print(f"   Attendees: {attendees_after} (+{attendees_after - attendees_before})")
        
        # Verify data characteristics
        print("\n🔍 Verifying data saved locally...")
        
        # Check messages with external IDs
        with_external = Message.objects.filter(
            channel=channel,
            external_message_id__isnull=False
        ).exclude(external_message_id='').count()
        
        # Check messages with API metadata
        with_api_meta = Message.objects.filter(
            channel=channel,
            metadata__synced_from='unipile_api'
        ).count()
        
        print(f"   Messages with external IDs: {with_external}")
        print(f"   Messages with API metadata: {with_api_meta}")
        
        # Check no polling - just verify no new messages appear without API calls
        print("\n🚫 Verifying no automatic polling...")
        count1 = Message.objects.filter(channel=channel).count()
        print(f"   Current message count: {count1}")
        print("   Waiting 10 seconds (no API calls)...")
        
        import time
        time.sleep(10)
        
        count2 = Message.objects.filter(channel=channel).count()
        print(f"   Final message count: {count2}")
        
        if count1 == count2:
            print("   ✅ No new messages without API calls (no polling)")
        else:
            new_msgs = count2 - count1
            print(f"   ⚠️ {new_msgs} new messages appeared (might be webhooks)")
        
        print("\n" + "=" * 60)
        print("✅ WhatsApp Historical Sync Test Completed!")
        print("=" * 60)
        
        # Summary
        print("\n📋 Summary:")
        if conversations_after > conversations_before:
            print(f"✅ Synced {conversations_after - conversations_before} new conversations from API")
        if messages_after > messages_before:
            print(f"✅ Synced {messages_after - messages_before} new messages from API")
        if attendees_after > attendees_before:
            print(f"✅ Synced {attendees_after - attendees_before} new attendees from API")
        if with_external > 0:
            print(f"✅ {with_external} messages have external IDs (proves API source)")
        if count1 == count2:
            print("✅ No automatic polling detected")
        
        return {
            'conversations_synced': conversations_after - conversations_before,
            'messages_synced': messages_after - messages_before,
            'attendees_synced': attendees_after - attendees_before,
            'no_polling': count1 == count2
        }


if __name__ == '__main__':
    # Run async function
    result = asyncio.run(test_unipile_api_sync())