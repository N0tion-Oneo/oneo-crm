#!/usr/bin/env python3
"""
Test script to directly check Unipile API for messages
"""
import os
import sys
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.unipile_sdk import unipile_service


async def test_unipile_messages():
    """Test Unipile API for messages in the specific chat"""
    print("🧪 Testing Unipile API directly...")
    
    # The chat ID from the frontend logs
    chat_id = "1T1s9uwKX3yXDdHr9p9uWQ"
    
    try:
        client = unipile_service.get_client()
        print(f"✅ Got Unipile client")
        
        # Test 1: Get messages for specific chat
        print(f"\n📨 Test 1: Getting messages for chat {chat_id}")
        messages_response = await client.messaging.get_all_messages(
            chat_id=chat_id,
            limit=10
        )
        print(f"📨 Messages response: {messages_response}")
        
        if 'messages' in messages_response:
            messages = messages_response['messages']
            print(f"📨 Found {len(messages)} messages")
            
            if messages:
                for i, msg in enumerate(messages[:3]):  # Show first 3 messages
                    print(f"📨 Message {i+1}: {msg.get('text', 'No text')[:50]}...")
            else:
                print("📨 No messages returned from Unipile API")
        else:
            print(f"📨 No 'messages' key in response: {list(messages_response.keys())}")
        
        # Test 2: Try getting all messages for the account
        print(f"\n📨 Test 2: Getting all messages for account mp9Gis3IRtuh9V5oSxZdSA")
        all_messages_response = await client.messaging.get_all_messages(
            account_id="mp9Gis3IRtuh9V5oSxZdSA",
            limit=10
        )
        print(f"📨 All messages response: {all_messages_response}")
        
        # Test 3: Check attendees API response format
        print(f"\n👥 Test 3: Check attendees API format")
        attendees_response = await client.messaging.get_all_attendees(
            account_id="mp9Gis3IRtuh9V5oSxZdSA",
            limit=5
        )
        print(f"👥 Attendees response keys: {list(attendees_response.keys())}")
        print(f"👥 Attendees response: {attendees_response}")
        
        # Test 4: Try raw API call to attendees endpoint
        print(f"\n👥 Test 4: Raw API call to attendees endpoint")
        raw_attendees = await client.request.get('chat_attendees', params={
            'account_id': 'mp9Gis3IRtuh9V5oSxZdSA',
            'limit': 5
        })
        print(f"👥 Raw attendees: {raw_attendees}")
        
        # Test 5: Check specific chat details for group
        print(f"\n👥 Test 5: Get group chat details")
        group_chat_id = "d3spoDQ-WK6qaXUz0RbLNw"  # Palatino group from chats API
        try:
            group_details = await client.request.get(f'chats/{group_chat_id}')
            print(f"👥 Group details: {group_details}")
        except Exception as e:
            print(f"👥 Error getting group details: {e}")
        
        # Test 6: Try direct chats API call to see raw structure  
        print(f"\n💬 Test 6: Raw chats API call")
        try:
            raw_chats = await client.request.get('chats', params={
                'account_id': 'mp9Gis3IRtuh9V5oSxZdSA',
                'limit': 5
            })
            print(f"💬 Raw chats keys: {list(raw_chats.keys())}")
            if 'items' in raw_chats:
                for i, chat in enumerate(raw_chats['items'][:2]):
                    print(f"💬 Chat {i+1}: {chat}")
        except Exception as e:
            print(f"💬 Error getting raw chats: {e}")
        
    except Exception as e:
        print(f"❌ Error testing Unipile API: {e}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_unipile_messages())