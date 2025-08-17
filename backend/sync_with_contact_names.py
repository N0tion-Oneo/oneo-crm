#!/usr/bin/env python3
"""
Enhanced message sync that fetches real contact names from UniPile attendees
"""

import os
import django
import requests
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import UserChannelConnection, Channel, Conversation, Message
from django.utils import timezone

def fetch_contact_name(attendee_id, unipile_settings, headers, contact_cache):
    """Fetch contact name from UniPile attendees API with caching"""
    
    # Check cache first
    if attendee_id in contact_cache:
        return contact_cache[attendee_id]
    
    try:
        attendee_url = f"{unipile_settings.dsn}/api/v1/chat_attendees/{attendee_id}"
        response = requests.get(attendee_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            attendee_data = response.json()
            name = attendee_data.get('name', 'Unknown')
            
            # Cache the result
            contact_cache[attendee_id] = name
            return name
        else:
            print(f"  ⚠️  Failed to fetch attendee {attendee_id}: {response.status_code}")
            return 'Unknown'
            
    except Exception as e:
        print(f"  ❌ Error fetching attendee {attendee_id}: {e}")
        return 'Unknown'

def main():
    print("🔄 ENHANCED MESSAGE SYNC WITH CONTACT NAMES")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        # Get existing WhatsApp messages that need contact name updates
        whatsapp_messages = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).exclude(
            metadata__sender_attendee_id__isnull=True
        )
        
        print(f"Found {whatsapp_messages.count()} WhatsApp messages to update")
        
        if not whatsapp_messages.exists():
            print("No WhatsApp messages found to update")
            return
        
        # UniPile API setup
        unipile_settings = settings.UNIPILE_SETTINGS
        headers = {
            'X-API-KEY': unipile_settings.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Contact name cache to avoid duplicate API calls
        contact_cache = {}
        updated_count = 0
        
        print(f"\n📝 UPDATING CONTACT NAMES")
        print("-" * 40)
        
        for msg in whatsapp_messages:
            attendee_id = msg.metadata.get('sender_attendee_id')
            if not attendee_id:
                continue
            
            # Fetch real contact name
            contact_name = fetch_contact_name(attendee_id, unipile_settings, headers, contact_cache)
            
            # Update the message's contact_email field with real name when possible
            old_contact = msg.contact_email
            
            # If we got a real name (not a phone number), update the message
            if contact_name and contact_name != 'Unknown' and '@s.whatsapp.net' not in contact_name:
                # Store both name and phone for WhatsApp contacts
                phone_number = old_contact.replace('@s.whatsapp.net', '') if '@s.whatsapp.net' in old_contact else old_contact
                
                # Update message metadata to include real contact name
                if 'contact_name' not in msg.metadata:
                    msg.metadata['contact_name'] = contact_name
                    msg.metadata['contact_phone'] = phone_number
                    msg.save(update_fields=['metadata'])
                    
                    print(f"  ✅ {old_contact[:15]}... → {contact_name}")
                    updated_count += 1
                else:
                    print(f"  ℹ️  Already has name: {msg.metadata['contact_name']}")
            else:
                print(f"  ⚠️  No real name for {old_contact[:15]}... (got: {contact_name})")
        
        print(f"\n📊 RESULTS")
        print("-" * 40)
        print(f"Messages processed: {whatsapp_messages.count()}")
        print(f"Names updated: {updated_count}")
        print(f"Unique contacts cached: {len(contact_cache)}")
        
        # Show the contact cache
        print(f"\n📇 CONTACT NAMES FOUND")
        print("-" * 40)
        for attendee_id, name in contact_cache.items():
            if '@s.whatsapp.net' not in name:
                print(f"  ✅ {name} (ID: {attendee_id[:10]}...)")
            else:
                print(f"  📱 {name} (ID: {attendee_id[:10]}...)")

if __name__ == '__main__':
    main()