#!/usr/bin/env python3
"""
Test WhatsApp message pagination
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from communications.unipile.core.client import UnipileClient
from django.conf import settings
from asgiref.sync import async_to_sync

def test_pagination():
    with schema_context('oneotalent'):
        client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # The chat ID from our test
        chat_id = 'JYoMejM-XWyaAjefOhg5GA'
        
        all_messages = []
        cursor = None
        page = 1
        
        while True:
            print(f'\n📄 Page {page}:')
            
            # Get a batch of messages
            response = async_to_sync(client.messaging.get_all_messages)(
                chat_id=chat_id,
                limit=50,
                cursor=cursor
            )
            
            if not response:
                print('  No response')
                break
                
            items = response.get('items', [])
            print(f'  Messages in this batch: {len(items)}')
            
            if items:
                all_messages.extend(items)
                first_msg = items[0]
                last_msg = items[-1]
                print(f'  First message time: {first_msg.get("timestamp", "unknown")}')
                print(f'  Last message time: {last_msg.get("timestamp", "unknown")}')
            
            # Check for cursor
            cursor = response.get('cursor')
            print(f'  Cursor: {cursor if cursor else "None (no more pages)"}')
            
            if not cursor or not items:
                break
                
            page += 1
            
            if page > 10:  # Safety limit
                print('\n⚠️ Stopping after 10 pages for safety')
                break
        
        print(f'\n✅ Total messages fetched: {len(all_messages)}')
        
        if all_messages:
            # Sort by timestamp and show range
            sorted_msgs = sorted(all_messages, key=lambda x: x.get('timestamp', ''))
            print(f'\n📅 Date range:')
            print(f'  Oldest: {sorted_msgs[0].get("timestamp", "unknown")}')
            print(f'  Newest: {sorted_msgs[-1].get("timestamp", "unknown")}')

if __name__ == '__main__':
    test_pagination()