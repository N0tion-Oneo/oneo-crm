#!/usr/bin/env python
"""
Test WhatsApp sync to see if messages are being fetched and stored
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Channel, UserChannelConnection, ChatAttendee, Message, Conversation
from communications.channels.whatsapp.background_sync import _run_comprehensive_sync_simplified

def test_sync():
    """Test sync to see what's happening with messages"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Testing WhatsApp Sync")
        print("=" * 60)
        
        # Get the WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        
        print(f"✅ Channel: {channel.name}")
        
        # Get the connection
        connection = UserChannelConnection.objects.filter(
            unipile_account_id=channel.unipile_account_id,
            channel_type='whatsapp'
        ).first()
        
        if not connection:
            print("❌ No connection found")
            return
            
        stored_phone = connection.connection_config.get('phone_number')
        print(f"✅ Business phone: {stored_phone}")
        
        # Count messages before sync
        messages_before = Message.objects.filter(channel=channel).count()
        conversations_before = Conversation.objects.filter(channel=channel).count()
        attendees_before = ChatAttendee.objects.filter(channel=channel).count()
        
        print(f"\n📊 Before sync:")
        print(f"   Messages: {messages_before}")
        print(f"   Conversations: {conversations_before}")
        print(f"   Attendees: {attendees_before}")
        
        print("\n" + "=" * 60)
        print("🔄 RUNNING SYNC")
        print("=" * 60)
        
        # Run the sync with minimal options
        sync_options = {
            'days_back': 7,  # Get messages from last 7 days
            'conversations_per_batch': 10,
            'messages_per_batch': 50,
            'max_messages_per_chat': 100,
            'include_attachments': False
        }
        
        try:
            # Run the simplified comprehensive sync
            result = _run_comprehensive_sync_simplified(
                channel=channel,
                options=sync_options,
                connection=connection
            )
            
            print("\n✅ Sync completed:")
            print(f"   Chats synced: {result.get('chats_synced', 0)}")
            print(f"   Messages synced: {result.get('messages_synced', 0)}")
            print(f"   Attendees synced: {result.get('attendees_synced', 0)}")
            print(f"   Conversations created: {result.get('conversations_created', 0)}")
            print(f"   Conversations updated: {result.get('conversations_updated', 0)}")
            
            if result.get('errors'):
                print(f"\n⚠️ Errors encountered:")
                for error in result['errors']:
                    print(f"   - {error}")
            
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Count messages after sync
        messages_after = Message.objects.filter(channel=channel).count()
        conversations_after = Conversation.objects.filter(channel=channel).count()
        attendees_after = ChatAttendee.objects.filter(channel=channel).count()
        
        print(f"\n📊 After sync:")
        print(f"   Messages: {messages_after} (+{messages_after - messages_before})")
        print(f"   Conversations: {conversations_after} (+{conversations_after - conversations_before})")
        print(f"   Attendees: {attendees_after} (+{attendees_after - attendees_before})")
        
        # Show some recent messages
        recent_messages = Message.objects.filter(
            channel=channel
        ).order_by('-created_at')[:5]
        
        print(f"\n📨 Recent messages:")
        for msg in recent_messages:
            sender_name = "Unknown"
            if msg.sender:
                sender_name = msg.sender.name
            elif msg.metadata and msg.metadata.get('attendee_name'):
                sender_name = msg.metadata['attendee_name']
            
            content_preview = msg.content[:50] if msg.content else "No content"
            print(f"   [{msg.direction}] {sender_name}: {content_preview}")
            print(f"      External ID: {msg.external_message_id}")
            print(f"      Created: {msg.created_at}")
        
        # Check conversations
        recent_convs = Conversation.objects.filter(
            channel=channel
        ).order_by('-updated_at')[:3]
        
        print(f"\n💬 Recent conversations:")
        for conv in recent_convs:
            msg_count = conv.messages.count()
            attendee_count = conv.conversation_attendees.count()
            print(f"   {conv.subject}: {msg_count} messages, {attendee_count} attendees")
            print(f"      External ID: {conv.external_thread_id}")
            
            # Show messages in this conversation
            conv_messages = conv.messages.order_by('-created_at')[:3]
            for msg in conv_messages:
                content_preview = msg.content[:40] if msg.content else "No content"
                print(f"         - {content_preview}")
        
        print("\n" + "=" * 60)
        print("✅ Sync test complete!")
        print("=" * 60)

if __name__ == "__main__":
    test_sync()