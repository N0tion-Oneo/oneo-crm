#!/usr/bin/env python3
"""
Debug script to see all attendee provider IDs
"""
import os
import sys
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.unipile_sdk import unipile_service


async def debug_attendee_ids():
    """Debug attendee provider IDs"""
    print("🧪 Debugging attendee provider IDs...")
    
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    
    try:
        client = unipile_service.get_client()
        
        # Get all attendees
        attendees_data = await client.messaging.get_all_attendees(
            account_id=account_id
        )
        
        all_attendees = attendees_data.get('items', attendees_data.get('attendees', []))
        print(f"👥 Found {len(all_attendees)} total attendees")
        
        # Show all provider IDs
        print(f"\n📋 All attendee provider IDs:")
        for i, attendee in enumerate(all_attendees):
            provider_id = attendee.get('provider_id')
            name = attendee.get('name')
            print(f"{i+1:2d}. {provider_id} → '{name}'")
        
        # Also get chats to see their provider IDs
        print(f"\n💬 Chat provider IDs (first 10):")
        chats_data = await client.messaging.get_all_chats(
            account_id=account_id,
            limit=10
        )
        
        chats = chats_data.get('items', chats_data.get('chats', []))
        for i, chat in enumerate(chats):
            provider_id = chat.get('provider_id')
            name = chat.get('name')
            chat_type = "group" if chat.get('type', 0) == 1 else "individual"
            print(f"{i+1:2d}. {provider_id} ({chat_type}) → '{name}'")
        
        # Check if any chat provider IDs match attendee provider IDs
        print(f"\n🔍 Cross-checking chat vs attendee provider IDs:")
        attendee_ids = {att.get('provider_id') for att in all_attendees}
        chat_ids = {chat.get('provider_id') for chat in chats if chat.get('type', 0) == 0}  # Only individual chats
        
        matches = chat_ids.intersection(attendee_ids)
        missing = chat_ids - attendee_ids
        
        print(f"✅ Matching IDs: {len(matches)}")
        print(f"❌ Missing from attendees: {len(missing)}")
        
        if missing:
            print(f"\n❌ Chat provider IDs NOT in attendees:")
            for missing_id in missing:
                print(f"  - {missing_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(debug_attendee_ids())