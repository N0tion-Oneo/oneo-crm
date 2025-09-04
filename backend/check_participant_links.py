#!/usr/bin/env python
"""
Check participant links after sync
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Participant, Conversation, Message
from pipelines.models import Record

# Use oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    print(f"🏢 Checking in tenant: {tenant.name} ({tenant.schema_name})")
    
    # Get the test record
    record = Record.objects.get(id=93)
    print(f"\n📄 Record: {record.id}")
    print(f"   Data: {record.data}")
    
    # Check participants linked to this record
    linked_participants = Participant.objects.filter(contact_record=record)
    print(f"\n👥 Participants linked to record {record.id}: {linked_participants.count()}")
    for p in linked_participants:
        print(f"   - {p.name or 'Unknown'} ({p.email or p.phone or 'No contact info'})")
    
    # Check all participants with the record's email
    record_email = record.data.get('email', 'cowanr@credos.co.uk')
    email_participants = Participant.objects.filter(email=record_email)
    print(f"\n📧 All participants with email {record_email}: {email_participants.count()}")
    for p in email_participants:
        print(f"   - {p.name or 'Unknown'} (Linked to record: {p.contact_record_id or 'None'})")
    
    # Check conversations
    print(f"\n💬 Conversations and Messages:")
    conversations = Conversation.objects.filter(
        messages__metadata__contains={'record_id': record.id}
    ).distinct()
    
    if conversations.exists():
        print(f"   Found {conversations.count()} conversations linked via messages")
    else:
        # Try another approach - get all conversations with participants
        all_conversations = Conversation.objects.all().order_by('-updated_at')[:10]
        print(f"   Recent conversations: {all_conversations.count()}")
        for conv in all_conversations:
            participants = Participant.objects.filter(
                conversation_memberships__conversation=conv
            ).distinct()
            linked = participants.filter(contact_record=record).exists()
            if linked:
                print(f"   ✅ {conv.subject[:50]} - Has linked participant")
            else:
                print(f"   ❌ {conv.subject[:50]} - No linked participants")
    
    # Check total messages
    total_messages = Message.objects.count()
    print(f"\n📊 Total messages in system: {total_messages}")