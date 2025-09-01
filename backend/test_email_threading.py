#!/usr/bin/env python
"""
Test email threading to verify Gmail thread IDs are properly handled
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
from communications.models import UserChannelConnection, Conversation, Message
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_email_threading():
    """Test email threading with Gmail thread IDs"""
    
    print("=" * 60)
    print("Testing Email Threading with Gmail")
    print("=" * 60)
    
    tenant = Tenant.objects.get(schema_name='oneotalent')
    print(f"✅ Tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get Gmail connection
        conn = UserChannelConnection.objects.filter(channel_type='gmail').first()
        if not conn:
            print("❌ No Gmail connection found")
            return False
        print(f"✅ Gmail: {conn.account_name}")
        
        # Send a test email and examine the response
        service = EmailService()
        subject = f"Threading Test - {datetime.now().strftime('%H:%M:%S')}"
        
        print(f"\n📧 Sending initial email: {subject}")
        result = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': 'josh@oneodigital.com', 'display_name': 'Josh Cowan'}],
            subject=subject,
            body='<p>This is the first email in a thread. Please reply to test threading.</p>'
        )
        
        if result.get('success'):
            print(f"✅ Email sent successfully")
            
            # Examine the full response
            response = result.get('response', {})
            print(f"\n📋 Full UniPile Response:")
            print(json.dumps(response, indent=2))
            
            # Extract key fields
            unipile_id = response.get('id')
            provider_id = response.get('provider_id')
            tracking_id = result.get('tracking_id')
            
            print(f"\n🔍 Key fields extracted:")
            print(f"   UniPile ID: {unipile_id}")
            print(f"   Provider ID (Gmail thread): {provider_id}")
            print(f"   Tracking ID: {tracking_id}")
            
            # Check if provider_id looks like a Gmail thread ID
            if provider_id:
                print(f"\n📊 Provider ID Analysis:")
                print(f"   Length: {len(provider_id)}")
                print(f"   Format: {'Hexadecimal' if all(c in '0123456789abcdef' for c in provider_id.lower()) else 'Mixed'}")
                print(f"   Looks like Gmail thread ID: {'Yes' if len(provider_id) == 16 else 'Maybe'}")
            
            # Now send a reply using the thread_id
            if provider_id:
                print(f"\n📧 Sending reply with thread_id: {provider_id}")
                reply_result = async_to_sync(service.send_email)(
                    account_id=conn.unipile_account_id,
                    to=[{'identifier': 'josh@oneodigital.com', 'display_name': 'Josh Cowan'}],
                    subject=f"Re: {subject}",
                    body='<p>This is a reply that should be in the same thread.</p>',
                    thread_id=provider_id  # Use the provider_id as thread_id
                )
                
                if reply_result.get('success'):
                    print(f"✅ Reply sent successfully")
                    reply_response = reply_result.get('response', {})
                    reply_provider_id = reply_response.get('provider_id')
                    print(f"   Reply provider_id: {reply_provider_id}")
                    
                    if reply_provider_id == provider_id:
                        print(f"✅ SUCCESS: Same thread ID maintained!")
                    else:
                        print(f"⚠️ WARNING: Different thread IDs - threading may not work")
                else:
                    print(f"❌ Failed to send reply: {reply_result.get('error')}")
            
            return True
        else:
            print(f"❌ Failed to send email: {result.get('error')}")
            return False

if __name__ == "__main__":
    success = test_email_threading()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ EMAIL THREADING TEST COMPLETED")
        print("Check your Gmail to verify if emails are in the same thread")
    else:
        print("❌ EMAIL THREADING TEST FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)