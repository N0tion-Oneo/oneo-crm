#!/usr/bin/env python3
"""
Debug script to check what the backend is sending for chat names
"""
import os
import sys
import django
import asyncio
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.unipile_sdk import unipile_service


async def debug_chat_response():
    """Debug what the backend is sending for chat names"""
    print("🧪 Debugging chat response data...")
    
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    
    try:
        client = unipile_service.get_client()
        print(f"✅ Got Unipile client")
        
        # Get chats like the backend does
        print(f"\n💬 Test 1: Get chats from Unipile")
        chats_data = await client.messaging.get_all_chats(
            account_id=account_id,
            limit=5
        )
        
        # Show raw chat structure
        chats = chats_data.get('items', chats_data.get('chats', []))
        print(f"💬 Found {len(chats)} chats")
        
        if chats:
            for i, chat in enumerate(chats[:3]):  # Show first 3
                print(f"\n💬 Chat {i+1}:")
                print(f"  - ID: {chat.get('id')}")
                print(f"  - Provider ID: {chat.get('provider_id')}")
                print(f"  - Name: '{chat.get('name')}'")
                print(f"  - Type: {chat.get('type')} (0=individual, 1=group)")
                print(f"  - Unread: {chat.get('unread_count', 0)}")
                
                # Extract phone number like backend does
                provider_id = chat.get('provider_id', '')
                phone_number = None
                is_group = chat.get('type', 0) == 1
                
                if '@s.whatsapp.net' in provider_id:
                    phone_number = provider_id.replace('@s.whatsapp.net', '')
                elif '@g.us' in provider_id:
                    phone_number = provider_id.replace('@g.us', '')
                
                print(f"  - Extracted phone: {phone_number}")
                print(f"  - Is group: {is_group}")
        
        # Get attendees like the backend does
        print(f"\n👥 Test 2: Get attendees from Unipile")
        attendees_data = await client.messaging.get_all_attendees(
            account_id=account_id
        )
        
        all_attendees = attendees_data.get('items', attendees_data.get('attendees', []))
        print(f"👥 Found {len(all_attendees)} total attendees")
        
        # Create mapping like backend does
        attendees_lookup = {}
        for attendee_data in all_attendees:
            provider_id = attendee_data.get('provider_id')
            if provider_id:
                attendees_lookup[provider_id] = {
                    'id': attendee_data.get('id'),
                    'name': attendee_data.get('name'),
                    'phone': attendee_data.get('phone'),
                    'provider_id': provider_id,
                }
        
        print(f"👥 Created lookup for {len(attendees_lookup)} attendees")
        
        # Test specific attendees we know about
        test_ids = [
            '27826840593@s.whatsapp.net',  # Dave S
            '27796968295@s.whatsapp.net',  # Mel Cook
            '27849977040@s.whatsapp.net',  # Vanessa (from logs)
        ]
        
        print(f"\n🔍 Test 3: Check specific attendee mappings")
        for test_id in test_ids:
            if test_id in attendees_lookup:
                attendee = attendees_lookup[test_id]
                print(f"✅ {test_id}: name='{attendee['name']}', id={attendee['id']}")
            else:
                print(f"❌ {test_id}: NOT FOUND in lookup")
        
        # Simulate backend logic for first few chats
        print(f"\n🔧 Test 4: Simulate backend chat name logic")
        for i, chat_data in enumerate(chats[:3]):
            provider_id = chat_data.get('provider_id', '')
            phone_number = None
            is_group = chat_data.get('type', 0) == 1
            
            if '@s.whatsapp.net' in provider_id:
                phone_number = provider_id.replace('@s.whatsapp.net', '')
            elif '@g.us' in provider_id:
                phone_number = provider_id.replace('@g.us', '')
            
            # Backend logic from whatsapp_views.py
            chat_name = chat_data.get('name')
            
            # For individual chats, prioritize attendee name if different from phone
            if not is_group and provider_id in attendees_lookup:
                attendee_name = attendees_lookup[provider_id]['name']
                if attendee_name and attendee_name != phone_number:
                    chat_name = attendee_name
                elif not chat_name or chat_name == phone_number:
                    chat_name = phone_number
            
            # For groups, use group name or create default
            if is_group and not chat_name:
                chat_name = f"Group {chat_data.get('id', 'Unknown')[:8]}"
            
            # Final fallback
            if not chat_name:
                chat_name = 'Unknown Contact'
            
            print(f"\nChat {i+1} ({provider_id}):")
            print(f"  - Raw name: '{chat_data.get('name')}'")
            print(f"  - Final name: '{chat_name}'")
            print(f"  - Is group: {is_group}")
            print(f"  - Found in lookup: {provider_id in attendees_lookup}")
            if provider_id in attendees_lookup:
                print(f"  - Attendee name: '{attendees_lookup[provider_id]['name']}'")
        
    except Exception as e:
        print(f"❌ Error debugging chat response: {e}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(debug_chat_response())