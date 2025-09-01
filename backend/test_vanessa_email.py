#!/usr/bin/env python
"""
Test email webhook to Vanessa (who now has a linked contact)
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
print("TEST EMAIL TO VANESSA")
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
    print(f"✅ Using Gmail account: {account_id}")

# Create webhook payload for email TO Vanessa
test_webhook = {
    "event": "mail_received",
    "type": "mail_received", 
    "account_id": account_id,
    "date": datetime.utcnow().isoformat() + "Z",
    "from": {
        "email": "josh@oneo.africa",  # Your email
        "name": "Josh from Oneo"
    },
    "to": [{
        "email": "vanessa.c.brown86@gmail.com",
        "name": "Vanessa Brown"
    }],
    "subject": f"Test Email to Vanessa - {datetime.now().strftime('%H:%M:%S')}",
    "body": {
        "text": "Hi Vanessa, this is a test email to verify the webhook system is working correctly.",
        "html": "<p>Hi Vanessa, this is a test email to verify the webhook system is working correctly.</p>"
    },
    "message_id": f"vanessa_test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "thread_id": f"vanessa_thread_{datetime.now().strftime('%Y%m%d')}",
    "folder": "SENT",
    "labels": ["SENT"],
    "attachments": []
}

# Send webhook
webhook_url = "http://localhost:8000/webhooks/unipile/"

print(f"\n📮 Sending test webhook...")
print(f"   From: {test_webhook['from']['email']}")
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
    
    if response.status_code == 200:
        response_data = response.json()
        result = response_data.get('result', {})
        
        print(f"✅ Webhook processed successfully!")
        
        # Check storage decision
        storage_decision = result.get('storage_decision', {})
        if storage_decision.get('should_store'):
            print(f"✅ MESSAGE WAS STORED!")
            
            # Check if message exists in database
            with schema_context('oneotalent'):
                message = Message.objects.filter(
                    external_message_id=test_webhook['message_id']
                ).first()
                
                if message:
                    print(f"\n🎉 SUCCESS! Message found in database:")
                    print(f"   Message ID: {message.id}")
                    print(f"   Conversation: {message.conversation.subject}")
                    print(f"   Direction: {message.direction}")
                    print(f"   Created: {message.created_at}")
                else:
                    print("\n⚠️ Message marked as stored but not found in DB yet")
        else:
            print(f"❌ Message NOT stored: {storage_decision.get('reason')}")
            
        # Show participant info
        participants = result.get('participants', [])
        print(f"\n👥 Participants:")
        for p in participants:
            print(f"   - {p.get('email')}")
            print(f"     Has contact: {p.get('has_contact')}")
            if p.get('has_contact'):
                print(f"     Contact ID: {p.get('contact_id')}")
                print(f"     Confidence: {p.get('confidence')}%")
                
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 80)