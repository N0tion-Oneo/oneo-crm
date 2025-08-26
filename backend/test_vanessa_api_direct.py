#!/usr/bin/env python
"""
Test UniPile API directly to investigate Vanessa's message limit
"""
import os
import sys
import django
import asyncio
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from communications.unipile import UnipileClient, UnipileMessagingClient

async def test_vanessa_api():
    """Test different API parameters to get more messages"""
    
    print("\n" + "="*80)
    print("UNIPILE API DIRECT TEST - VANESSA'S MESSAGES")
    print("="*80)
    
    # Initialize UniPile client
    dsn = getattr(settings, 'UNIPILE_DSN', '')
    access_token = getattr(settings, 'UNIPILE_API_KEY', '')
    
    client = UnipileClient(dsn=dsn, access_token=access_token)
    messaging = UnipileMessagingClient(client)
    
    chat_id = "1T1s9uwKX3yXDdHr9p9uWQ"
    
    print(f"\n📱 Testing chat: {chat_id}")
    
    # Test 1: Get messages without any limit
    print("\n🔍 Test 1: No limit specified")
    try:
        result = await messaging.get_all_messages(
            chat_id=chat_id
        )
        print(f"   Result: Got {len(result.get('items', []))} messages")
        print(f"   Cursor: {result.get('cursor') is not None}")
        if result.get('items'):
            first = result['items'][0]
            last = result['items'][-1]
            print(f"   Date range: {first.get('timestamp', 'N/A')[:19]} to {last.get('timestamp', 'N/A')[:19]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Try with a very high limit
    print("\n🔍 Test 2: High limit (5000)")
    try:
        result = await messaging.get_all_messages(
            chat_id=chat_id,
            limit=5000
        )
        print(f"   Result: Got {len(result.get('items', []))} messages")
        print(f"   Cursor: {result.get('cursor') is not None}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Try pagination manually with small batches
    print("\n🔍 Test 3: Manual pagination (50 per batch)")
    total_messages = []
    cursor = None
    batch_count = 0
    
    while batch_count < 20:  # Limit to 20 batches for safety
        batch_count += 1
        try:
            result = await messaging.get_all_messages(
                chat_id=chat_id,
                limit=50,
                cursor=cursor
            )
            
            messages = result.get('items', [])
            if not messages:
                print(f"   Batch {batch_count}: No messages, stopping")
                break
                
            total_messages.extend(messages)
            print(f"   Batch {batch_count}: Got {len(messages)} messages (total: {len(total_messages)})")
            
            # Check for cursor
            cursor = result.get('cursor')
            if not cursor:
                print(f"   No cursor returned, stopping at {len(total_messages)} messages")
                break
                
        except Exception as e:
            print(f"   Batch {batch_count} error: {e}")
            break
    
    if total_messages:
        first = total_messages[0]
        last = total_messages[-1]
        print(f"\n   📊 Total collected: {len(total_messages)} messages")
        print(f"   Date range: {first.get('timestamp', 'N/A')[:19]} to {last.get('timestamp', 'N/A')[:19]}")
    
    # Test 4: Try with date parameters to go further back
    print("\n🔍 Test 4: With date range (since 2024-01-01)")
    try:
        result = await messaging.get_all_messages(
            chat_id=chat_id,
            since="2024-01-01T00:00:00Z",
            limit=1000
        )
        print(f"   Result: Got {len(result.get('items', []))} messages")
        if result.get('items'):
            first = result['items'][0]
            last = result['items'][-1]
            print(f"   Date range: {first.get('timestamp', 'N/A')[:19]} to {last.get('timestamp', 'N/A')[:19]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Check what cursor contains
    print("\n🔍 Test 5: Analyze cursor content")
    try:
        result = await messaging.get_all_messages(
            chat_id=chat_id,
            limit=10
        )
        cursor = result.get('cursor')
        if cursor:
            # Try to decode base64 cursor
            import base64
            try:
                decoded = base64.b64decode(cursor)
                print(f"   Decoded cursor: {decoded.decode('utf-8', errors='ignore')}")
            except:
                print(f"   Raw cursor: {cursor[:100]}...")
        else:
            print("   No cursor returned")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == '__main__':
    asyncio.run(test_vanessa_api())