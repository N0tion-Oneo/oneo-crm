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
        
        # Fetch one chat and get a message to see all fields
        chat_response = async_to_sync(client.messaging.get_all_chats)(
            account_id=wa_connection.unipile_account_id,
            limit=1
        )
        
        if chat_response and 'items' in chat_response and chat_response['items']:
            chat = chat_response['items'][0]
            print(f'\nChat ID: {chat.get("id", "N/A")}')
            
            # Get one message to see all fields
            msg_response = async_to_sync(client.messaging.get_all_messages)(
                account_id=wa_connection.unipile_account_id,
                chat_id=chat['id'],
                limit=1
            )
            
            if msg_response and 'items' in msg_response:
                print(f'\nMessage fields:')
                msg = msg_response['items'][0]
                print(json.dumps(msg, indent=2, default=str))
