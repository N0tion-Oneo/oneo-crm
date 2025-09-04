#!/usr/bin/env python
"""
Test the message fetcher for LinkedIn
"""
import os
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Enable detailed logging
logging.basicConfig(level=logging.INFO)

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection
from communications.record_communications.unipile_integration import AttendeeResolver, MessageFetcher
from communications.unipile.core.client import UnipileClient
from django.conf import settings

# Use oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    print("🏢 Testing in tenant: oneotalent")
    
    # Get LinkedIn connection
    linkedin_conn = UserChannelConnection.objects.filter(
        channel_type='linkedin'
    ).first()
    
    if linkedin_conn:
        print(f"\n📡 LinkedIn connection: {linkedin_conn.account_name}")
        print(f"   UniPile Account ID: {linkedin_conn.unipile_account_id}")
        
        # Initialize UniPile client
        client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # Initialize attendee resolver
        resolver = AttendeeResolver(client)
        
        # Test identifiers
        identifiers = {
            'linkedin': ['robbiecowan']
        }
        
        print(f"\n🔍 Step 1: Resolve attendees for: {identifiers}")
        
        # Resolve attendees
        attendee_map = resolver.resolve_messaging_attendees(
            identifiers=identifiers,
            channel_type='linkedin',
            account_id=linkedin_conn.unipile_account_id
        )
        
        if attendee_map:
            print(f"   ✅ Found {len(attendee_map)} attendees")
            for provider_id, info in attendee_map.items():
                print(f"      Provider ID: {provider_id[:30]}...")
                
            print(f"\n🔍 Step 2: Fetch messages for attendees")
            
            # Initialize message fetcher
            fetcher = MessageFetcher(client)
            
            # Fetch messages
            message_data = fetcher.fetch_messages_for_attendees(
                attendee_map=attendee_map,
                account_id=linkedin_conn.unipile_account_id,
                channel_type='linkedin',
                days_back=0,  # 0 = no limit
                max_messages_per_attendee=100
            )
            
            if message_data:
                print(f"   ✅ Found messages for {len(message_data)} attendees")
                for attendee_id, data in message_data.items():
                    print(f"\n   Attendee: {attendee_id[:30]}...")
                    conversations = data.get('conversations', [])
                    print(f"   Conversations: {len(conversations)}")
                    
                    total_messages = 0
                    for conv in conversations[:3]:  # Show first 3 conversations
                        messages = conv.get('messages', [])
                        total_messages += len(messages)
                        subject = conv.get('chat_data', {}).get('subject', 'No subject')
                        print(f"      - {subject[:50]}... ({len(messages)} messages)")
                    
                    print(f"   Total messages: {total_messages}")
            else:
                print("   ❌ No messages found")
                
                # Let's try to debug further by listing chats directly
                print("\n🔍 Step 3: Debug - List chats directly")
                from asgiref.sync import async_to_sync
                
                try:
                    chats_response = async_to_sync(client.messaging.list_chats)(
                        account_id=linkedin_conn.unipile_account_id,
                        limit=10
                    )
                    
                    if chats_response and 'items' in chats_response:
                        print(f"   Found {len(chats_response['items'])} chats:")
                        for chat in chats_response['items'][:5]:
                            print(f"      - ID: {chat.get('id')}")
                            print(f"        Subject: {chat.get('subject', 'No subject')}")
                            print(f"        Attendee IDs: {chat.get('attendee_ids', [])}")
                    else:
                        print("   No chats found")
                        
                except Exception as e:
                    print(f"   ❌ Error listing chats: {e}")
                    
        else:
            print("   ❌ No attendees found")
            
    else:
        print("❌ No LinkedIn connection found")