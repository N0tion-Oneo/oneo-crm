#!/usr/bin/env python
"""
Clear all WhatsApp data from the database
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from tenants.models import Tenant

# Switch to oneotalent tenant
oneo_tenant = Tenant.objects.get(schema_name='oneotalent')
connection.set_tenant(oneo_tenant)
print(f"📌 Using tenant: {oneo_tenant.schema_name} ({oneo_tenant.name})")

from communications.models import (
    Channel, Message, Conversation, ChatAttendee, ConversationAttendee
)

print("\n" + "=" * 60)
print("🗑️  Clearing WhatsApp Data")
print("=" * 60)

# Get WhatsApp channels
whatsapp_channels = Channel.objects.filter(channel_type='whatsapp')
print(f"\nFound {whatsapp_channels.count()} WhatsApp channels")

# Count before deletion
print("\n📊 Before Deletion:")
msg_count = Message.objects.filter(channel__channel_type='whatsapp').count()
conv_count = Conversation.objects.filter(channel__channel_type='whatsapp').count()
attendee_count = ChatAttendee.objects.filter(channel__channel_type='whatsapp').count()
conv_attendee_count = ConversationAttendee.objects.filter(
    conversation__channel__channel_type='whatsapp'
).count()

print(f"  Messages: {msg_count}")
print(f"  Conversations: {conv_count}")
print(f"  Attendees: {attendee_count}")
print(f"  Conversation Attendees: {conv_attendee_count}")

# Delete data
print("\n🧹 Deleting...")

# Delete messages
deleted_msgs = Message.objects.filter(channel__channel_type='whatsapp').delete()
print(f"  Deleted {deleted_msgs[0]} messages")

# Delete conversation attendees (many-to-many through table)
deleted_conv_attendees = ConversationAttendee.objects.filter(
    conversation__channel__channel_type='whatsapp'
).delete()
print(f"  Deleted {deleted_conv_attendees[0]} conversation attendees")

# Delete conversations
deleted_convs = Conversation.objects.filter(channel__channel_type='whatsapp').delete()
print(f"  Deleted {deleted_convs[0]} conversations")

# Delete attendees
deleted_attendees = ChatAttendee.objects.filter(channel__channel_type='whatsapp').delete()
print(f"  Deleted {deleted_attendees[0]} attendees")

# Verify deletion
print("\n📊 After Deletion:")
msg_count_after = Message.objects.filter(channel__channel_type='whatsapp').count()
conv_count_after = Conversation.objects.filter(channel__channel_type='whatsapp').count()
attendee_count_after = ChatAttendee.objects.filter(channel__channel_type='whatsapp').count()
conv_attendee_count_after = ConversationAttendee.objects.filter(
    conversation__channel__channel_type='whatsapp'
).count()

print(f"  Messages: {msg_count_after}")
print(f"  Conversations: {conv_count_after}")
print(f"  Attendees: {attendee_count_after}")
print(f"  Conversation Attendees: {conv_attendee_count_after}")

print("\n" + "=" * 60)
print("✅ WhatsApp data cleared!")
print("=" * 60)
