#!/usr/bin/env python
"""
Debug attendee name mapping  
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.conf import settings
from django_tenants.utils import schema_context
from communications.models import Participant, UserChannelConnection, Message
from communications.record_communications.unipile_integration import AttendeeResolver
from communications.unipile.core.client import UnipileClient

with schema_context('oneotalent'):
    print("=" * 60)
    print("DEBUGGING ATTENDEE NAME MAPPING")
    print("=" * 60)
    
    # Get WhatsApp connection
    whatsapp_conn = UserChannelConnection.objects.filter(
        channel_type='whatsapp',
        auth_status='authenticated'
    ).first()
    
    if whatsapp_conn:
        print("\n📱 WhatsApp Connection:")
        print(f"  Account ID: {whatsapp_conn.unipile_account_id}")
        
        # Initialize UnipileClient with correct params
        client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # Initialize resolver
        resolver = AttendeeResolver(client)
        
        print("\nFetching attendee names from UniPile...")
        # Fetch attendee names
        attendee_names = resolver.fetch_all_attendees_with_names(
            account_id=whatsapp_conn.unipile_account_id,
            channel_type='whatsapp'
        )
        
        print(f"Total attendee names fetched: {len(attendee_names)}")
        
        # Show some sample entries
        print("\nSample attendee entries (first 10):")
        for i, (key, name) in enumerate(list(attendee_names.items())[:10]):
            print(f"  {i+1}. '{key}' -> '{name}'")
        
        # Check what WhatsApp message senders we have
        print("\n📊 WhatsApp Message Senders (from metadata):")
        
        whatsapp_messages = Message.objects.filter(
            conversation__channel__channel_type='whatsapp'
        )[:10]
        
        unique_senders = set()
        for msg in whatsapp_messages:
            metadata = msg.metadata or {}
            unipile_data = metadata.get('unipile_data', {})
            sender_attendee_id = unipile_data.get('sender_attendee_id', '')
            if sender_attendee_id:
                unique_senders.add(sender_attendee_id)
        
        print(f"Found {len(unique_senders)} unique sender attendee IDs in messages")
        
        for sender_id in list(unique_senders)[:5]:
            print(f"\n  Sender attendee ID: '{sender_id}'")
            
            # Check if this ID is in our fetched names
            if sender_id in attendee_names:
                print(f"    ✅ Found in attendee_names: '{attendee_names[sender_id]}'")
            else:
                print(f"    ❌ NOT found in attendee_names")
                # Check for partial matches
                found_match = False
                for key in attendee_names:
                    if sender_id == key.split('@')[0] or key == f"{sender_id}@s.whatsapp.net":
                        print(f"      Possible match: '{key}' -> '{attendee_names[key]}'")
                        found_match = True
                        break
                if not found_match:
                    print(f"      No matches found")
        
        # Now check participant provider_ids
        print("\n📋 Existing Participants with provider_id:")
        participants = Participant.objects.filter(
            metadata__provider_id__isnull=False
        )[:3]
        
        for p in participants:
            provider_id = p.metadata.get('provider_id', '')
            print(f"\n  Participant {p.id}:")
            print(f"    Provider ID: '{provider_id}'")
            print(f"    Current name: '{p.name}' (empty: {not p.name})")
            
            # Check if this provider_id is in attendee_names
            if provider_id in attendee_names:
                print(f"    ✅ Would update name to: '{attendee_names[provider_id]}'")
            else:
                print(f"    ❌ No match in attendee_names")
    else:
        print("No WhatsApp connection found")
