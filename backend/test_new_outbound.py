#!/usr/bin/env python
"""
Test NEW OUTBOUND email to Vanessa with proper mail_sent webhook
"""
import os
import sys
import django
import requests
import json
from datetime import datetime
import uuid

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import UserChannelConnection, Message, Participant

print("=" * 80)
print("TEST NEW OUTBOUND EMAIL TO VANESSA")
print("=" * 80)

# Get Gmail account ID and user email
with schema_context('oneotalent'):
    gmail_connection = UserChannelConnection.objects.filter(
        channel_type='gmail',
        is_active=True
    ).first()
    
    if not gmail_connection:
        print("❌ No Gmail connection found")
        sys.exit(1)
    
    account_id = gmail_connection.unipile_account_id
    gmail_user_email = gmail_connection.user.email  # josh@oneodigital.com
    print(f"✅ Using Gmail account: {account_id}")
    print(f"   Connected user email: {gmail_user_email}")
    
    # Check Vanessa's participant
    vanessa_email = "vanessa.c.brown86@gmail.com"
    vanessa_participant = Participant.objects.filter(
        email=vanessa_email
    ).first()
    
    if vanessa_participant and vanessa_participant.contact_record:
        print(f"✅ Vanessa has contact: Record ID {vanessa_participant.contact_record.id}")
    else:
        print(f"⚠️ Vanessa doesn't have a contact linked")

webhook_url = "http://localhost:8000/webhooks/unipile/"

# Generate unique IDs for new message
message_id = f"<test-{uuid.uuid4()}@mail.gmail.com>"
thread_id = f"thread-{uuid.uuid4().hex[:16]}"
timestamp = datetime.now().isoformat()

# Simulate outbound email webhook
webhook_data = {
    "event": "mail_sent",  # Event type for outbound
    "account_id": account_id,
    "provider": "gmail",
    "webhook_type": "mail_sent",
    "message_id": message_id,
    "thread_id": thread_id,
    "id": message_id,
    "subject": f"Test email at {datetime.now().strftime('%H:%M:%S')}",
    "content": f"This is a test email sent at {timestamp}",
    "html_content": f"<p>This is a test email sent at {timestamp}</p>",
    "date": timestamp,
    "from_attendee": {
        "identifier": gmail_user_email,
        "display_name": "Josh",
        "email": gmail_user_email,
        "name": "Josh"
    },
    "to_attendees": [
        {
            "identifier": vanessa_email,
            "display_name": "Vanessa Brown",
            "email": vanessa_email,
            "name": "Vanessa Brown"
        }
    ],
    "cc_attendees": [],
    "bcc_attendees": [],
    "attachments": [],
    "labels": ["SENT"],
    "folder": "SENT"
}

print(f"\n📮 Sending NEW outbound email webhook...")
print(f"   From: {gmail_user_email} (Josh)")
print(f"   To: {vanessa_email} (Vanessa Brown)")
print(f"   Subject: {webhook_data['subject']}")
print(f"   Message ID: {message_id}")

# Send webhook
response = requests.post(webhook_url, json=webhook_data)

print(f"\n📨 Response Status: {response.status_code}")

if response.status_code == 200:
    response_data = response.json()
    if response_data.get('success'):
        print("✅ OUTBOUND EMAIL CREATED!")
        
        # Check if message was created
        with schema_context('oneotalent'):
            message = Message.objects.filter(
                external_message_id=message_id
            ).first()
            
            if message:
                print(f"\n✅ Message found in database:")
                print(f"   Message ID: {message.id}")
                print(f"   Direction: {message.direction}")
                print(f"   Status: {message.status}")
                print(f"   Subject: {message.subject}")
                print(f"   Contact Email: {message.contact_email}")
                print(f"   Contact Record: {message.contact_record_id}")
                
                if message.contact_record_id:
                    print(f"   ✅ LINKED TO CONTACT RECORD: {message.contact_record_id}")
                else:
                    print(f"   ❌ NO CONTACT RECORD LINKED")
                
                # Check conversation participants
                if message.conversation:
                    print(f"\n📚 Conversation:")
                    print(f"   ID: {message.conversation.id}")
                    print(f"   Subject: {message.conversation.subject}")
                    print(f"   Channel: {message.conversation.channel.channel_type}")
                    
                    participants = message.conversation.participants.all()
                    print(f"   Participants: {participants.count()}")
                    for p in participants:
                        print(f"     - {p.participant.email}")
                        if p.participant.contact_record:
                            print(f"       ✅ Linked to contact ID: {p.participant.contact_record.id}")
            else:
                print("❌ Message not found in database")
    else:
        print(f"❌ Webhook processing failed: {response_data}")
else:
    print(f"❌ HTTP Error: {response.text}")

print("=" * 80)