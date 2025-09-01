#!/usr/bin/env python
"""
Test script for email webhook handling
Tests the complete flow from webhook receipt to message storage
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.webhooks.dispatcher import UnifiedWebhookDispatcher
from communications.models import UserChannelConnection, Message, Conversation

def test_email_webhook():
    """Test email webhook processing"""
    
    # Sample email webhook data from UniPile
    sample_webhook = {
        "event": "mail_received",
        "type": "mail_received",
        "account_id": "test_account_123",  # This should match a real account in your system
        "date": "2025-01-01T10:30:00.000Z",
        "from": {
            "email": "sender@example.com",
            "name": "John Sender"
        },
        "to": [{
            "email": "recipient@example.com", 
            "name": "Jane Recipient"
        }],
        "subject": "Test Email Subject",
        "body": {
            "text": "This is a test email message.",
            "html": "<html><body><p>This is a test email message.</p></body></html>"
        },
        "message_id": "test_msg_" + datetime.now().strftime("%Y%m%d%H%M%S"),
        "thread_id": "test_thread_123",
        "folder": "INBOX",
        "labels": ["INBOX"],
        "attachments": []
    }
    
    print("=" * 80)
    print("EMAIL WEBHOOK TEST")
    print("=" * 80)
    
    # Check for existing email connections
    print("\n1. Checking for email connections...")
    
    # Use oneotalent tenant for testing (where communications tables exist)
    with schema_context('oneotalent'):
        email_connections = UserChannelConnection.objects.filter(
            channel_type__in=['gmail', 'outlook', 'mail', 'email'],
            is_active=True
        )
        
        if email_connections.exists():
            print(f"Found {email_connections.count()} email connection(s):")
            for conn in email_connections:
                print(f"  - {conn.channel_type}: {conn.account_name} (Account ID: {conn.unipile_account_id})")
                
                # Use the first connection's account ID for testing
                if not sample_webhook.get("account_id") or sample_webhook["account_id"] == "test_account_123":
                    sample_webhook["account_id"] = conn.unipile_account_id
                    print(f"  Using account ID: {conn.unipile_account_id}")
                    break
        else:
            print("  No email connections found. Creating test connection...")
            # Create a test connection for demonstration
            test_conn = UserChannelConnection.objects.create(
                channel_type='gmail',
                unipile_account_id='test_gmail_account',
                account_name='Test Gmail Account',
                auth_status='authenticated',
                is_active=True,
                user_id=1  # Assuming user with ID 1 exists
            )
            sample_webhook["account_id"] = test_conn.unipile_account_id
            print(f"  Created test connection: {test_conn.account_name}")
    
    # Test webhook dispatcher
    print("\n2. Testing webhook dispatcher...")
    dispatcher = UnifiedWebhookDispatcher()
    
    # Test account ID extraction
    print("\n3. Testing account ID extraction...")
    account_id = dispatcher._extract_account_id(sample_webhook)
    print(f"  Extracted account ID: {account_id}")
    
    if not account_id:
        print("  ERROR: Failed to extract account ID")
        print("  Webhook data keys:", list(sample_webhook.keys()))
        return
    
    # Test provider type detection
    print("\n4. Testing provider type detection...")
    provider_type = dispatcher._get_provider_type(account_id)
    print(f"  Detected provider type: {provider_type}")
    
    if not provider_type:
        print("  ERROR: Failed to detect provider type")
        print("  Make sure the account exists in the database")
        return
    
    # Test webhook processing
    print("\n5. Processing webhook...")
    result = dispatcher.process_webhook('mail_received', sample_webhook)
    
    print("\n6. Processing result:")
    print(json.dumps(result, indent=2, default=str))
    
    # Check if message was created
    if result.get('success'):
        print("\n7. Checking created message...")
        
        with schema_context('oneotalent'):
            # Look for the message
            messages = Message.objects.filter(
                external_message_id=sample_webhook['message_id']
            )
            
            if messages.exists():
                message = messages.first()
                print(f"  Message created successfully!")
                print(f"  - ID: {message.id}")
                print(f"  - Subject: {message.conversation.subject}")
                print(f"  - Content: {message.content[:100]}...")
                print(f"  - Direction: {message.direction}")
                print(f"  - Status: {message.status}")
                
                # Check conversation
                print(f"\n  Conversation details:")
                print(f"  - ID: {message.conversation.id}")
                print(f"  - Subject: {message.conversation.subject}")
                print(f"  - Channel: {message.conversation.channel.name}")
            else:
                print("  WARNING: Message not found in database")
                print("  This might be due to contact resolution filters")
                
                # Check if it was filtered out
                if 'storage_decision' in result:
                    decision = result['storage_decision']
                    print(f"  Storage decision: {decision.get('should_store')}")
                    print(f"  Reason: {decision.get('reason')}")
    else:
        print("\n7. Processing failed!")
        print(f"  Error: {result.get('error')}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_email_webhook()