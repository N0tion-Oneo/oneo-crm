#!/usr/bin/env python
"""
Complete test of email webhook handling with both formats
Tests both inbound and outbound emails with UniPile format
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
print("COMPLETE EMAIL WEBHOOK TEST")
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
    
    # Check if Vanessa has a participant linked to contact
    vanessa_email = "vanessa.c.brown86@gmail.com"
    vanessa_participant = Participant.objects.filter(
        email=vanessa_email
    ).first()
    
    if vanessa_participant:
        print(f"✅ Vanessa's participant exists: {vanessa_participant.id}")
        print(f"   Has contact: {'Yes' if vanessa_participant.contact_record else 'No'}")
    else:
        print(f"⚠️ No participant for {vanessa_email}")

webhook_url = "http://localhost:8000/webhooks/unipile/"

# Test 1: INBOUND email with UniPile format (from/to fields)
print("\n" + "=" * 60)
print("TEST 1: INBOUND EMAIL (UniPile format)")
print("=" * 60)

inbound_webhook = {
    "event": "mail_received",
    "type": "mail_received",
    "account_id": account_id,
    "date": datetime.utcnow().isoformat() + "Z",
    "from": {
        "email": vanessa_email,
        "name": "Vanessa Brown"
    },
    "to": [{
        "email": gmail_user_email,
        "name": "Josh"
    }],
    "subject": f"UniPile Format Test - Inbound - {datetime.now().strftime('%H:%M:%S')}",
    "body": {
        "text": "Testing inbound email with UniPile format (from/to fields)",
        "html": "<p>Testing inbound email with UniPile format (from/to fields)</p>"
    },
    "message_id": f"unipile_inbound_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "thread_id": f"unipile_thread_{datetime.now().strftime('%Y%m%d')}",
    "folder": "INBOX",
    "labels": ["INBOX"],
    "attachments": []
}

print(f"📮 Sending inbound test...")
print(f"   From: {inbound_webhook['from']['email']}")
print(f"   To: {inbound_webhook['to'][0]['email']}")
print(f"   Subject: {inbound_webhook['subject']}")

try:
    response = requests.post(
        webhook_url,
        json=inbound_webhook,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"📨 Response Status: {response.status_code}")
    
    # Get response data for error details
    try:
        response_data = response.json()
    except:
        response_data = {"raw_text": response.text}
    
    if response.status_code == 200:
        result = response_data.get('result', {})
        if not result:
            print(f"   Full response: {response_data}")
        storage_decision = result.get('storage_decision', {})
        
        if storage_decision.get('should_store'):
            print(f"✅ INBOUND MESSAGE STORED!")
            
            # Check message in DB
            with schema_context('oneotalent'):
                message = Message.objects.filter(
                    external_message_id=inbound_webhook['message_id']
                ).first()
                
                if message:
                    print(f"   Message ID: {message.id}")
                    print(f"   Direction: {message.direction}")
                    print(f"   From: {message.sender_participant.email if message.sender_participant else 'Unknown'}")
        else:
            print(f"❌ Message NOT stored: {storage_decision.get('reason')}")
            print(f"   Full storage decision: {storage_decision}")
    else:
        print(f"❌ Webhook failed: {response.status_code}")
        print(f"   Error: {response_data.get('error', response_data)}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: OUTBOUND email with UniPile format
print("\n" + "=" * 60)
print("TEST 2: OUTBOUND EMAIL (UniPile format)")
print("=" * 60)

outbound_webhook = {
    "event": "mail_sent",
    "type": "mail_sent", 
    "account_id": account_id,
    "date": datetime.utcnow().isoformat() + "Z",
    "from": {
        "email": gmail_user_email,  # FROM the connected account
        "name": "Josh"
    },
    "to": [{
        "email": vanessa_email,  # TO Vanessa
        "name": "Vanessa Brown"
    }],
    "subject": f"UniPile Format Test - Outbound - {datetime.now().strftime('%H:%M:%S')}",
    "body": {
        "text": "Testing outbound email with UniPile format (from/to fields)",
        "html": "<p>Testing outbound email with UniPile format (from/to fields)</p>"
    },
    "message_id": f"unipile_outbound_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "thread_id": f"unipile_thread_{datetime.now().strftime('%Y%m%d')}",
    "folder": "SENT",
    "labels": ["SENT"],
    "attachments": []
}

print(f"📮 Sending outbound test...")
print(f"   From: {outbound_webhook['from']['email']}")
print(f"   To: {outbound_webhook['to'][0]['email']}")
print(f"   Subject: {outbound_webhook['subject']}")

try:
    response = requests.post(
        webhook_url,
        json=outbound_webhook,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"📨 Response Status: {response.status_code}")
    
    # Get response data for error details
    try:
        response_data = response.json()
    except:
        response_data = {"raw_text": response.text}
    
    if response.status_code == 200:
        result = response_data.get('result', {})
        if not result:
            print(f"   Full response: {response_data}")
        storage_decision = result.get('storage_decision', {})
        
        if storage_decision.get('should_store'):
            print(f"✅ OUTBOUND MESSAGE STORED!")
            
            # Check message in DB
            with schema_context('oneotalent'):
                message = Message.objects.filter(
                    external_message_id=outbound_webhook['message_id']
                ).first()
                
                if message:
                    print(f"   Message ID: {message.id}")
                    print(f"   Direction: {message.direction}")
                    print(f"   To: {message.recipient_participants.first().email if message.recipient_participants.exists() else 'Unknown'}")
        else:
            print(f"❌ Message NOT stored: {storage_decision.get('reason')}")
            print(f"   Full storage decision: {storage_decision}")
    else:
        print(f"❌ Webhook failed: {response.status_code}")
        print(f"   Error: {response_data.get('error', response_data)}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Alternative format with from_attendee/to_attendees
print("\n" + "=" * 60)
print("TEST 3: ALTERNATIVE FORMAT (from_attendee/to_attendees)")
print("=" * 60)

alt_webhook = {
    "event": "mail_received",
    "type": "mail_received",
    "account_id": account_id,
    "date": datetime.utcnow().isoformat() + "Z",
    "from_attendee": {
        "identifier": vanessa_email,
        "display_name": "Vanessa Brown"
    },
    "to_attendees": [{
        "identifier": gmail_user_email,
        "display_name": "Josh"
    }],
    "subject": f"Alternative Format Test - {datetime.now().strftime('%H:%M:%S')}",
    "body": {
        "text": "Testing with from_attendee/to_attendees format",
        "html": "<p>Testing with from_attendee/to_attendees format</p>"
    },
    "message_id": f"alt_format_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "thread_id": f"alt_thread_{datetime.now().strftime('%Y%m%d')}",
    "folder": "INBOX",
    "labels": ["INBOX"],
    "attachments": []
}

print(f"📮 Sending alternative format test...")
print(f"   From: {alt_webhook['from_attendee']['identifier']}")
print(f"   To: {alt_webhook['to_attendees'][0]['identifier']}")
print(f"   Subject: {alt_webhook['subject']}")

try:
    response = requests.post(
        webhook_url,
        json=alt_webhook,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"📨 Response Status: {response.status_code}")
    
    # Get response data for error details
    try:
        response_data = response.json()
    except:
        response_data = {"raw_text": response.text}
    
    if response.status_code == 200:
        result = response_data.get('result', {})
        if not result:
            print(f"   Full response: {response_data}")
        storage_decision = result.get('storage_decision', {})
        
        if storage_decision.get('should_store'):
            print(f"✅ ALTERNATIVE FORMAT MESSAGE STORED!")
            
            # Check message in DB
            with schema_context('oneotalent'):
                message = Message.objects.filter(
                    external_message_id=alt_webhook['message_id']
                ).first()
                
                if message:
                    print(f"   Message ID: {message.id}")
                    print(f"   Direction: {message.direction}")
                    print(f"   From: {message.sender_participant.email if message.sender_participant else 'Unknown'}")
        else:
            print(f"❌ Message NOT stored: {storage_decision.get('reason')}")
            print(f"   Full storage decision: {storage_decision}")
    else:
        print(f"❌ Webhook failed: {response.status_code}")
        print(f"   Error: {response_data.get('error', response_data)}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Count messages created in this test
with schema_context('oneotalent'):
    test_messages = Message.objects.filter(
        external_message_id__in=[
            inbound_webhook['message_id'],
            outbound_webhook['message_id'],
            alt_webhook['message_id']
        ]
    )
    
    print(f"Messages created: {test_messages.count()}/3")
    
    for msg in test_messages:
        print(f"  - {msg.subject} ({msg.direction})")

print("\n✅ Test complete!")