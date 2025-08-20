#!/usr/bin/env python3
"""
Debug script to find the mismatch between synced attendees and conversations
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
import django
django.setup()

from django_tenants.utils import tenant_context
from tenants.models import Tenant
from communications.models import Conversation, ChatAttendee, Channel
from communications.unipile_sdk import unipile_service
from asgiref.sync import sync_to_async

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_sync_mismatch():
    """Find attendees that should be synced for conversations with messages"""
    
    account_id = "mp9Gis3IRtuh9V5oSxZdSA"
    
    # Get tenant context
    tenant = await sync_to_async(Tenant.objects.get)(schema_name='oneotalent')
    
    with tenant_context(tenant):
        channel = await sync_to_async(Channel.objects.filter(channel_type='whatsapp').first)()
        
        # Find conversations with messages (these are the ones we care about)
        conversations_with_messages = await sync_to_async(list)(
            Conversation.objects.filter(
                channel=channel,
                messages__isnull=False
            ).distinct()
        )
        
        print(f"📊 Conversations with messages: {len(conversations_with_messages)}")
        
        for conv in conversations_with_messages:
            print(f"\n💬 Conversation: {conv.subject}")
            print(f"   External ID: {conv.external_thread_id}")
            message_count = await sync_to_async(conv.messages.count)()
            print(f"   Messages: {message_count}")
            
            # Try to get the chat data from Unipile
            try:
                client = unipile_service.get_client()
                
                # Get the chat details
                chat_details = await client.messaging.get_chat_by_id(conv.external_thread_id)
                if chat_details:
                    provider_id = chat_details.get('provider_id') or chat_details.get('attendee_provider_id')
                    print(f"   Provider ID from API: {provider_id}")
                    
                    # Check if we have this attendee
                    attendee = await sync_to_async(ChatAttendee.objects.filter(
                        channel=channel,
                        provider_id=provider_id
                    ).first)()
                    
                    if attendee:
                        print(f"   ✅ Attendee found: {attendee.name}")
                    else:
                        print(f"   ❌ Missing attendee for provider_id: {provider_id}")
                        
                        # Try to find this attendee in the full attendee list
                        try:
                            attendees_data = await client.messaging.get_all_attendees(
                                account_id=account_id,
                                limit=100
                            )
                            
                            attendees = attendees_data.get('items', [])
                            matching_attendee = None
                            
                            for att in attendees:
                                if att.get('provider_id') == provider_id:
                                    matching_attendee = att
                                    break
                            
                            if matching_attendee:
                                print(f"   🔍 Found in API: {matching_attendee.get('name', 'Unknown')} ({matching_attendee.get('provider_id')})")
                            else:
                                print(f"   ⚠️  Not found in attendees API either")
                                
                        except Exception as e:
                            print(f"   ⚠️  Error checking attendees: {e}")
                else:
                    print(f"   ⚠️  Could not get chat details from API")
                    
            except Exception as e:
                print(f"   ❌ Error getting chat details: {e}")

if __name__ == "__main__":
    asyncio.run(debug_sync_mismatch())