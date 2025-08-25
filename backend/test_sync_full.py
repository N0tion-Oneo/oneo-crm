#!/usr/bin/env python
"""
Test full WhatsApp sync: chats, attendees, messages, and direction
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django.utils import timezone
from tenants.models import Tenant

# Switch to oneotalent tenant for testing
oneo_tenant = Tenant.objects.get(schema_name='oneotalent')
connection.set_tenant(oneo_tenant)
print(f"📌 Using tenant: {oneo_tenant.schema_name} ({oneo_tenant.name})")

print("=" * 60)
print("🧪 Testing Full WhatsApp Sync")
print("=" * 60)

from communications.models import (
    Channel, UserChannelConnection, Conversation, Message, ChatAttendee
)
from communications.channels.whatsapp.sync import (
    ComprehensiveSyncService,
    ConversationSyncService,
    MessageSyncService,
    AttendeeSyncService,
)

# Get the real WhatsApp channel with the specific account ID
channel = Channel.objects.filter(
    channel_type='whatsapp',
    unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
).first()

if not channel:
    print("❌ No WhatsApp channel found with real account")
    sys.exit(1)

print(f"📱 Using channel: {channel.name}")
print(f"   Account ID: {channel.unipile_account_id}")

# Get Josh's connection for this account
connection_obj = UserChannelConnection.objects.filter(
    unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA',
    user__email='josh@oneodigital.com',
    is_active=True
).first()

if connection_obj:
    print(f"👤 Using connection: {connection_obj.account_name}")
    print(f"   User: {connection_obj.user.email}")

# Check current state before sync
print("\n📊 Current State:")
conv_count = Conversation.objects.filter(channel=channel).count()
msg_count = Message.objects.filter(channel=channel).count()
attendee_count = ChatAttendee.objects.filter(channel=channel).count()

print(f"   Conversations: {conv_count}")
print(f"   Messages: {msg_count}")
print(f"   Attendees: {attendee_count}")

# Check message directions
inbound = Message.objects.filter(channel=channel, direction='inbound').count()
outbound = Message.objects.filter(channel=channel, direction='outbound').count()
print(f"   Message directions - Inbound: {inbound}, Outbound: {outbound}")

print("\n🚀 Starting Comprehensive Sync...")
print("-" * 40)

# Run comprehensive sync
sync_service = ComprehensiveSyncService(
    channel=channel,
    connection=connection_obj
)

# Run sync with options
sync_options = {
    'max_conversations': 10,  # Limit for testing
    'max_messages_per_chat': 50,
    'days_back': 7
}

result = sync_service.run_comprehensive_sync(sync_options)

print("\n📊 Sync Results:")
print(f"   Conversations synced: {result.get('conversations_synced', 0)}")
print(f"   Messages synced: {result.get('messages_synced', 0)}")
print(f"   Attendees synced: {result.get('attendees_synced', 0)}")
print(f"   Conversations created: {result.get('conversations_created', 0)}")
print(f"   Messages created: {result.get('messages_created', 0)}")

if result.get('errors'):
    print(f"\n⚠️ Errors encountered:")
    for error in result['errors'][:5]:  # Show first 5 errors
        print(f"   - {error}")

# Check final state
print("\n📊 Final State:")
conv_count_after = Conversation.objects.filter(channel=channel).count()
msg_count_after = Message.objects.filter(channel=channel).count()
attendee_count_after = ChatAttendee.objects.filter(channel=channel).count()

print(f"   Conversations: {conv_count} → {conv_count_after} (+{conv_count_after - conv_count})")
print(f"   Messages: {msg_count} → {msg_count_after} (+{msg_count_after - msg_count})")
print(f"   Attendees: {attendee_count} → {attendee_count_after} (+{attendee_count_after - attendee_count})")

# Check message directions after sync
inbound_after = Message.objects.filter(channel=channel, direction='inbound').count()
outbound_after = Message.objects.filter(channel=channel, direction='outbound').count()
print(f"   Message directions - Inbound: {inbound} → {inbound_after} (+{inbound_after - inbound})")
print(f"                       Outbound: {outbound} → {outbound_after} (+{outbound_after - outbound})")

# Show sample attendees
print("\n👥 Sample Attendees (first 10):")
attendees = ChatAttendee.objects.filter(channel=channel).order_by('-created_at')[:10]
for attendee in attendees:
    phone = attendee.metadata.get('phone_number', 'N/A') if attendee.metadata else 'N/A'
    print(f"   - {attendee.name} ({attendee.external_attendee_id[:20]}...)")
    print(f"     Phone: {phone}, Is Self: {attendee.is_self}")

# Show sample conversations with attendees
print("\n💬 Sample Conversations with Attendees (first 5):")
conversations = Conversation.objects.filter(channel=channel).order_by('-last_message_at')[:5]
for conv in conversations:
    print(f"\n   📌 {conv.subject or 'Unnamed'} ({conv.external_thread_id[:20]}...)")
    print(f"      Type: {conv.conversation_type}, Messages: {conv.message_count}")
    
    # Show attendees in this conversation
    conv_attendees = conv.attendees.all()[:3]
    if conv_attendees:
        print(f"      Attendees:")
        for att in conv_attendees:
            print(f"        - {att.name} (Self: {att.is_self})")
    
    # Show sample messages with direction
    messages = Message.objects.filter(conversation=conv).order_by('-created_at')[:3]
    if messages:
        print(f"      Recent messages:")
        for msg in messages:
            direction_icon = "→" if msg.direction == 'outbound' else "←"
            sender_name = msg.sender.name if msg.sender else "Unknown"
            content_preview = msg.content[:50] if msg.content else "(empty)"
            print(f"        {direction_icon} {sender_name}: {content_preview}")

print("\n" + "=" * 60)
print("✅ Sync test completed!")
print("=" * 60)