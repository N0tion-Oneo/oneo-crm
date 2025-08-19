#!/usr/bin/env python3
"""
Debug pagination from Unipile API
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


async def debug_pagination():
    """Debug pagination from Unipile API"""
    print("🧪 Debugging pagination from Unipile API...")
    
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    
    try:
        client = unipile_service.get_client()
        
        # First request with limit 10
        print(f"\n🔍 First request (limit=10)...")
        chats_data = await client.messaging.get_all_chats(
            account_id=account_id,
            limit=10
        )
        
        print(f"Raw response keys: {list(chats_data.keys())}")
        chats = chats_data.get('items', chats_data.get('chats', []))
        cursor = chats_data.get('cursor')
        has_more = chats_data.get('has_more', False)
        
        print(f"Chats returned: {len(chats)}")
        print(f"Cursor: {cursor}")
        print(f"Has more: {has_more}")
        
        # If we have a cursor, try the next page
        if cursor:
            print(f"\n🔍 Second request (limit=10, cursor={cursor[:20]}...)...")
            chats_data_2 = await client.messaging.get_all_chats(
                account_id=account_id,
                limit=10,
                cursor=cursor
            )
            
            chats_2 = chats_data_2.get('items', chats_data_2.get('chats', []))
            cursor_2 = chats_data_2.get('cursor')
            has_more_2 = chats_data_2.get('has_more', False)
            
            print(f"Page 2 chats returned: {len(chats_2)}")
            print(f"Page 2 cursor: {cursor_2}")
            print(f"Page 2 has more: {has_more_2}")
            
            # Show first few chat IDs to confirm they're different
            print(f"\nPage 1 chat IDs: {[chat.get('id')[:8] for chat in chats[:3]]}")
            print(f"Page 2 chat IDs: {[chat.get('id')[:8] for chat in chats_2[:3]]}")
            
        else:
            print(f"❌ No cursor returned from first request")
        
        # Let's also check how many total chats there are
        print(f"\n🔍 Checking total chat count (no limit)...")
        all_chats_data = await client.messaging.get_all_chats(
            account_id=account_id,
            limit=1000  # Large limit to get everything
        )
        
        all_chats = all_chats_data.get('items', all_chats_data.get('chats', []))
        print(f"Total chats available: {len(all_chats)}")
        
        # Show detailed response structure
        print(f"\n📋 Full response structure:")
        safe_response = {k: v for k, v in chats_data.items() if k not in ['items']}
        safe_response['items_count'] = len(chats)
        print(json.dumps(safe_response, indent=2, default=str))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(debug_pagination())