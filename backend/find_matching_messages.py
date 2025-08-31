#!/usr/bin/env python
import os
import sys
import django
from asgiref.sync import async_to_sync

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.conf import settings
from communications.models import UserChannelConnection
from communications.unipile.core.client import UnipileClient
from django_tenants.utils import schema_context

with schema_context('oneotalent'):
    wa_connection = UserChannelConnection.objects.filter(
        channel_type='whatsapp',
        is_active=True
    ).first()
    
    if wa_connection:
        client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # First get an attendee with a name
        response = async_to_sync(client.messaging.get_all_attendees)(
            account_id=wa_connection.unipile_account_id,
            limit=10
        )
        
        attendees_with_names = []
        if response and 'items' in response:
            for attendee in response['items']:
                name = attendee.get('name', '')
                provider_id = attendee.get('provider_id', '')
                if name and name != provider_id:  # Has a real name
                    phone = provider_id.replace('@s.whatsapp.net', '') if '@s.whatsapp.net' in provider_id else ''
                    if phone:
                        attendees_with_names.append({
                            'name': name,
                            'phone': phone,
                            'provider_id': provider_id,
                            'attendee_id': attendee.get('id', '')
                        })
        
        print(f'Found {len(attendees_with_names)} attendees with names')
        
        if attendees_with_names:
            # Try to find messages from these attendees
            for attendee in attendees_with_names[:3]:
                print(f'\\nChecking for messages from {attendee["name"]} ({attendee["phone"]})')
                
                # Try to find a chat with this attendee
                chat_response = async_to_sync(client.messaging.get_all_chats)(
                    account_id=wa_connection.unipile_account_id,
                    attendee_id=attendee['attendee_id'],
                    limit=1
                )
                
                if chat_response and 'items' in chat_response and chat_response['items']:
                    chat = chat_response['items'][0]
                    print(f'  Found chat: {chat["id"]}')
                    
                    # Get messages from this chat
                    msg_response = async_to_sync(client.messaging.get_all_messages)(
                        account_id=wa_connection.unipile_account_id,
                        chat_id=chat['id'],
                        limit=2
                    )
                    
                    if msg_response and 'items' in msg_response:
                        for msg in msg_response['items']:
                            sender_id = msg.get('sender_id', '')
                            is_sender = msg.get('is_sender', 0)
                            print(f'    Message: sender_id={sender_id}, is_sender={is_sender}')
                else:
                    print(f'  No chats found')
