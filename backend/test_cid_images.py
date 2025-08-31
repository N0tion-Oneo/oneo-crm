#!/usr/bin/env python
"""Test script to verify CID image handling in emails"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.models import Message
from django_tenants.utils import schema_context
import re

# Check messages with CID images
with schema_context('oneotalent'):
    messages = Message.objects.filter(
        content__icontains='cid:'
    ).order_by('-created_at')[:3]
    
    print(f"Found {messages.count()} messages with CID images\n")
    
    for msg in messages:
        print(f"Message ID: {msg.id}")
        print(f"Subject: {msg.subject or 'No subject'}")
        print(f"External ID: {msg.external_message_id}")
        
        # Extract CID references
        cid_matches = re.findall(r'cid:([^"\'>\s]+)', msg.content, re.IGNORECASE)
        if cid_matches:
            print(f"CID images found: {len(cid_matches)}")
            for cid in cid_matches[:3]:
                print(f"  - cid:{cid}")
                # This is what the frontend will transform to:
                print(f"    -> /api/v1/communications/messages/{msg.id}/attachments/{cid}/download/")
        
        # Check if message has attachment metadata
        if msg.metadata:
            attachments = msg.metadata.get('attachments', [])
            if attachments:
                print(f"Attachment metadata: {len(attachments)} attachments")
                for att in attachments[:3]:
                    print(f"  - {att.get('filename', 'Unknown')}: {att.get('id', 'No ID')}")
        
        print("-" * 50)