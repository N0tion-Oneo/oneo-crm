#!/usr/bin/env python
"""
Test INBOUND email FROM Vanessa (who has a contact) TO the Gmail account
This should be stored because Vanessa has a contact record
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
from communications.models import UserChannelConnection, Message

print("=" * 80)
print("TEST INBOUND EMAIL FROM VANESSA")
print("=" * 80)

# Get Gmail account ID
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
    print(f"   Account user: {gmail_user_email}")

# Create webhook payload for INBOUND email FROM Vanessa
test_webhook = {
    "event": "mail_received",
    "type": "mail_received",
    "account_id": account_id,
    "date": datetime.utcnow().isoformat() + "Z",
    "from": {
        "email": "vanessa.c.brown86@gmail.com",  # Vanessa has a contact!
        "name": "Vanessa Brown"
    },
    "to": [{
        "email": gmail_user_email,  # TO the connected account
        "name": "Josh"
    }],
    "subject": f"Email FROM Vanessa - {datetime.now().strftime('%H:%M:%S')}",
    "body": {
        "text": "Hi Josh, this is Vanessa. Testing the email system.",
        "html": "<p>Hi Josh, this is Vanessa. Testing the email system.</p>"
    },
    "message_id": f"inbound_vanessa_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "thread_id": f"vanessa_inbound_{datetime.now().strftime('%Y%m%d')}",
    "folder": "INBOX",
    "labels": ["INBOX"],
    "attachments": []
}

# Send webhook
webhook_url = "http://localhost:8000/webhooks/unipile/"

print(f"\n📮 Sending test webhook...")
print(f"   From: {test_webhook['from']['email']} (HAS CONTACT)")
print(f"   To: {test_webhook['to'][0]['email']}")
print(f"   Subject: {test_webhook['subject']}")

try:
    response = requests.post(
        webhook_url,
        json=test_webhook,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"\n📨 Response Status: {response.status_code}")
    
    # Always try to get response data
    try:
        response_data = response.json()
    except:
        response_data = {"raw_text": response.text}
    
    if response.status_code == 200:
        result = response_data.get('result', {})
        
        print(f"✅ Webhook processed successfully!")
        
        # Check storage decision
        storage_decision = result.get('storage_decision', {})
        if storage_decision.get('should_store'):
            print(f"\n🎉 MESSAGE WAS STORED!")
            
            # Check if message exists in database
            with schema_context('oneotalent'):
                message = Message.objects.filter(
                    external_message_id=test_webhook['message_id']
                ).first()
                
                if message:
                    print(f"\n✅ Message confirmed in database:")
                    print(f"   Message ID: {message.id}")
                    print(f"   Conversation: {message.conversation.subject}")
                    print(f"   Direction: {message.direction}")
                    print(f"   From: {message.sender_participant.email if message.sender_participant else 'Unknown'}")
                    print(f"   Created: {message.created_at}")
                else:
                    print("\n⚠️ Message marked as stored but not found in DB yet")
        else:
            print(f"\n❌ Message NOT stored: {storage_decision.get('reason')}")
            
        # Show participant info
        participants = result.get('participants', [])
        print(f"\n👥 Participants found: {len(participants)}")
        for p in participants:
            print(f"   - {p.get('email')}")
            print(f"     Has contact: {p.get('has_contact')}")
            if p.get('has_contact'):
                print(f"     ✅ Contact ID: {p.get('contact_id')}")
                print(f"     Confidence: {p.get('confidence')}%")
    else:
        print(f"\n❌ Webhook failed with status {response.status_code}")
        print(f"   Error: {response_data.get('error', response_data)}")
                
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 80)