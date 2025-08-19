#!/usr/bin/env python3
"""
Debug script to check attendees API pagination issues
"""
import os
import sys
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.unipile_sdk import unipile_service


async def debug_attendees():
    """Debug attendees API pagination"""
    print("🧪 Debugging attendees API pagination...")
    
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    
    try:
        client = unipile_service.get_client()
        print(f"✅ Got Unipile client")
        
        # Test 1: First page with limit 5
        print(f"\n📋 Test 1: First page of attendees (limit=5)")
        first_page = await client.messaging.get_all_attendees(
            account_id=account_id,
            limit=5
        )
        print(f"📋 First page response keys: {list(first_page.keys())}")
        print(f"📋 First page structure: {first_page}")
        
        # Check if we have items
        attendees_list = first_page.get('items', first_page.get('attendees', []))
        print(f"📋 Found {len(attendees_list)} attendees in first page")
        
        if attendees_list:
            for i, attendee in enumerate(attendees_list[:3]):  # Show first 3
                print(f"📋 Attendee {i+1}: id={attendee.get('id')}, provider_id={attendee.get('provider_id')}, name={attendee.get('name')}")
        
        # Test 2: Check pagination info
        print(f"\n📋 Test 2: Pagination info")
        cursor = first_page.get('cursor')
        has_more = first_page.get('has_more', False)
        print(f"📋 Has cursor: {bool(cursor)}")
        print(f"📋 Has more: {has_more}")
        print(f"📋 Cursor value: {cursor}")
        
        # Test 3: Try second page if available
        if has_more and cursor:
            print(f"\n📋 Test 3: Second page with cursor")
            second_page = await client.messaging.get_all_attendees(
                account_id=account_id,
                limit=5,
                cursor=cursor
            )
            second_attendees = second_page.get('items', second_page.get('attendees', []))
            print(f"📋 Found {len(second_attendees)} attendees in second page")
            
            if second_attendees:
                for i, attendee in enumerate(second_attendees[:3]):  # Show first 3
                    print(f"📋 Page 2 Attendee {i+1}: id={attendee.get('id')}, provider_id={attendee.get('provider_id')}, name={attendee.get('name')}")
        
        # Test 4: Try without limit to get all
        print(f"\n📋 Test 4: Get all attendees without pagination")
        all_attendees = await client.messaging.get_all_attendees(
            account_id=account_id
        )
        all_list = all_attendees.get('items', all_attendees.get('attendees', []))
        print(f"📋 Found {len(all_list)} total attendees without pagination")
        
        # Test 5: Try raw API call
        print(f"\n📋 Test 5: Raw API call to attendees endpoint")
        raw_response = await client.request.get('chat_attendees', params={
            'account_id': account_id,
            'limit': 10
        })
        print(f"📋 Raw response: {raw_response}")
        
    except Exception as e:
        print(f"❌ Error debugging attendees: {e}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(debug_attendees())