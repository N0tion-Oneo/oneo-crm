#!/usr/bin/env python
"""
Test why participant names aren't being updated
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Participant, Message

def test_name_update():
    with schema_context('oneotalent'):
        # Test the participant cache building logic
        from communications.record_communications.storage.message_store import MessageStore
        
        store = MessageStore()
        
        # Get some sample messages
        messages = Message.objects.filter(
            metadata__from__email='saul@oneodigital.com'
        )[:10]
        
        # Convert to the format expected by _build_participant_cache
        messages_data = []
        for msg in messages:
            messages_data.append({
                'metadata': msg.metadata,
                'sender': None,  # Not enriched
                'channel_type': 'email'
            })
        
        print(f"Testing with {len(messages_data)} messages")
        
        # Build participant cache
        participant_cache = store._build_participant_cache(messages_data, attendee_names={})
        
        # Check what was found
        print(f"\nParticipant cache size: {len(participant_cache)}")
        
        # Check if Saul was found and what name was extracted
        saul_key = "email:saul@oneodigital.com"
        if saul_key in participant_cache:
            saul = participant_cache[saul_key]
            print(f"\nSaul found in cache:")
            print(f"  Current name: '{saul.name}'")
            print(f"  Email: {saul.email}")
        
        # Check what the extraction logic found
        email_to_name = {}
        for msg_data in messages_data:
            metadata = msg_data.get('metadata', {})
            from_data = metadata.get('from', {})
            if isinstance(from_data, dict):
                email = from_data.get('email', '').lower()
                name = from_data.get('name', '')
                print(f"\nFrom message: email='{email}', name='{name}'")
                if email and name:
                    if email not in email_to_name or len(name) > len(email_to_name.get(email, '')):
                        email_to_name[email] = name
        
        print(f"\nExtracted email_to_name mapping:")
        for email, name in email_to_name.items():
            print(f"  {email} -> '{name}'")

if __name__ == '__main__':
    test_name_update()