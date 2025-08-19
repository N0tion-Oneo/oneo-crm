#!/usr/bin/env python3
"""
Debug script to check if we can get chat-specific attendees
"""
import os
import sys
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.unipile_sdk import unipile_service


async def debug_chat_attendees():
    """Test different approaches to get chat attendees"""
    print("🧪 Testing different approaches to get chat attendees...")
    
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    
    try:
        client = unipile_service.get_client()
        
        # Get a few chats first
        chats_data = await client.messaging.get_all_chats(
            account_id=account_id,
            limit=3
        )
        
        chats = chats_data.get('items', chats_data.get('chats', []))
        print(f"💬 Testing with {len(chats)} chats")
        
        for i, chat in enumerate(chats):
            chat_id = chat.get('id')
            provider_id = chat.get('provider_id')
            is_group = chat.get('type', 0) == 1
            
            print(f"\n💬 Chat {i+1}: {chat_id}")
            print(f"  - Provider ID: {provider_id}")
            print(f"  - Is group: {is_group}")
            print(f"  - Name: {chat.get('name')}")
            
            # Try method 1: Get chat details
            try:
                print(f"  📋 Method 1: Get chat details")
                chat_details = await client.request.get(f'chats/{chat_id}')
                print(f"    ✅ Got chat details: {len(str(chat_details))} chars")
                
                # Check if chat details have attendee info
                if 'attendees' in chat_details:
                    attendees = chat_details['attendees']
                    print(f"    👥 Found {len(attendees)} attendees in chat details")
                    for j, att in enumerate(attendees[:2]):  # Show first 2
                        print(f"      {j+1}. {att.get('provider_id')} → {att.get('name')}")
                else:
                    print(f"    ❌ No attendees in chat details")
                    
            except Exception as e:
                print(f"    ❌ Failed to get chat details: {e}")
            
            # Try method 2: Get chat attendees endpoint
            try:
                print(f"  📋 Method 2: Get chat attendees endpoint")
                chat_attendees = await client.request.get(f'chats/{chat_id}/attendees')
                print(f"    ✅ Got chat attendees: {chat_attendees}")
            except Exception as e:
                print(f"    ❌ Failed to get chat attendees: {e}")
            
            # Try method 3: Raw API call with provider_id filter
            if not is_group:  # Only try for individual chats
                try:
                    print(f"  📋 Method 3: Get attendees filtered by provider_id")
                    filtered_attendees = await client.request.get('chat_attendees', params={
                        'account_id': account_id,
                        'provider_id': provider_id
                    })
                    print(f"    ✅ Got filtered attendees: {filtered_attendees}")
                except Exception as e:
                    print(f"    ❌ Failed to get filtered attendees: {e}")
            
            # Try method 4: Search in all attendees for phone number
            phone_number = None
            if '@s.whatsapp.net' in provider_id:
                phone_number = provider_id.replace('@s.whatsapp.net', '')
                
                print(f"  📋 Method 4: Search all attendees for phone {phone_number}")
                try:
                    all_attendees_data = await client.messaging.get_all_attendees(
                        account_id=account_id
                    )
                    all_attendees = all_attendees_data.get('items', [])
                    
                    # Search for matching phone number or name
                    matches = []
                    for att in all_attendees:
                        att_phone = att.get('phone', '')
                        att_provider_id = att.get('provider_id', '')
                        att_name = att.get('name', '')
                        
                        if (phone_number in att_phone or 
                            phone_number in att_provider_id or
                            phone_number in att_name):
                            matches.append(att)
                    
                    print(f"    🔍 Found {len(matches)} potential matches for phone {phone_number}")
                    for match in matches:
                        print(f"      - {match.get('provider_id')} → {match.get('name')} (phone: {match.get('phone')})")
                        
                except Exception as e:
                    print(f"    ❌ Failed to search attendees: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(debug_chat_attendees())