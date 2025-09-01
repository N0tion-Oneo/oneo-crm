#!/usr/bin/env python
"""
Check recent webhook activity and email messages
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.utils import timezone
from communications.models import Message, Conversation, Channel, Participant, UserChannelConnection

print("=" * 80)
print("RECENT EMAIL ACTIVITY CHECK")
print(f"Current time: {timezone.now()}")
print("=" * 80)

with schema_context('oneotalent'):
    # Check Gmail connection status
    print("\n1. Gmail Connection Status:")
    print("-" * 40)
    
    gmail_connection = UserChannelConnection.objects.filter(
        channel_type='gmail',
        is_active=True
    ).first()
    
    if gmail_connection:
        print(f"✅ Active Gmail connection found")
        print(f"   Account: {gmail_connection.account_name}")
        print(f"   Account ID: {gmail_connection.unipile_account_id}")
        print(f"   Status: {gmail_connection.auth_status}")
        print(f"   Last sync: {gmail_connection.last_sync_at}")
    else:
        print("❌ No active Gmail connection")
    
    # Check recent messages (last 30 minutes)
    print("\n2. Recent Email Messages (last 30 minutes):")
    print("-" * 40)
    
    time_threshold = timezone.now() - timedelta(minutes=30)
    
    recent_emails = Message.objects.filter(
        channel__channel_type='gmail',
        created_at__gte=time_threshold
    ).order_by('-created_at')
    
    print(f"Found {recent_emails.count()} email message(s)")
    
    for msg in recent_emails[:10]:
        print(f"\n📧 Message: {msg.id}")
        print(f"   External ID: {msg.external_message_id}")
        print(f"   Direction: {msg.direction}")
        print(f"   Created: {msg.created_at}")
        print(f"   Subject: {msg.conversation.subject if msg.conversation else 'No conversation'}")
        
        # Show sender/recipient info
        if msg.sender_participant:
            print(f"   From: {msg.sender_participant.email}")
            if msg.sender_participant.contact_record:
                print(f"   From Contact: Yes (ID: {msg.sender_participant.contact_record.id})")
        
        # Check metadata for recipients
        if msg.metadata and 'recipients' in msg.metadata:
            recipients = msg.metadata.get('recipients', {})
            to_list = recipients.get('to', [])
            if to_list:
                print(f"   To: {', '.join([r.get('identifier', r.get('email', 'unknown')) for r in to_list])}")
    
    # Check ALL recent messages (any channel) to see what's coming through
    print("\n3. ALL Recent Messages (any channel, last 30 minutes):")
    print("-" * 40)
    
    all_recent = Message.objects.filter(
        created_at__gte=time_threshold
    ).order_by('-created_at')
    
    print(f"Found {all_recent.count()} total message(s)")
    
    channel_counts = {}
    for msg in all_recent:
        channel_type = msg.channel.channel_type if msg.channel else 'unknown'
        channel_counts[channel_type] = channel_counts.get(channel_type, 0) + 1
    
    for channel_type, count in channel_counts.items():
        print(f"   {channel_type}: {count} message(s)")
    
    # Check conversations
    print("\n4. Recent Email Conversations (last 30 minutes):")
    print("-" * 40)
    
    recent_convos = Conversation.objects.filter(
        channel__channel_type='gmail',
        created_at__gte=time_threshold
    ).order_by('-created_at')
    
    print(f"Found {recent_convos.count()} conversation(s)")
    
    for convo in recent_convos[:5]:
        print(f"\n💬 Conversation: {convo.id}")
        print(f"   Subject: {convo.subject}")
        print(f"   Created: {convo.created_at}")
        print(f"   Message count: {convo.messages.count()}")
    
    # Check participants with Vanessa's email
    print("\n5. Vanessa's Participant Status:")
    print("-" * 40)
    
    vanessa_participant = Participant.objects.filter(
        email__iexact='vanessa.c.brown86@gmail.com'
    ).first()
    
    if vanessa_participant:
        print(f"✅ Vanessa's participant found")
        print(f"   ID: {vanessa_participant.id}")
        print(f"   Email: {vanessa_participant.email}")
        print(f"   Has contact: {bool(vanessa_participant.contact_record)}")
        if vanessa_participant.contact_record:
            print(f"   Contact ID: {vanessa_participant.contact_record.id}")
        
        # Check recent messages involving Vanessa
        vanessa_messages = Message.objects.filter(
            sender_participant=vanessa_participant,
            created_at__gte=time_threshold
        ).count()
        
        print(f"   Messages from Vanessa (last 30 min): {vanessa_messages}")
    else:
        print("❌ No participant found for Vanessa")
    
    # Check if there are any messages TO Vanessa
    print("\n6. Messages TO/FROM vanessa.c.brown86@gmail.com:")
    print("-" * 40)
    
    # Search in metadata
    messages_with_vanessa = Message.objects.filter(
        created_at__gte=time_threshold,
        metadata__icontains='vanessa.c.brown86@gmail.com'
    )
    
    print(f"Found {messages_with_vanessa.count()} message(s) mentioning Vanessa's email")
    
    for msg in messages_with_vanessa[:5]:
        print(f"\n   Message ID: {msg.id}")
        print(f"   Created: {msg.created_at}")
        print(f"   Direction: {msg.direction}")
        
        # Try to extract more info
        if msg.metadata:
            if 'sender_info' in msg.metadata:
                sender = msg.metadata['sender_info']
                if isinstance(sender, dict):
                    print(f"   From: {sender.get('email', 'unknown')}")
            if 'recipients' in msg.metadata:
                recipients = msg.metadata['recipients']
                if isinstance(recipients, dict) and 'to' in recipients:
                    to_list = recipients['to']
                    if to_list:
                        print(f"   To: {to_list}")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
print("\nIf your email doesn't appear:")
print("1. UniPile may not have sent the webhook yet (can take a few seconds)")
print("2. Check if the webhook URL is correctly configured in UniPile")
print("3. The email might not match any contacts (check sender/recipient)")
print("4. There might be an error in webhook processing")
print("=" * 80)