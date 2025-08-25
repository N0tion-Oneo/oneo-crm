#!/usr/bin/env python
"""
Debug the exact API call being made for messages
"""
import os
import sys
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from django_tenants.utils import schema_context
from communications.models import Channel, Conversation
from communications.channels.whatsapp.client import WhatsAppClient
from communications.unipile import UnipileClient, UnipileMessagingClient
from django.conf import settings
from asgiref.sync import async_to_sync

def test_api_calls():
    """Test the exact API calls being made"""
    
    with schema_context('oneotalent'):
        print("\n=== API CALL DEBUG TEST ===\n")
        
        # Get channel and conversation
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No channel found")
            return
        
        conversations = Conversation.objects.filter(channel=channel)[:1]
        if not conversations:
            print("❌ No conversations found")
            return
        
        conv = conversations[0]
        print(f"Testing with conversation: {conv.external_thread_id}")
        
        # Test 1: Direct UniPile API call
        print("\n--- Test 1: Direct UniPile API (chat_id only) ---")
        try:
            dsn = getattr(settings, 'UNIPILE_DSN', 'https://api1.unipile.com:13111')
            access_token = settings.UNIPILE_API_KEY
            
            unipile_client = UnipileClient(dsn=dsn, access_token=access_token)
            messaging_client = UnipileMessagingClient(unipile_client)
            
            # Call with ONLY chat_id (no account_id)
            result = async_to_sync(messaging_client.get_all_messages)(
                chat_id=conv.external_thread_id,
                limit=5
            )
            
            if 'items' in result:
                print(f"✅ SUCCESS: Got {len(result.get('items', []))} messages")
            else:
                print(f"❌ FAILED: {result}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        # Test 2: WhatsAppClient with empty account_id
        print("\n--- Test 2: WhatsAppClient with empty account_id ---")
        try:
            client = WhatsAppClient()
            
            # This mimics what the sync service does
            result = async_to_sync(client.get_messages)(
                account_id='',  # Empty string
                conversation_id=conv.external_thread_id,
                limit=5
            )
            
            if result.get('success'):
                print(f"✅ SUCCESS: Got {len(result.get('messages', []))} messages")
            else:
                print(f"❌ FAILED: {result}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        # Test 3: WhatsAppClient with None account_id
        print("\n--- Test 3: WhatsAppClient with None account_id ---")
        try:
            client = WhatsAppClient()
            
            result = async_to_sync(client.get_messages)(
                account_id=None,  # None
                conversation_id=conv.external_thread_id,
                limit=5
            )
            
            if result.get('success'):
                print(f"✅ SUCCESS: Got {len(result.get('messages', []))} messages")
            else:
                print(f"❌ FAILED: {result}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        # Test 4: WhatsAppClient with actual account_id
        print("\n--- Test 4: WhatsAppClient with real account_id ---")
        try:
            client = WhatsAppClient()
            
            result = async_to_sync(client.get_messages)(
                account_id='mp9Gis3IRtuh9V5oSxZdSA',  # Real account ID
                conversation_id=conv.external_thread_id,
                limit=5
            )
            
            if result.get('success'):
                print(f"✅ SUCCESS: Got {len(result.get('messages', []))} messages")
            else:
                print(f"❌ FAILED: {result}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_api_calls()