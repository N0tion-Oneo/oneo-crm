#!/usr/bin/env python
"""
Test email reply with angle bracket fix
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Message
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
import logging

# Configure detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_reply_fix():
    """Test email reply with angle bracket handling"""
    
    print("=" * 60)
    print("Testing Email Reply with Angle Bracket Fix")
    print("=" * 60)
    
    # Get tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    print(f"✅ Tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get Gmail connection
        conn = UserChannelConnection.objects.filter(channel_type='gmail').first()
        if not conn:
            print("❌ No Gmail connection found")
            return False
        print(f"✅ Gmail: {conn.account_name}")
        
        # Find a message with angle brackets to reply to
        message_to_reply = Message.objects.filter(
            external_message_id__isnull=False,
            external_message_id__startswith='<'
        ).first()
        
        if message_to_reply:
            print(f"\n📧 Found message with angle brackets:")
            print(f"   ID: {message_to_reply.id}")
            print(f"   External ID (raw): {message_to_reply.external_message_id}")
            
            # Strip angle brackets
            clean_external_id = message_to_reply.external_message_id
            if clean_external_id.startswith('<') and clean_external_id.endswith('>'):
                clean_external_id = clean_external_id[1:-1]
            
            print(f"   External ID (clean): {clean_external_id}")
            print(f"   Subject: {message_to_reply.subject}")
            
            # Test sending with cleaned ID
            test_to = [{'identifier': message_to_reply.contact_email or 'test@example.com', 'display_name': ''}]
            reply_subject = f"Re: {message_to_reply.subject}" if not message_to_reply.subject.startswith('Re:') else message_to_reply.subject
            reply_body = f"""
            <p>Testing reply with cleaned external ID.</p>
            <p>Original ID: {message_to_reply.external_message_id}</p>
            <p>Cleaned ID: {clean_external_id}</p>
            <p>Timestamp: {datetime.now().isoformat()}</p>
            """
            
            print(f"\n📤 Sending reply:")
            print(f"   To: {test_to}")
            print(f"   Reply-to ID: {clean_external_id}")
            
            service = EmailService()
            
            try:
                result = async_to_sync(service.send_email)(
                    account_id=conn.unipile_account_id,
                    to=test_to,
                    subject=reply_subject,
                    body=reply_body,
                    reply_to=clean_external_id  # Use cleaned ID
                )
                
                print(f"\n📨 Result:")
                print(json.dumps(result, indent=2))
                
                if result.get('success'):
                    print(f"\n✅ Reply sent successfully with cleaned ID!")
                    print(f"   Tracking ID: {result.get('tracking_id')}")
                    return True
                else:
                    print(f"\n❌ Failed: {result.get('error')}")
                    return False
                    
            except Exception as e:
                print(f"\n❌ Exception: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("⚠️ No messages with angle brackets found")
            
            # Test with a regular message
            regular_message = Message.objects.filter(
                external_message_id__isnull=False
            ).exclude(external_message_id='').first()
            
            if regular_message:
                print(f"\n📧 Testing with regular message:")
                print(f"   External ID: {regular_message.external_message_id}")
                # Continue with test...
            
            return False

if __name__ == "__main__":
    test_reply_fix()