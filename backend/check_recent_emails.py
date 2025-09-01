#!/usr/bin/env python
"""
Check for recently received emails in the system
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
from communications.models import Message, Conversation, Channel

print("=" * 80)
print("CHECKING RECENT EMAIL MESSAGES")
print("=" * 80)

# Use oneotalent tenant
with schema_context('oneotalent'):
    # Get messages from the last hour
    time_threshold = timezone.now() - timedelta(hours=1)
    
    print(f"\nLooking for messages since: {time_threshold}")
    
    # Check for Gmail messages
    gmail_messages = Message.objects.filter(
        channel__channel_type='gmail',
        created_at__gte=time_threshold
    ).order_by('-created_at')
    
    print(f"\nFound {gmail_messages.count()} Gmail message(s) in the last hour")
    
    if gmail_messages.exists():
        print("\nRecent Gmail Messages:")
        print("-" * 40)
        for msg in gmail_messages[:10]:  # Show last 10
            print(f"\n📧 Message ID: {msg.id}")
            print(f"   External ID: {msg.external_message_id}")
            print(f"   Subject: {msg.conversation.subject if msg.conversation else 'No conversation'}")
            print(f"   From: {msg.sender_name or 'Unknown'}")
            print(f"   Direction: {msg.direction}")
            print(f"   Content: {msg.content[:100]}..." if msg.content else "   Content: (empty)")
            print(f"   Created: {msg.created_at}")
            print(f"   Status: {msg.status}")
            
            # Check metadata
            if msg.metadata:
                print(f"   Has metadata: Yes")
                if 'email_specific' in msg.metadata:
                    print(f"   Email specific: {msg.metadata.get('email_specific')}")
                if 'folder' in msg.metadata:
                    print(f"   Folder: {msg.metadata.get('folder')}")
    else:
        print("\n❌ No Gmail messages found in the last hour")
    
    # Also check all channels to see what's connected
    print("\n" + "=" * 40)
    print("Active Gmail Channels:")
    print("-" * 40)
    
    gmail_channels = Channel.objects.filter(
        channel_type='gmail',
        is_active=True
    )
    
    for channel in gmail_channels:
        print(f"\n📮 Channel: {channel.name}")
        print(f"   Account ID: {channel.unipile_account_id}")
        print(f"   Status: {channel.auth_status}")
        
        # Count messages in this channel
        msg_count = Message.objects.filter(channel=channel).count()
        recent_count = Message.objects.filter(
            channel=channel,
            created_at__gte=time_threshold
        ).count()
        print(f"   Total messages: {msg_count}")
        print(f"   Messages in last hour: {recent_count}")
    
    # Check for any messages regardless of channel type
    print("\n" + "=" * 40)
    print("All Recent Messages (any channel):")
    print("-" * 40)
    
    all_recent = Message.objects.filter(
        created_at__gte=time_threshold
    ).order_by('-created_at')
    
    print(f"\nFound {all_recent.count()} total message(s) in the last hour")
    
    if all_recent.exists():
        for msg in all_recent[:5]:
            print(f"\n   Channel Type: {msg.channel.channel_type if msg.channel else 'Unknown'}")
            print(f"   Subject/Content: {msg.conversation.subject if msg.conversation else msg.content[:50]}")
            print(f"   Created: {msg.created_at}")

print("\n" + "=" * 80)