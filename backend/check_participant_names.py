#!/usr/bin/env python
"""
Check participant names in the database
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Participant, Message, Conversation

with schema_context('oneotalent'):
    print("=" * 60)
    print("CHECKING PARTICIPANT NAMES IN DATABASE")
    print("=" * 60)
    
    # Check WhatsApp participants (phone contains actual phone numbers)
    whatsapp_participants = Participant.objects.filter(phone__regex=r'^\+?[0-9]{10,}').exclude(phone='')[:10]
    print(f"\n📱 WhatsApp Participants (found {whatsapp_participants.count()}):")
    for p in whatsapp_participants:
        print(f"  ID: {p.id}")
        print(f"  Phone: {p.phone}")
        print(f"  Name: '{p.name}' (empty: {not p.name})")
        print(f"  Display Name: '{p.get_display_name()}'")
        print("  ---")
    
    # Check LinkedIn participants
    linkedin_participants = Participant.objects.filter(linkedin_member_urn__isnull=False).exclude(linkedin_member_urn='')[:10]
    print(f"\n💼 LinkedIn Participants (found {linkedin_participants.count()}):")
    for p in linkedin_participants:
        print(f"  ID: {p.id}")
        print(f"  URN: {p.linkedin_member_urn[:30]}...")
        print(f"  Name: '{p.name}' (empty: {not p.name})")
        print(f"  Display Name: '{p.get_display_name()}'")
        print("  ---")
    
    # Check specific phone number (Saul's)
    print(f"\n🔍 Looking for Saul's WhatsApp (27845855518):")
    saul_participant = Participant.objects.filter(phone='27845855518').first()
    if saul_participant:
        print(f"  Found! ID: {saul_participant.id}")
        print(f"  Name: '{saul_participant.name}'")
        print(f"  Email: {saul_participant.email}")
        print(f"  Phone: {saul_participant.phone}")
        
        # Check messages from this participant
        messages = Message.objects.filter(sender_participant=saul_participant)[:3]
        print(f"  Has {messages.count()} messages as sender")
    else:
        print("  Not found as exact match!")
        # Try to find by provider_id in metadata
        saul_by_metadata = Participant.objects.filter(metadata__provider_id__contains='27845855518').first()
        if saul_by_metadata:
            print(f"  Found in metadata! ID: {saul_by_metadata.id}")
            print(f"  Name: '{saul_by_metadata.name}'")
            print(f"  Phone: {saul_by_metadata.phone}")
            print(f"  Metadata: {saul_by_metadata.metadata}")
    
    # Check recent WhatsApp conversation
    print(f"\n💬 Recent WhatsApp Conversation:")
    whatsapp_conv = Conversation.objects.filter(
        channel__channel_type='whatsapp'
    ).order_by('-last_message_at').first()
    
    if whatsapp_conv:
        print(f"  Conversation ID: {whatsapp_conv.id}")
        print(f"  Subject: {whatsapp_conv.subject}")
        
        # Get participants in this conversation
        participants = Participant.objects.filter(
            conversation_memberships__conversation=whatsapp_conv
        ).distinct()
        
        print(f"  Participants ({participants.count()}):")
        for p in participants:
            print(f"    - {p.get_display_name()} (Name: '{p.name}', Phone: {p.phone})")
        
        # Get recent messages
        messages = Message.objects.filter(
            conversation=whatsapp_conv
        ).order_by('-created_at')[:3]
        
        print(f"  Recent messages:")
        for msg in messages:
            sender_name = msg.sender_participant.get_display_name() if msg.sender_participant else 'Unknown'
            sender_actual = msg.sender_participant.name if msg.sender_participant else 'No participant'
            print(f"    - From: {sender_name} (actual name field: '{sender_actual}')")
            print(f"      Content: {msg.content[:50]}...")
    
    # Check all participants with metadata
    print(f"\n🔍 Checking participants with provider_id in metadata:")
    participants_with_provider = Participant.objects.filter(metadata__provider_id__isnull=False)[:10]
    for p in participants_with_provider:
        print(f"  ID: {p.id}")
        print(f"  Name: '{p.name}' (empty: {not p.name})")
        print(f"  Phone: {p.phone}")
        print(f"  Provider ID: {p.metadata.get('provider_id', 'N/A')}")
        print("  ---")
