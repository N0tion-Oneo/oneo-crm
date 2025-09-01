#!/usr/bin/env python
"""
Test webhook endpoint directly to see if it's working
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
from communications.models import UserChannelConnection

print("=" * 80)
print("WEBHOOK ENDPOINT TEST")
print("=" * 80)

# Get the Gmail account ID
with schema_context('oneotalent'):
    gmail_connection = UserChannelConnection.objects.filter(
        channel_type='gmail',
        is_active=True
    ).first()
    
    if not gmail_connection:
        print("❌ No Gmail connection found")
        sys.exit(1)
    
    account_id = gmail_connection.unipile_account_id
    print(f"✅ Found Gmail account: {account_id}")

# Create a test webhook payload
test_webhook = {
    "event": "mail_received",
    "type": "mail_received",
    "account_id": account_id,
    "date": datetime.utcnow().isoformat() + "Z",
    "from": {
        "email": "test@example.com",
        "name": "Test Sender"
    },
    "to": [{
        "email": "recipient@oneotalent.com",
        "name": "Recipient"
    }],
    "subject": f"Direct Webhook Test - {datetime.now().strftime('%H:%M:%S')}",
    "body": {
        "text": "This is a direct webhook test to verify the endpoint is working.",
        "html": "<p>This is a direct webhook test to verify the endpoint is working.</p>"
    },
    "message_id": f"direct_test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "thread_id": f"thread_{datetime.now().strftime('%Y%m%d')}",
    "folder": "INBOX",
    "labels": ["INBOX"],
    "attachments": []
}

# Test the webhook endpoint (on public schema)
webhook_url = "http://localhost:8000/webhooks/unipile/"

print(f"\n📮 Sending test webhook to: {webhook_url}")
print(f"   Event type: mail_received")
print(f"   Subject: {test_webhook['subject']}")

try:
    response = requests.post(
        webhook_url,
        json=test_webhook,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"\n📨 Response Status: {response.status_code}")
    print(f"📝 Response Body:")
    
    try:
        response_data = response.json()
        print(json.dumps(response_data, indent=2))
        
        if response_data.get('success'):
            print("\n✅ Webhook processed successfully!")
            
            # Check if message was stored
            result = response_data.get('result', {})
            storage_decision = result.get('storage_decision', {})
            
            if storage_decision.get('should_store'):
                print("✅ Message was stored")
            else:
                print(f"⚠️ Message not stored: {storage_decision.get('reason')}")
                
                # Show participant info
                participants = result.get('participants', [])
                print(f"\n👥 Participants found: {len(participants)}")
                for p in participants:
                    print(f"   - {p.get('email')} (has contact: {p.get('has_contact')})")
        else:
            print(f"\n❌ Webhook failed: {response_data.get('error')}")
            
    except json.JSONDecodeError:
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("\n❌ Connection Error: Could not connect to webhook endpoint")
    print("   Make sure the Django server is running on localhost:8000")
    
except requests.exceptions.Timeout:
    print("\n❌ Timeout: Webhook endpoint took too long to respond")
    
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 80)