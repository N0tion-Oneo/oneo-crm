#!/usr/bin/env python
"""
Test actual UniPile API calls with real account data
"""
import os
import sys
import django
import json
import asyncio
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.channels.whatsapp import WhatsAppClient
from communications.models import UserChannelConnection, Channel
from asgiref.sync import async_to_sync


async def test_unipile_api():
    """Test real UniPile API calls"""
    
    from channels.db import database_sync_to_async
    
    @database_sync_to_async
    def get_connection():
        with schema_context('oneotalent'):
            return UserChannelConnection.objects.filter(
                unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA',  # Real UniPile account
                channel_type='whatsapp'
            ).first()
    
    # Get the real WhatsApp connection
    connection = await get_connection()
    
    if not connection:
        print("❌ Real WhatsApp connection not found")
        return
    
    print(f"✅ Found WhatsApp connection: {connection.account_name}")
    print(f"   Account ID: {connection.unipile_account_id}")
    
    # Initialize WhatsApp client
    client = WhatsAppClient()
    
    print("\n📱 Testing UniPile API calls...")
    print("=" * 60)
    
    # 1. Test getting account info
    print("\n1️⃣ Getting account info...")
    try:
        account_info = await client.get_account_info(connection.unipile_account_id)
        if account_info.get('success'):
            print(f"   ✅ Account info retrieved")
            print(f"   Response: {json.dumps(account_info.get('data', {}), indent=2)[:500]}")
        else:
            print(f"   ❌ Failed: {account_info.get('error')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        
    # 2. Test getting chats list
    print("\n2️⃣ Getting chats list...")
    try:
        chats_result = await client.get_chats(
                connection.unipile_account_id,
                limit=5  # Get just 5 chats for testing
        )
        
        if chats_result.get('success'):
            chats = chats_result.get('chats', [])
            print(f"   ✅ Retrieved {len(chats)} chats")
            
            # Show first chat details
            if chats:
                first_chat = chats[0]
                print(f"\n   First chat details:")
                print(f"   - ID: {first_chat.get('id')}")
                print(f"   - Name: {first_chat.get('name')}")
                print(f"   - Type: {first_chat.get('type')}")
                print(f"   - Unread: {first_chat.get('unread_count')}")
                print(f"   - Last message: {first_chat.get('timestamp')}")
                
                # Save chat ID for message testing
                chat_id = first_chat.get('id')
            else:
                print("   ⚠️ No chats found")
                chat_id = None
        else:
            print(f"   ❌ Failed: {chats_result.get('error')}")
            chat_id = None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        chat_id = None
    
    # 3. Test getting messages from a chat (if we have a chat ID)
    if chat_id:
        print(f"\n3️⃣ Getting messages from chat {chat_id}...")
        try:
            messages_result = await client.get_messages(
                connection.unipile_account_id,
                chat_id,
                limit=3  # Get just 3 messages for testing
            )
            
            if messages_result.get('success'):
                messages = messages_result.get('messages', [])
                print(f"   ✅ Retrieved {len(messages)} messages")
                
                # Show first message details
                if messages:
                    first_msg = messages[0]
                    print(f"\n   First message details:")
                    print(f"   - ID: {first_msg.get('id')}")
                    print(f"   - Sender: {first_msg.get('sender_id')}")
                    print(f"   - Text: {first_msg.get('text', '')[:100]}")
                    print(f"   - Timestamp: {first_msg.get('timestamp')}")
            else:
                print(f"   ❌ Failed: {messages_result.get('error')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
    # 4. Test getting attendees/participants
    if chat_id:
        print(f"\n4️⃣ Getting attendees from chat {chat_id}...")
        try:
            attendees_result = await client.get_attendees(
                connection.unipile_account_id,
                chat_id
            )
            
            if attendees_result.get('success'):
                attendees = attendees_result.get('attendees', [])
                print(f"   ✅ Retrieved {len(attendees)} attendees")
                
                # Show attendee details
                for attendee in attendees[:3]:  # Show first 3
                    print(f"\n   Attendee:")
                    print(f"   - ID: {attendee.get('id')}")
                    print(f"   - Name: {attendee.get('name')}")
                    print(f"   - Phone: {attendee.get('phone')}")
            else:
                print(f"   ❌ Failed: {attendees_result.get('error')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
    print("\n" + "=" * 60)
    print("✅ UniPile API testing complete")
    
    # Show response structure expectations
    print("\n📋 Expected Response Structures (from docs):")
    print("""
        Chat Object:
        - id: unique identifier
        - account_id: UniPile account ID
        - provider_id: provider-specific ID
        - name: chat name
        - type: 0 (1-1), 1 (group), 2 (broadcast)
        - timestamp: last activity
        - unread_count: number of unread messages
        - archived: 0/1
        
        Message Object:
        - id: unique identifier  
        - provider_id: provider-specific ID
        - sender_id: attendee ID who sent
        - text: message content
        - attachments: array of media
        - timestamp: when sent
        
        Attendee Object:
        - id: unique identifier
        - provider_id: provider-specific ID (often phone@s.whatsapp.net)
        - name: display name
        - phone: phone number
        - profile_picture_url: avatar URL
        """)


if __name__ == '__main__':
    print("🚀 Testing UniPile API with real account data...")
    print("=" * 60)
    
    # Run the async test
    asyncio.run(test_unipile_api())
    
    print("\n✨ Test complete!")