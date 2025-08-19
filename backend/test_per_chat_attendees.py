#!/usr/bin/env python3
"""
Test the per-chat attendee fetching logic that's implemented in whatsapp_views.py
"""
import os
import sys
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.unipile_sdk import unipile_service


async def test_per_chat_attendees():
    """Test the per-chat attendee fetching approach"""
    print("🧪 Testing per-chat attendee fetching approach...")
    
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    
    try:
        client = unipile_service.get_client()
        
        # Get first few chats
        chats_data = await client.messaging.get_all_chats(
            account_id=account_id,
            limit=3
        )
        
        chats = chats_data.get('items', chats_data.get('chats', []))
        print(f"💬 Testing with {len(chats)} chats")
        
        for i, chat_data in enumerate(chats):
            chat_id = chat_data.get('id')
            provider_id = chat_data.get('provider_id', '')
            is_group = chat_data.get('type', 0) == 1
            
            print(f"\n💬 Chat {i+1}: {chat_id}")
            print(f"  - Provider ID: {provider_id}")
            print(f"  - Is group: {is_group}")
            print(f"  - Raw name: '{chat_data.get('name')}'")
            
            # Test per-chat attendee fetching (like backend does)
            try:
                print(f"  🔍 Fetching per-chat attendees...")
                chat_attendees_data = await client.request.get(f'chats/{chat_id}/attendees')
                chat_attendees_list = chat_attendees_data.get('items', [])
                
                print(f"  📋 Found {len(chat_attendees_list)} attendees")
                
                # Process attendees like backend does
                attendees = []
                for attendee_data in chat_attendees_list:
                    # Extract contact name - same logic as backend
                    contact_name = attendee_data.get('name', '')
                    
                    # If no name, try extracting from provider_id
                    if not contact_name or contact_name == attendee_data.get('phone'):
                        attendee_provider_id = attendee_data.get('provider_id', '')
                        if '@s.whatsapp.net' in attendee_provider_id:
                            phone_part = attendee_provider_id.replace('@s.whatsapp.net', '')
                            contact_name = attendee_data.get('name') or phone_part
                    
                    attendee = {
                        'id': attendee_data.get('id'),
                        'name': contact_name,
                        'phone': attendee_data.get('phone'),
                        'provider_id': attendee_data.get('provider_id'),
                    }
                    attendees.append(attendee)
                    
                    # Show attendee details
                    print(f"    👤 {attendee['provider_id']} → '{attendee['name']}'")
                    
                    # Check if this attendee matches the chat provider_id
                    if attendee_data.get('provider_id') == provider_id:
                        print(f"    ✅ MATCH: This attendee corresponds to chat {provider_id}")
                
                # Apply chat naming logic like backend does
                chat_name = chat_data.get('name')
                
                # For individual chats, prioritize attendee name if different from phone
                if not is_group and attendees:
                    # Find attendee matching chat provider_id
                    matching_attendee = None
                    for att in attendees:
                        if att['provider_id'] == provider_id:
                            matching_attendee = att
                            break
                    
                    if matching_attendee:
                        attendee_name = matching_attendee['name']
                        phone_number = provider_id.replace('@s.whatsapp.net', '') if '@s.whatsapp.net' in provider_id else None
                        
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
                
                print(f"  🏷️ Final chat name: '{chat_name}'")
                
            except Exception as e:
                print(f"  ❌ Failed to fetch per-chat attendees: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_per_chat_attendees())