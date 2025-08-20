#!/usr/bin/env python3
"""
Debug script to check conversation names and attendee data
"""
import os
import sys
import django
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import tenant_context
from tenants.models import Tenant
from communications.models import Conversation, Message, ChatAttendee, Channel
from django.db.models import Count

def debug_conversations():
    """Debug conversation names and attendee data"""
    
    # Get the OneOTalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with tenant_context(tenant):
        print(f'🏢 Using tenant: {tenant.name} (schema: {tenant.schema_name})')
        
        # Find the WhatsApp channel
        channels = Channel.objects.filter(channel_type='whatsapp')
        print(f'\n📱 WhatsApp Channels ({channels.count()} total):')
        
        if not channels.exists():
            print('  No WhatsApp channels found!')
            return
            
        channel = channels.first()
        print(f'  Channel: {channel.name} (account_id: {channel.unipile_account_id})')

        # Show all attendees with names
        attendees = ChatAttendee.objects.filter(channel=channel)
        print(f'\n👥 ChatAttendees ({attendees.count()} total):')
        for attendee in attendees:
            print(f'  - "{attendee.name}" (provider_id: {attendee.provider_id}, is_self: {attendee.is_self})')

        # Show all conversations with their subjects and message counts
        conversations = Conversation.objects.filter(channel=channel).annotate(msg_count=Count('messages'))
        print(f'\n💬 Conversations ({conversations.count()} total):')
        for conv in conversations:
            print(f'  - Subject: "{conv.subject}"')
            print(f'    ID: {conv.external_thread_id}')
            print(f'    Messages: {conv.msg_count}')
            
            # Show the attendees in metadata
            attendees = conv.metadata.get('attendees', [])
            if attendees:
                attendee_names = [a.get('name', 'Unknown') for a in attendees]
                print(f'    Attendees in metadata: {attendee_names}')
            else:
                print(f'    No attendees in metadata')
            print()

        # Show messages with direction
        messages = Message.objects.filter(channel=channel).order_by('created_at')
        print(f'\n📨 Messages ({messages.count()} total):')
        for msg in messages:
            direction_arrow = '→' if msg.direction == 'outbound' else '←'
            content_preview = msg.content[:50] + '...' if len(msg.content) > 50 else msg.content
            print(f'  {direction_arrow} "{content_preview}" (direction: {msg.direction})')

if __name__ == "__main__":
    debug_conversations()