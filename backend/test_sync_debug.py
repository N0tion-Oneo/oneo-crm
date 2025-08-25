#!/usr/bin/env python
"""
Debug script to test WhatsApp sync and identify issues
"""
import os
import sys
import django
import logging
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from django_tenants.utils import schema_context
from communications.models import Channel, Conversation, ChatAttendee, Message
from communications.channels.whatsapp.client import WhatsAppClient
from asgiref.sync import async_to_sync

def test_sync_flow():
    """Test the sync flow step by step"""
    
    # Use oneotalent tenant
    with schema_context('oneotalent'):
        print("\n=== TESTING WHATSAPP SYNC FLOW ===\n")
        
        # 1. Get the real WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        
        print(f"✅ Found channel: {channel.name}")
        print(f"   UniPile Account ID: {channel.unipile_account_id}")
        print(f"   Connection Config: {channel.connection_config}")
        
        # 2. Test API connection
        print("\n--- Testing API Connection ---")
        client = WhatsAppClient()
        
        # 3. Get conversations from API
        print("\n--- Fetching Conversations ---")
        try:
            result = async_to_sync(client.get_conversations)(
                account_id=channel.unipile_account_id,
                limit=5
            )
            
            if result.get('success'):
                conversations = result.get('conversations', [])
                print(f"✅ Retrieved {len(conversations)} conversations")
                
                # Show conversation structure
                if conversations:
                    conv = conversations[0]
                    print(f"\nFirst conversation structure:")
                    print(f"  ID: {conv.get('id')}")
                    print(f"  Name: {conv.get('name')}")
                    print(f"  Type: {conv.get('type')}")
                    print(f"  Participants: {conv.get('participants', [])}")
                    print(f"  Attendees: {conv.get('attendees', [])}")
                    print(f"  Last Message: {conv.get('last_message_at')}")
                    
                    # 4. Try to get messages for first conversation
                    print(f"\n--- Fetching Messages for conversation {conv.get('id')[:20]}... ---")
                    try:
                        # Test with different parameter combinations
                        print("Attempt 1: With account_id and conversation_id")
                        msg_result = async_to_sync(client.get_messages)(
                            account_id=channel.unipile_account_id,
                            conversation_id=conv.get('id'),
                            limit=5
                        )
                        
                        if msg_result.get('success'):
                            messages = msg_result.get('messages', [])
                            print(f"✅ Retrieved {len(messages)} messages")
                            
                            if messages:
                                msg = messages[0]
                                print(f"\nFirst message structure:")
                                print(f"  ID: {msg.get('id')}")
                                print(f"  Text: {msg.get('text', '')[:50]}...")
                                print(f"  Sender: {msg.get('sender')}")
                                print(f"  Sender Attendee ID: {msg.get('sender_attendee_id')}")
                                print(f"  Is Sender: {msg.get('is_sender')}")
                        else:
                            print(f"❌ Failed to get messages: {msg_result.get('error')}")
                    
                    except Exception as e:
                        print(f"❌ Error fetching messages: {e}")
                        
                        # Try without account_id
                        print("\nAttempt 2: Without account_id (chat_id only)")
                        try:
                            # Note: The client.get_messages already handles this internally
                            # but let's test the raw API call
                            from communications.unipile import UnipileClient, UnipileMessagingClient
                            from django.conf import settings
                            
                            dsn = getattr(settings, 'UNIPILE_DSN', 'https://api1.unipile.com:13111')
                            access_token = settings.UNIPILE_API_KEY
                            
                            unipile_client = UnipileClient(dsn=dsn, access_token=access_token)
                            messaging_client = UnipileMessagingClient(unipile_client)
                            
                            # Call directly without account_id
                            msg_result = async_to_sync(messaging_client.get_all_messages)(
                                chat_id=conv.get('id'),
                                limit=5
                            )
                            
                            if 'items' in msg_result:
                                messages = msg_result.get('items', [])
                                print(f"✅ Retrieved {len(messages)} messages (direct API call)")
                            else:
                                print(f"❌ Unexpected response structure: {list(msg_result.keys())}")
                        
                        except Exception as e2:
                            print(f"❌ Direct API call also failed: {e2}")
                    
                    # 5. Check attendees in conversation
                    print(f"\n--- Checking Attendees ---")
                    participants = conv.get('participants', [])
                    attendees = conv.get('attendees', [])
                    
                    print(f"Participants field: {len(participants)} items")
                    print(f"Attendees field: {len(attendees)} items")
                    
                    if participants:
                        print("Participants:")
                        for p in participants[:3]:
                            print(f"  - {p}")
                    
                    if attendees:
                        print("Attendees:")
                        for a in attendees[:3]:
                            print(f"  - {a}")
                    
            else:
                print(f"❌ Failed to get conversations: {result.get('error')}")
        
        except Exception as e:
            print(f"❌ Error during sync test: {e}")
            import traceback
            traceback.print_exc()
        
        # 6. Check database state
        print("\n--- Database State ---")
        conv_count = Conversation.objects.filter(channel=channel).count()
        attendee_count = ChatAttendee.objects.filter(channel=channel).count()
        message_count = Message.objects.filter(channel=channel).count()
        
        print(f"Conversations in DB: {conv_count}")
        print(f"Attendees in DB: {attendee_count}")
        print(f"Messages in DB: {message_count}")

if __name__ == "__main__":
    test_sync_flow()