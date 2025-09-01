#!/usr/bin/env python
"""
Test script to verify email webhook handling with proper From/To fields
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.webhooks.email_handler import EmailWebhookHandler
from communications.models import UserChannelConnection, Message

def test_email_webhook():
    """Test email webhook with sample data"""
    
    # Sample webhook data simulating an email from Vanessa
    sample_webhook = {
        "event": "message.received",
        "timestamp": datetime.now().isoformat(),
        "external_id": f"test-email-{datetime.now().timestamp()}",
        "subject": "Test Email from Vanessa",
        "body": "<p>This is a test email to verify the From/To fields are correctly set.</p>",
        
        # Sender information
        "from_attendee": {
            "identifier": "vanessa.c.brown86@gmail.com",
            "display_name": "Vanessa Brown"
        },
        
        # Recipients information
        "to_attendees": [
            {
                "identifier": "josh@oneohq.com",
                "display_name": "Josh Cowan"
            }
        ],
        "cc_attendees": [],
        
        # Thread and message IDs
        "thread_id": "thread-12345",
        "message_id": f"msg-{datetime.now().timestamp()}",
        
        # Folder and labels
        "folder": "INBOX",
        "labels": ["INBOX", "UNREAD"],
        "is_read": False
    }
    
    print("=" * 60)
    print("Testing Email Webhook Handler")
    print("=" * 60)
    
    # Get a test account (you'll need to adjust this to match your setup)
    try:
        # Try to find an email connection
        connection = UserChannelConnection.objects.filter(
            channel_type__in=['gmail', 'outlook', 'email']
        ).first()
        
        if not connection:
            print("❌ No email connection found. Please connect an email account first.")
            return
        
        print(f"✅ Using connection: {connection.account_name} ({connection.channel_type})")
        account_id = connection.unipile_account_id or connection.id
        
        # Initialize handler
        handler = EmailWebhookHandler()
        
        # Process the webhook
        print("\n📧 Processing webhook...")
        result = handler.handle_email_received(str(account_id), sample_webhook)
        
        print("\n📊 Result:")
        print(json.dumps(result, indent=2, default=str))
        
        if result.get('success'):
            print("\n✅ Webhook processed successfully!")
            
            # Check the created message
            if result.get('message_id'):
                message = Message.objects.filter(id=result['message_id']).first()
                if message:
                    print("\n📨 Message metadata:")
                    metadata = message.metadata or {}
                    
                    # Check for the new fields
                    if 'from' in metadata:
                        print(f"  From: {metadata['from']}")
                    else:
                        print("  ❌ Missing 'from' field in metadata")
                    
                    if 'to' in metadata:
                        print(f"  To: {metadata['to']}")
                    else:
                        print("  ❌ Missing 'to' field in metadata")
                    
                    if 'cc' in metadata:
                        print(f"  CC: {metadata['cc']}")
                    
                    # Also show the old fields for comparison
                    print("\n  Legacy fields:")
                    if 'sender_info' in metadata:
                        print(f"    sender_info: {metadata['sender_info'].get('email')}")
                    if 'recipients' in metadata:
                        to_recipients = metadata['recipients'].get('to', [])
                        if to_recipients:
                            print(f"    recipients.to: {[r.get('email') for r in to_recipients]}")
                    
                    print(f"\n  contact_email field: {message.contact_email}")
                    print(f"  direction: {message.direction}")
        else:
            print(f"\n❌ Webhook processing failed: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def check_existing_messages():
    """Check a few existing messages to see their metadata structure"""
    print("\n" + "=" * 60)
    print("Checking Existing Email Messages")
    print("=" * 60)
    
    messages = Message.objects.filter(
        channel__channel_type__in=['gmail', 'outlook', 'email']
    ).order_by('-created_at')[:5]
    
    for i, message in enumerate(messages, 1):
        print(f"\nMessage {i} (ID: {message.id}):")
        print(f"  Created: {message.created_at}")
        print(f"  Direction: {message.direction}")
        print(f"  Subject: {message.subject}")
        print(f"  Contact Email: {message.contact_email}")
        
        metadata = message.metadata or {}
        
        # Check for new fields
        has_from = 'from' in metadata
        has_to = 'to' in metadata
        
        if has_from:
            from_field = metadata['from']
            if isinstance(from_field, dict):
                print(f"  ✅ From: {from_field.get('name', '')} <{from_field.get('email', '')}>")
            else:
                print(f"  ✅ From: {from_field}")
        else:
            print("  ❌ Missing 'from' field")
            
        if has_to:
            to_field = metadata['to']
            if isinstance(to_field, list):
                to_emails = [f"{r.get('name', '')} <{r.get('email', '')}>" if r.get('name') else r.get('email', '') 
                           for r in to_field]
                print(f"  ✅ To: {', '.join(to_emails)}")
            else:
                print(f"  ✅ To: {to_field}")
        else:
            print("  ❌ Missing 'to' field")
    
    # Count how many need fixing
    total_email_messages = Message.objects.filter(
        channel__channel_type__in=['gmail', 'outlook', 'email']
    ).count()
    
    need_fixing = Message.objects.filter(
        channel__channel_type__in=['gmail', 'outlook', 'email']
    ).exclude(
        metadata__has_key='from'
    ).count()
    
    print(f"\n📊 Summary:")
    print(f"  Total email messages: {total_email_messages}")
    print(f"  Need metadata fix: {need_fixing}")
    print(f"  Already fixed: {total_email_messages - need_fixing}")
    
    if need_fixing > 0:
        print(f"\n💡 Run 'python manage.py fix_email_metadata' to fix {need_fixing} messages")

if __name__ == "__main__":
    # First check existing messages
    check_existing_messages()
    
    # Then test the webhook handler
    print("\n" + "=" * 60)
    response = input("Do you want to test the webhook handler? (y/n): ")
    if response.lower() == 'y':
        test_email_webhook()