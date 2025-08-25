#!/usr/bin/env python
"""
Manual sync test with detailed debugging
"""
import os
import sys
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from django_tenants.utils import schema_context
from communications.models import Channel, Conversation, ChatAttendee, Message
from communications.channels.whatsapp.sync.conversations import ConversationSyncService
from communications.channels.whatsapp.sync.messages import MessageSyncService
from communications.channels.whatsapp.sync.attendees import AttendeeSyncService

def test_manual_sync():
    """Test manual sync with detailed debugging"""
    
    with schema_context('oneotalent'):
        print("\n=== MANUAL SYNC TEST ===\n")
        
        # Get channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No channel found")
            return
        
        print(f"✅ Using channel: {channel.name}")
        
        # 1. Test conversation sync
        print("\n--- SYNCING CONVERSATIONS ---")
        conv_service = ConversationSyncService(channel=channel)
        
        # Sync just 2 conversations for testing
        conv_stats = conv_service.sync_conversations(max_conversations=2)
        
        print(f"Conversation sync results:")
        print(f"  Synced: {conv_stats['conversations_synced']}")
        print(f"  Created: {conv_stats['conversations_created']}")
        print(f"  Updated: {conv_stats['conversations_updated']}")
        print(f"  Attendees: {conv_stats['attendees_synced']}")
        print(f"  Errors: {conv_stats.get('errors', [])}")
        
        # Check what was saved
        conversations = Conversation.objects.filter(channel=channel)
        print(f"\nConversations in DB: {conversations.count()}")
        
        if conversations.exists():
            # 2. Test message sync for first conversation
            first_conv = conversations.first()
            print(f"\n--- SYNCING MESSAGES FOR: {first_conv.subject or first_conv.external_thread_id} ---")
            
            msg_service = MessageSyncService(channel=channel)
            msg_stats = msg_service.sync_messages_for_conversation(
                first_conv,
                max_messages=5
            )
            
            print(f"Message sync results:")
            print(f"  Synced: {msg_stats['messages_synced']}")
            print(f"  Created: {msg_stats['messages_created']}")
            print(f"  Attendees: {msg_stats.get('attendees_synced', 0)}")
            print(f"  Errors: {msg_stats.get('errors', [])}")
            
            # Check messages
            messages = Message.objects.filter(conversation=first_conv)
            print(f"\nMessages in DB for this conversation: {messages.count()}")
            
            for msg in messages[:3]:
                print(f"  - {msg.content[:50]}...")
                print(f"    Sender: {msg.sender}")
                print(f"    Direction: {msg.direction}")
        
        # 3. Check attendees
        attendees = ChatAttendee.objects.filter(channel=channel)
        print(f"\n--- ATTENDEES IN DB: {attendees.count()} ---")
        for att in attendees[:5]:
            print(f"  - {att.name}")
            print(f"    ID: {att.external_attendee_id}")
            print(f"    Is Self: {att.is_self}")

if __name__ == "__main__":
    test_manual_sync()