#!/usr/bin/env python
"""
Check for emails to/from vanessa.c.brown86@gmail.com
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
from communications.models import Message, Conversation, Channel, Participant
from pipelines.models import Record

print("=" * 80)
print("CHECKING FOR VANESSA'S EMAIL")
print("=" * 80)

# Use oneotalent tenant
with schema_context('oneotalent'):
    # First, check if there's a contact record with this email
    print("\n1. Checking for contact record with email: vanessa.c.brown86@gmail.com")
    
    # Search for records with this email in data field
    contact_records = Record.objects.filter(
        data__icontains='vanessa.c.brown86@gmail.com'
    )
    
    print(f"   Found {contact_records.count()} contact record(s) with this email")
    
    for record in contact_records:
        # Get name from data field or use ID
        name = record.data.get('name', record.data.get('full_name', f'Record {record.id}'))
        print(f"\n   📇 Contact: {name} (ID: {record.id})")
        print(f"      Pipeline: {record.pipeline.name}")
        print(f"      Email in data: {record.data.get('email', 'Not found')}")
        print(f"      Full data: {record.data}")
    
    # Check for participants with this email
    print("\n2. Checking for participants with this email...")
    participants = Participant.objects.filter(
        email__iexact='vanessa.c.brown86@gmail.com'
    )
    
    print(f"   Found {participants.count()} participant(s)")
    for p in participants:
        print(f"   - {p.name or p.display_name} ({p.email})")
        print(f"     Has contact: {bool(p.contact_record)}")
        if p.contact_record:
            print(f"     Contact ID: {p.contact_record.id}")
    
    # Check for recent messages involving this email
    print("\n3. Checking for recent messages...")
    
    # Get messages from the last 2 hours
    time_threshold = timezone.now() - timedelta(hours=2)
    
    # Check messages where this email appears in metadata
    recent_messages = Message.objects.filter(
        created_at__gte=time_threshold
    ).filter(
        metadata__icontains='vanessa.c.brown86@gmail.com'
    ).order_by('-created_at')
    
    print(f"   Found {recent_messages.count()} message(s) mentioning this email in last 2 hours")
    
    for msg in recent_messages:
        print(f"\n   📧 Message ID: {msg.id}")
        print(f"      Channel: {msg.channel.channel_type if msg.channel else 'Unknown'}")
        print(f"      Direction: {msg.direction}")
        print(f"      Created: {msg.created_at}")
        print(f"      Content preview: {msg.content[:100] if msg.content else '(empty)'}...")
        
        # Check metadata for email details
        if msg.metadata:
            if 'sender_info' in msg.metadata:
                print(f"      From: {msg.metadata.get('sender_info')}")
            if 'recipients' in msg.metadata:
                recipients = msg.metadata.get('recipients', {})
                if recipients.get('to'):
                    print(f"      To: {recipients.get('to')}")
    
    # Also check by participant relationships
    print("\n4. Checking messages through participant relationships...")
    
    if participants.exists():
        participant = participants.first()
        
        # Get messages where this participant is the sender
        participant_messages = Message.objects.filter(
            sender_participant=participant,
            created_at__gte=time_threshold
        ).order_by('-created_at')
        
        print(f"   Found {participant_messages.count()} message(s) for this participant")
        
        for msg in participant_messages[:5]:
            print(f"\n   📨 Message via participant: {msg.id}")
            print(f"      Subject: {msg.conversation.subject if msg.conversation else 'No subject'}")
            print(f"      Created: {msg.created_at}")
    
    # Check all Gmail messages from last 2 hours to see what's coming through
    print("\n5. All Gmail messages in last 2 hours:")
    print("-" * 40)
    
    all_gmail = Message.objects.filter(
        channel__channel_type='gmail',
        created_at__gte=time_threshold
    ).order_by('-created_at')
    
    print(f"   Total Gmail messages: {all_gmail.count()}")
    
    for msg in all_gmail[:10]:
        print(f"\n   📧 {msg.external_message_id}")
        print(f"      Created: {msg.created_at}")
        print(f"      Direction: {msg.direction}")
        if msg.metadata:
            sender = msg.metadata.get('sender_info', {})
            recipients = msg.metadata.get('recipients', {})
            print(f"      From: {sender}")
            if recipients.get('to'):
                print(f"      To: {recipients.get('to')}")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)