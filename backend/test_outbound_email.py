#!/usr/bin/env python
"""
Test OUTBOUND email to Vanessa with proper mail_sent webhook
"""
import os
import sys
import django
import requests
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import UserChannelConnection, Message, Participant

print("=" * 80)
print("TEST OUTBOUND EMAIL TO VANESSA")
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

# Create outbound email webhook (mail_sent event)
outbound_webhook = {
    "event": "mail_sent",  # This is what Gmail sends for outbound
    "type": "mail_sent",
    "account_id": account_id,
    "date": datetime.utcnow().isoformat() + "Z",
    "from": {
        "email": gmail_user_email,  # FROM the connected account
        "name": "Josh"
    },
    "to": [{
        "email": vanessa_email,  # TO Vanessa who has a contact
        "name": "Vanessa Brown"
    }],
    "subject": f"test outbound email",  # Matching your actual subject
    "body": {
        "text": "This is a test outbound email to Vanessa who has a contact record.",
        "html": "<p>This is a test outbound email to Vanessa who has a contact record.</p>"
    },
    "message_id": f"<CAPqYiuLMuRw1BJ-bNTp5rdGgxrqo4xSgMuvM46zak26LO9wpJQ@mail.gmail.com>",
    "thread_id": f"thread_{datetime.now().strftime('%Y%m%d')}",
    "folder": "SENT",
    "labels": ["SENT"],
    "attachments": []
}

print(f"\n📮 Sending outbound email webhook...")
print(f"   From: {outbound_webhook['from']['email']} ({outbound_webhook['from']['name']})")
print(f"   To: {outbound_webhook['to'][0]['email']} ({outbound_webhook['to'][0]['name']})")
print(f"   Subject: {outbound_webhook['subject']}")
print(f"   Message ID: {outbound_webhook['message_id']}")

try:
    response = requests.post(
        webhook_url,
        json=outbound_webhook,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"\n📨 Response Status: {response.status_code}")
    
    # Get response data
    try:
        response_data = response.json()
    except:
        response_data = {"raw_text": response.text}
    
    if response.status_code == 200:
        result = response_data.get('result', {})
        
        # Check if message was created or updated
        if result.get('success'):
            action = result.get('action', 'created')
            print(f"✅ OUTBOUND EMAIL {action.upper()}!")
            
            # Check storage decision
            storage_decision = result.get('storage_decision', {})
            if storage_decision.get('should_store'):
                print(f"   Storage: Message was stored")
                print(f"   Reason: {storage_decision.get('reasoning', 'N/A')}")
            elif storage_decision:
                print(f"   Storage: {storage_decision.get('should_store')}")
                print(f"   Reason: {storage_decision.get('reason', 'N/A')}")
            
            # Check participants
            participants = result.get('participants', [])
            if participants:
                print(f"\n👥 Participants found: {len(participants)}")
                for p in participants:
                    print(f"   - {p.get('email')}")
                    if p.get('has_contact'):
                        print(f"     ✅ Has contact: ID {p.get('contact_id')}")
                        print(f"     Confidence: {p.get('confidence')}%")
                    else:
                        print(f"     ❌ No contact found")
            
            # Check message in database
            with schema_context('oneotalent'):
                message = Message.objects.filter(
                    external_message_id=outbound_webhook['message_id']
                ).first()
                
                if message:
                    print(f"\n✅ Message found in database:")
                    print(f"   Message ID: {message.id}")
                    print(f"   Direction: {message.direction}")
                    print(f"   Status: {message.status}")
                    print(f"   Subject: {message.subject}")
                    print(f"   Contact Email: {message.contact_email}")
                    
                    # Check conversation
                    if message.conversation:
                        print(f"\n📚 Conversation:")
                        print(f"   ID: {message.conversation.id}")
                        print(f"   Subject: {message.conversation.subject}")
                        print(f"   Channel: {message.conversation.channel.channel_type}")
                        
                        # Check conversation participants
                        from communications.models import ConversationParticipant
                        conv_participants = ConversationParticipant.objects.filter(
                            conversation=message.conversation
                        )
                        print(f"   Participants: {conv_participants.count()}")
                        for cp in conv_participants:
                            participant = cp.participant
                            print(f"     - {participant.email or participant.display_name}")
                            if participant.contact_record:
                                print(f"       ✅ Linked to contact ID: {participant.contact_record.id}")
                else:
                    print(f"\n⚠️ Message not found in database yet")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    else:
        print(f"❌ Webhook failed with status {response.status_code}")
        print(f"   Error: {response_data.get('error', response_data)}")
                
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 80)