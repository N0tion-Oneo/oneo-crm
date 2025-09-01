#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message, Conversation, Participant
from communications.record_communications.models import RecordCommunicationLink
from pipelines.models import Record
from django.db.models import Q

# Get tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

print("=" * 80)
print("CHECKING SAUL CHILCHIK'S EMAIL COMMUNICATIONS")
print("=" * 80)

with schema_context(tenant.schema_name):
    # Find Saul's record
    try:
        saul_record = Record.objects.get(id=66)
        print(f"\n✅ Found Saul's record: ID {saul_record.id}")
        print(f"   Data: {saul_record.data}")
    except Record.DoesNotExist:
        print("\n❌ Record 66 (Saul Chilchik) not found")
        sys.exit(1)

    # Check for email in field data
    emails = []
    if 'email' in saul_record.data:
        emails.append(saul_record.data['email'])
    if 'email_address' in saul_record.data:
        emails.append(saul_record.data['email_address'])
    if 'work_email' in saul_record.data:
        emails.append(saul_record.data['work_email'])
    if 'personal_email' in saul_record.data:
        emails.append(saul_record.data['personal_email'])

    print(f"\n📧 Saul's email addresses: {emails}")

    # Find participants with Saul's email
    print("\n" + "=" * 80)
    print("PARTICIPANTS:")
    print("=" * 80)

    for email in emails:
        participants = Participant.objects.filter(
            Q(email__iexact=email) | 
            Q(display_name__icontains='saul') |
            Q(display_name__icontains='chilchik')
        )
        
        for participant in participants:
            print(f"\n👤 Participant ID: {participant.id}")
            print(f"   Email: {participant.email}")
            print(f"   Name: {participant.display_name}")
            print(f"   Contact Record: {participant.contact_record_id}")
            print(f"   Conversation: {participant.conversation_id}")
            
            # Check if linked to Saul's record
            if participant.contact_record_id == 66:
                print(f"   ✅ Linked to Saul's record")
            else:
                print(f"   ⚠️ NOT linked to Saul's record")

    # Find messages from/to Saul
    print("\n" + "=" * 80)
    print("MESSAGES:")
    print("=" * 80)

    # Get recent timeframe
    recent = timezone.now() - timedelta(days=7)

    # Find messages through participants
    messages = Message.objects.filter(
        conversation__participants__email__in=emails
    ).filter(
        created_at__gte=recent
    ).distinct().order_by('-created_at')

    print(f"\nFound {messages.count()} messages in the last 7 days")

    for msg in messages[:10]:  # Show last 10
        print(f"\n📧 Message ID: {msg.id}")
        print(f"   Created: {msg.created_at}")
        print(f"   Direction: {msg.direction}")
        print(f"   Subject: {msg.metadata.get('subject', 'No subject')}")
        print(f"   External ID: {msg.external_message_id}")
        
        # Check participants
        participants = msg.conversation.participants.all()
        for p in participants:
            if p.email in emails:
                print(f"   👤 Saul as participant: {p.email} (Record: {p.contact_record_id})")

    # Check RecordCommunicationLinks
    print("\n" + "=" * 80)
    print("RECORD COMMUNICATION LINKS:")
    print("=" * 80)

    links = RecordCommunicationLink.objects.filter(record_id=66)
    print(f"\nFound {links.count()} communication links for Saul's record")

    for link in links[:10]:
        print(f"\n🔗 Link ID: {link.id}")
        print(f"   Conversation: {link.conversation_id}")
        print(f"   Participant: {link.participant_id}")
        print(f"   Created: {link.created_at}")
        print(f"   Match Type: {link.match_type}")
        print(f"   Created by sync: {link.created_by_sync}")
        
        # Check if conversation has recent messages
        recent_msgs = Message.objects.filter(
            conversation_id=link.conversation_id,
            created_at__gte=recent
        ).count()
        print(f"   Recent messages in conversation: {recent_msgs}")

    # Check today's messages specifically
    print("\n" + "=" * 80)
    print("TODAY'S MESSAGES:")
    print("=" * 80)

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_messages = Message.objects.filter(
        created_at__gte=today
    ).order_by('-created_at')

    print(f"\nTotal messages today: {today_messages.count()}")

    # Check if any are from/to Saul
    saul_today = 0
    for msg in today_messages:
        participants = msg.conversation.participants.all()
        for p in participants:
            if p.email in emails:
                saul_today += 1
                print(f"\n📧 Saul's message: {msg.id}")
                print(f"   Time: {msg.created_at}")
                print(f"   Subject: {msg.metadata.get('subject', 'No subject')}")
                break

    if saul_today == 0:
        print("\n⚠️ No messages from/to Saul found today")
        print("\nThis means the webhook is not receiving Saul's emails.")
        print("Possible reasons:")
        print("1. Webhook URL not configured in UniPile")
        print("2. UniPile cannot reach localhost (need ngrok/tunnel)")
        print("3. Saul's email account not syncing via webhook")