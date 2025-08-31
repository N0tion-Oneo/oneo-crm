#!/usr/bin/env python
"""
Test message API to see what data is being returned
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message
from communications.record_communications.serializers import RecordMessageSerializer

# Use oneotalent schema
with schema_context('oneotalent'):
    # Get first few messages
    messages = Message.objects.select_related('channel', 'conversation', 'sender_participant').order_by('-created_at')[:3]
    
    for message in messages:
        print(f"\n{'='*60}")
        print(f"Message ID: {message.id}")
        print(f"Direction: {message.direction}")
        print(f"Channel: {message.channel.channel_type if message.channel else 'None'}")
        print(f"Content: {message.content[:100]}...")
        
        # Serialize the message
        serializer = RecordMessageSerializer(message)
        data = serializer.data
        
        print(f"\nSerialized data:")
        print(f"  sender_name: {data.get('sender_name')}")
        print(f"  contact_name: {data.get('contact_name')}")
        print(f"  metadata.account_owner_name: {data.get('metadata', {}).get('account_owner_name')}")
        print(f"  metadata.contact_name: {data.get('metadata', {}).get('contact_name')}")
        print(f"  metadata.from: {data.get('metadata', {}).get('from')}")
        print(f"  metadata.to: {data.get('metadata', {}).get('to')}")