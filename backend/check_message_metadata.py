#!/usr/bin/env python
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message

with schema_context('oneotalent'):
    # Check what's in message metadata
    whatsapp_msg = Message.objects.filter(
        conversation__channel__channel_type='whatsapp'
    ).first()
    
    if whatsapp_msg:
        print('WhatsApp Message Metadata:')
        print(json.dumps(whatsapp_msg.metadata, indent=2))
        if whatsapp_msg.sender_participant:
            print(f"\nSender Participant:")
            print(f"  ID: {whatsapp_msg.sender_participant.id}")
            print(f"  Name: '{whatsapp_msg.sender_participant.name}'")
            print(f"  Phone: {whatsapp_msg.sender_participant.phone}")
    
    linkedin_msg = Message.objects.filter(
        conversation__channel__channel_type='linkedin'  
    ).first()
    
    if linkedin_msg:
        print('\n' + '='*50)
        print('LinkedIn Message Metadata:')
        print(json.dumps(linkedin_msg.metadata, indent=2))
        if linkedin_msg.sender_participant:
            print(f"\nSender Participant:")
            print(f"  ID: {linkedin_msg.sender_participant.id}")
            print(f"  Name: '{linkedin_msg.sender_participant.name}'")
            print(f"  URN: {linkedin_msg.sender_participant.linkedin_member_urn}")
