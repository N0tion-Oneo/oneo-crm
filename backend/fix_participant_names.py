#!/usr/bin/env python
"""
Fix participant names by extracting them from message metadata
"""
import os
import sys
import django
import re

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Participant, Message, Conversation
from django.db import transaction

def extract_phone_from_provider_id(provider_id):
    """Extract phone number from WhatsApp provider_id"""
    if '@s.whatsapp.net' in provider_id:
        return provider_id.replace('@s.whatsapp.net', '')
    return None

with schema_context('oneotalent'):
    print("=" * 60)
    print("FIXING PARTICIPANT NAMES AND PHONE NUMBERS")
    print("=" * 60)
    
    with transaction.atomic():
        # Fix WhatsApp participants
        print("\n📱 Fixing WhatsApp participants...")
        
        # Find all WhatsApp messages
        whatsapp_messages = Message.objects.filter(
            conversation__channel__channel_type='whatsapp'
        ).select_related('sender_participant')
        
        # Build a map of provider_id to names from message metadata
        provider_to_name = {}
        provider_to_phone = {}
        
        for msg in whatsapp_messages:
            metadata = msg.metadata or {}
            
            # Extract sender info from metadata
            sender_data = metadata.get('sender', {})
            if sender_data:
                provider_id = sender_data.get('provider_id', '')
                name = sender_data.get('name', '')
                phone = sender_data.get('phone', '')
                
                if provider_id and name:
                    # Store the best name we find
                    if provider_id not in provider_to_name or len(name) > len(provider_to_name.get(provider_id, '')):
                        provider_to_name[provider_id] = name
                
                if provider_id and phone:
                    provider_to_phone[provider_id] = phone
                elif provider_id:
                    # Extract phone from provider_id
                    extracted_phone = extract_phone_from_provider_id(provider_id)
                    if extracted_phone:
                        provider_to_phone[provider_id] = extracted_phone
        
        print(f"  Found {len(provider_to_name)} unique WhatsApp identities with names")
        
        # Update participants
        updated_count = 0
        for provider_id, name in provider_to_name.items():
            # Find participant by provider_id in metadata
            participant = Participant.objects.filter(
                metadata__provider_id=provider_id
            ).first()
            
            if participant:
                phone = provider_to_phone.get(provider_id, '')
                
                # Update name if better
                if name and (not participant.name or len(name) > len(participant.name)):
                    print(f"  Updating {participant.id}: '{participant.name}' -> '{name}'")
                    participant.name = name
                    updated_count += 1
                
                # Update phone if needed
                if phone and not participant.phone:
                    participant.phone = phone
                    print(f"    Also set phone: {phone}")
                
                participant.save()
        
        print(f"  Updated {updated_count} WhatsApp participants")
        
        # Fix LinkedIn participants
        print("\n💼 Fixing LinkedIn participants...")
        
        linkedin_messages = Message.objects.filter(
            conversation__channel__channel_type='linkedin'
        ).select_related('sender_participant')
        
        linkedin_provider_to_name = {}
        
        for msg in linkedin_messages:
            metadata = msg.metadata or {}
            
            # Extract sender info from metadata
            sender_data = metadata.get('sender', {})
            if sender_data:
                provider_id = sender_data.get('provider_id', '')
                name = sender_data.get('name', '')
                
                if provider_id and name:
                    if provider_id not in linkedin_provider_to_name or len(name) > len(linkedin_provider_to_name.get(provider_id, '')):
                        linkedin_provider_to_name[provider_id] = name
        
        print(f"  Found {len(linkedin_provider_to_name)} unique LinkedIn identities with names")
        
        # Update LinkedIn participants
        linkedin_updated = 0
        for provider_id, name in linkedin_provider_to_name.items():
            participant = Participant.objects.filter(
                metadata__provider_id=provider_id
            ).first()
            
            if participant:
                if name and (not participant.name or len(name) > len(participant.name)):
                    print(f"  Updating {participant.id}: '{participant.name}' -> '{name}'")
                    participant.name = name
                    linkedin_updated += 1
                    participant.save()
        
        print(f"  Updated {linkedin_updated} LinkedIn participants")
        
        # Create missing participants with correct phone numbers
        print("\n🔧 Creating missing participants with correct data...")
        
        # Check for WhatsApp messages without proper sender participants
        messages_without_participants = Message.objects.filter(
            conversation__channel__channel_type='whatsapp',
            sender_participant__isnull=True
        )
        
        print(f"  Found {messages_without_participants.count()} WhatsApp messages without sender participants")
        
        for msg in messages_without_participants[:10]:  # Limit to first 10 for safety
            metadata = msg.metadata or {}
            sender_data = metadata.get('sender', {})
            
            if sender_data:
                provider_id = sender_data.get('provider_id', '')
                name = sender_data.get('name', '')
                phone = sender_data.get('phone', '') or extract_phone_from_provider_id(provider_id)
                
                if phone:
                    # Create or get participant with phone
                    participant, created = Participant.objects.get_or_create(
                        phone=phone,
                        defaults={
                            'name': name or '',
                            'metadata': {'provider_id': provider_id}
                        }
                    )
                    
                    if created:
                        print(f"  Created participant for phone {phone} with name '{name}'")
                    
                    # Link message to participant
                    msg.sender_participant = participant
                    msg.save(update_fields=['sender_participant'])
        
        print("\n✅ Fix complete!")
        
        # Show updated stats
        print("\n📊 Updated Statistics:")
        whatsapp_with_names = Participant.objects.filter(
            metadata__provider_id__isnull=False,
            name__isnull=False
        ).exclude(name='').count()
        
        linkedin_with_names = Participant.objects.filter(
            linkedin_member_urn__isnull=False,
            name__isnull=False
        ).exclude(name='').count()
        
        print(f"  WhatsApp participants with names: {whatsapp_with_names}")
        print(f"  LinkedIn participants with names: {linkedin_with_names}")
