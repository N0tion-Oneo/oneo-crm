#!/usr/bin/env python
import os
import sys
import django
import json
from asgiref.sync import async_to_sync

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.conf import settings
from communications.models import UserChannelConnection
from communications.unipile.core.client import UnipileClient
from django_tenants.utils import schema_context

# Use oneotalent schema where we have data
with schema_context('oneotalent'):
    # Get WhatsApp connection
    wa_connection = UserChannelConnection.objects.filter(
        channel_type='whatsapp',
        is_active=True
    ).first()
    
    if wa_connection:
        print(f'Found WhatsApp connection: {wa_connection.unipile_account_id}')
        
        # Initialize UniPile client
        client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # Fetch attendees to see the full structure
        print('\nFetching attendees...')
        response = async_to_sync(client.messaging.get_all_attendees)(
            account_id=wa_connection.unipile_account_id,
            limit=3  # Just get a few to see the structure
        )
        
        if response and 'items' in response:
            print(f'\nGot {len(response["items"])} attendees')
            for i, attendee in enumerate(response['items'], 1):
                print(f'\n--- Attendee {i} ---')
                print(f'id: {attendee.get("id", "N/A")}')
                print(f'provider_id: {attendee.get("provider_id", "N/A")}')
                print(f'name: {attendee.get("name", "N/A")}')
                
                # Check if we've seen this ID in messages
                # The "id" field from attendees should match "sender_attendee_id" in messages
                print(f'  -> This is the ID that should appear as sender_attendee_id in messages')
                
                if i >= 2:  # Only check first 2
                    break
        
        # Now fetch some chats directly to see what sender_attendee_id we get
        print('\n\nFetching chats directly...')
        chat_response = async_to_sync(client.messaging.get_all_chats)(
            account_id=wa_connection.unipile_account_id,
            limit=2
        )
        
        if chat_response and 'items' in chat_response:
            for chat in chat_response['items']:
                print(f'\nChat ID: {chat.get("id", "N/A")}')
                print(f'Attendee IDs: {chat.get("attendee_ids", [])}')
                
                # Get messages for this chat
                msg_response = async_to_sync(client.messaging.get_all_messages)(
                    account_id=wa_connection.unipile_account_id,
                    chat_id=chat['id'],
                    limit=2
                )
                
                if msg_response and 'items' in msg_response:
                    print(f'  Messages:')
                    for msg in msg_response['items']:
                        print(f'    - sender_attendee_id: {msg.get("sender_attendee_id", "N/A")}')
                        print(f'      is_sender: {msg.get("is_sender", "N/A")}')
