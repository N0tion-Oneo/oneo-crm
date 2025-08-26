#!/usr/bin/env python
"""
Compare API responses between Vanessa and Grant's conversations
"""
import os
import sys
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from communications.unipile import UnipileClient, UnipileMessagingClient

async def compare_conversations():
    """Compare API responses for different conversations"""
    
    print("\n" + "="*80)
    print("COMPARING CONVERSATIONS: VANESSA vs GRANT")
    print("="*80)
    
    # Initialize UniPile client
    dsn = getattr(settings, 'UNIPILE_DSN', '')
    access_token = getattr(settings, 'UNIPILE_API_KEY', '')
    
    client = UnipileClient(dsn=dsn, access_token=access_token)
    messaging = UnipileMessagingClient(client)
    
    conversations = [
        {"name": "Vanessa", "id": "1T1s9uwKX3yXDdHr9p9uWQ", "expected": 305},
        {"name": "Grant Kavnat", "id": "Z6sXmguuXPSUtXQGRrZndA", "expected": 727},
        {"name": "Robbie Cowan", "id": "G591JeOHXF2j95hwHx7lSA", "expected": 952}
    ]
    
    for conv in conversations:
        print(f"\n📱 Testing {conv['name']} (expected {conv['expected']} messages)")
        print(f"   Chat ID: {conv['id']}")
        
        # Count total messages available via pagination
        total_messages = 0
        cursor = None
        api_calls = 0
        oldest_date = None
        newest_date = None
        
        while api_calls < 10:  # Safety limit
            api_calls += 1
            
            try:
                result = await messaging.get_all_messages(
                    chat_id=conv['id'],
                    limit=200,
                    cursor=cursor
                )
                
                messages = result.get('items', [])
                if not messages:
                    break
                
                total_messages += len(messages)
                
                # Track dates
                if not newest_date and messages:
                    newest_date = messages[0].get('timestamp', '')[:19]
                if messages:
                    oldest_date = messages[-1].get('timestamp', '')[:19]
                
                print(f"   API call {api_calls}: Got {len(messages)} messages (total: {total_messages})")
                
                # Check for more
                cursor = result.get('cursor')
                if not cursor:
                    print(f"   No more messages available (API returned no cursor)")
                    break
                    
            except Exception as e:
                print(f"   Error: {e}")
                break
        
        print(f"\n   📊 Results for {conv['name']}:")
        print(f"      Total messages from API: {total_messages}")
        print(f"      Expected in DB: {conv['expected']}")
        print(f"      Date range: {newest_date} to {oldest_date}")
        
        if total_messages != conv['expected']:
            print(f"      ⚠️ MISMATCH: API has {total_messages} but DB has {conv['expected']}")
    
    # Now test if we can get older messages for Vanessa using different approaches
    print("\n" + "="*80)
    print("TESTING ALTERNATIVE APPROACHES FOR VANESSA")
    print("="*80)
    
    vanessa_id = "1T1s9uwKX3yXDdHr9p9uWQ"
    
    # Test 1: Try without any parameters
    print("\n🔍 Test 1: Raw API call with no parameters")
    try:
        endpoint = f"chats/{vanessa_id}/messages"
        response = await client._make_request('GET', endpoint)
        
        items = response.get('items', [])
        print(f"   Got {len(items)} messages")
        if items:
            print(f"   Date range: {items[0].get('timestamp', '')[:19]} to {items[-1].get('timestamp', '')[:19]}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Try with account_id
    print("\n🔍 Test 2: Include account_id in request")
    try:
        result = await messaging.get_all_messages(
            account_id="mp9Gis3IRtuh9V5oSxZdSA",
            chat_id=vanessa_id,
            limit=200
        )
        print(f"   Got {len(result.get('items', []))} messages")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == '__main__':
    asyncio.run(compare_conversations())