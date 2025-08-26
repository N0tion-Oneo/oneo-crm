#!/usr/bin/env python
"""
Test UniPile API with before/after date filters for Vanessa
"""
import os
import sys
import django
import asyncio
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from communications.unipile import UnipileClient, UnipileMessagingClient

async def test_date_filters():
    """Test with before/after filters to get older messages"""
    
    print("\n" + "="*80)
    print("TESTING DATE FILTERS FOR VANESSA'S MESSAGES")
    print("="*80)
    
    # Initialize UniPile client
    dsn = getattr(settings, 'UNIPILE_DSN', '')
    access_token = getattr(settings, 'UNIPILE_API_KEY', '')
    
    client = UnipileClient(dsn=dsn, access_token=access_token)
    messaging = UnipileMessagingClient(client)
    
    chat_id = "1T1s9uwKX3yXDdHr9p9uWQ"
    
    # First, let's get the date of the oldest message we have (August 1, 2025)
    oldest_date = "2025-08-01T11:57:52.000Z"
    
    print(f"\n📱 Testing chat: {chat_id}")
    print(f"   Current oldest message: {oldest_date}")
    
    # Test 1: Get messages before the oldest date we have
    print(f"\n🔍 Test 1: Messages before {oldest_date}")
    try:
        # Make direct API call with before parameter
        endpoint = f"chats/{chat_id}/messages"
        params = {
            'before': oldest_date,
            'limit': 200
        }
        
        response = await client._make_request('GET', endpoint, params=params)
        
        if response.get('items'):
            messages = response['items']
            print(f"   ✅ Got {len(messages)} older messages!")
            first = messages[0]
            last = messages[-1]
            print(f"   Date range: {first.get('timestamp', 'N/A')[:19]} to {last.get('timestamp', 'N/A')[:19]}")
            
            # Check for cursor
            if response.get('cursor'):
                print(f"   Cursor present: Can get even more messages")
            else:
                print(f"   No cursor: This is all available history")
        else:
            print(f"   ❌ No messages returned before {oldest_date}")
            
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Get messages in chunks going backwards
    print(f"\n🔍 Test 2: Paginate backwards from oldest known message")
    all_messages = []
    current_before = oldest_date
    
    for i in range(5):  # Try 5 iterations
        try:
            endpoint = f"chats/{chat_id}/messages"
            params = {
                'before': current_before,
                'limit': 50
            }
            
            response = await client._make_request('GET', endpoint, params=params)
            
            if not response.get('items'):
                print(f"   Iteration {i+1}: No more messages")
                break
            
            messages = response['items']
            all_messages.extend(messages)
            print(f"   Iteration {i+1}: Got {len(messages)} messages (total: {len(all_messages)})")
            
            # Update before date to the oldest message we got
            if messages:
                current_before = messages[-1].get('timestamp', current_before)
                print(f"      New before date: {current_before[:19]}")
            
            if not response.get('cursor'):
                print(f"   No cursor - reached the end")
                break
                
        except Exception as e:
            print(f"   Iteration {i+1} error: {e}")
            break
    
    if all_messages:
        print(f"\n   📊 Total older messages found: {len(all_messages)}")
        first = all_messages[0]
        last = all_messages[-1]
        print(f"   Date range: {first.get('timestamp', 'N/A')[:19]} to {last.get('timestamp', 'N/A')[:19]}")
    
    # Test 3: Try different date ranges
    print(f"\n🔍 Test 3: Test specific date ranges")
    
    # July 2025
    print("\n   Testing July 2025:")
    try:
        endpoint = f"chats/{chat_id}/messages"
        params = {
            'after': "2025-07-01T00:00:00.000Z",
            'before': "2025-07-31T23:59:59.999Z",
            'limit': 200
        }
        
        response = await client._make_request('GET', endpoint, params=params)
        
        if response.get('items'):
            print(f"      ✅ Found {len(response['items'])} messages in July 2025")
        else:
            print(f"      No messages in July 2025")
    except Exception as e:
        print(f"      Error: {e}")
    
    # June 2025
    print("\n   Testing June 2025:")
    try:
        endpoint = f"chats/{chat_id}/messages"
        params = {
            'after': "2025-06-01T00:00:00.000Z",
            'before': "2025-06-30T23:59:59.999Z",
            'limit': 200
        }
        
        response = await client._make_request('GET', endpoint, params=params)
        
        if response.get('items'):
            print(f"      ✅ Found {len(response['items'])} messages in June 2025")
        else:
            print(f"      No messages in June 2025")
    except Exception as e:
        print(f"      Error: {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == '__main__':
    asyncio.run(test_date_filters())