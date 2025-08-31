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
        
        # Fetch a chat to see its structure
        print('\nFetching chats...')
        chat_response = async_to_sync(client.messaging.get_all_chats)(
            account_id=wa_connection.unipile_account_id,
            limit=2
        )
        
        if chat_response and 'items' in chat_response:
            for i, chat in enumerate(chat_response['items'], 1):
                print(f'\n--- Chat {i} ---')
                print(f'Chat ID: {chat.get("id", "N/A")}')
                print(f'Chat name: {chat.get("name", "N/A")}')
                print(f'Attendee IDs: {chat.get("attendee_ids", [])}')
                print(f'Attendees: {chat.get("attendees", [])}')
                
                # Check if attendees have names
                if 'attendees' in chat and chat['attendees']:
                    for attendee in chat['attendees']:
                        print(f'  Attendee: {json.dumps(attendee, indent=4)}')
