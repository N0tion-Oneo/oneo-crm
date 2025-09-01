#!/usr/bin/env python
"""
Test email sending with a real recipient scenario
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
from communications.models import UserChannelConnection, Message, Conversation
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
import logging

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_real_email_send():
    """Test email sending with real recipient from existing messages"""
    
    print("=" * 60)
    print("Testing Email Send with Real Recipients")
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
        print(f"   Account ID: {conn.unipile_account_id}")
        
        # Find a real email from existing messages
        recent_message = Message.objects.filter(
            contact_email__isnull=False,
            direction='inbound'
        ).exclude(
            contact_email=''
        ).first()
        
        if recent_message:
            real_email = recent_message.contact_email
            print(f"✅ Found real email from messages: {real_email}")
        else:
            # Use a safe test email
            real_email = 'vanessa.c.brown86@gmail.com'
            print(f"⚠️ No recent messages found, using test email: {real_email}")
        
        # Test 1: Simple email to real recipient
        print(f"\n📧 Test 1: Simple email to {real_email}")
        test_to = [{'identifier': real_email, 'display_name': ''}]
        test_subject = f"Test Email - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        test_body = f"""
        <p>This is a test email from Oneo CRM.</p>
        <p>Testing email functionality with real recipient.</p>
        <p>Timestamp: {datetime.now().isoformat()}</p>
        """
        
        print(f"   To: {test_to}")
        print(f"   Subject: {test_subject}")
        
        service = EmailService()
        
        try:
            result = async_to_sync(service.send_email)(
                account_id=conn.unipile_account_id,
                to=test_to,
                subject=test_subject,
                body=test_body
            )
            
            print(f"\n📨 Result:")
            print(json.dumps(result, indent=2))
            
            if result.get('success'):
                print(f"✅ Test 1 passed - Email sent successfully!")
                external_id = result.get('response', {}).get('id')
                print(f"   External ID: {external_id}")
            else:
                print(f"❌ Test 1 failed: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Test 1 exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 2: Reply threading with real message
        print(f"\n📧 Test 2: Reply threading")
        
        # Find a message to reply to
        message_to_reply = Message.objects.filter(
            external_message_id__isnull=False,
            contact_email=real_email
        ).exclude(external_message_id='').first()
        
        if message_to_reply:
            print(f"   Found message to reply to:")
            print(f"   - ID: {message_to_reply.id}")
            print(f"   - External ID: {message_to_reply.external_message_id}")
            print(f"   - Subject: {message_to_reply.subject}")
            
            reply_subject = f"Re: {message_to_reply.subject}" if not message_to_reply.subject.startswith('Re:') else message_to_reply.subject
            reply_body = f"""
            <p>This is a test reply to verify threading.</p>
            <p>Replying to message: {message_to_reply.external_message_id}</p>
            <p>Timestamp: {datetime.now().isoformat()}</p>
            """
            
            try:
                result = async_to_sync(service.send_email)(
                    account_id=conn.unipile_account_id,
                    to=test_to,
                    subject=reply_subject,
                    body=reply_body,
                    reply_to=message_to_reply.external_message_id
                )
                
                print(f"\n📨 Reply Result:")
                print(json.dumps(result, indent=2))
                
                if result.get('success'):
                    print(f"✅ Test 2 passed - Reply sent with threading!")
                else:
                    print(f"❌ Test 2 failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ Test 2 exception: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ No messages found to reply to, skipping test 2")
        
        print("\n" + "=" * 60)
        print("Testing complete!")
        return True

if __name__ == "__main__":
    test_real_email_send()