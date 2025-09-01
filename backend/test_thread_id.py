#!/usr/bin/env python
"""
Test email threading with thread_id parameter
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
from communications.unipile import unipile_service
from asgiref.sync import async_to_sync
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_thread_id():
    """Test if UniPile accepts thread_id parameter"""
    
    print("=" * 60)
    print("Testing Email Threading with thread_id")
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
        
        # Find a conversation with a thread ID
        conversation = Conversation.objects.filter(
            external_thread_id__isnull=False,
            channel__channel_type='gmail'
        ).exclude(external_thread_id='').first()
        
        if conversation:
            print(f"\n📧 Found conversation:")
            print(f"   ID: {conversation.id}")
            print(f"   Thread ID: {conversation.external_thread_id}")
            print(f"   Subject: {conversation.subject}")
            
            # Try sending with thread_id parameter
            print(f"\n📤 Testing with thread_id parameter...")
            
            client = unipile_service.get_client()
            
            # Build request with thread_id
            data = {
                'account_id': conn.unipile_account_id,
                'to': [{'identifier': 'test@example.com', 'display_name': 'Test'}],
                'subject': f"Thread test - {datetime.now().strftime('%H:%M:%S')}",
                'body': f"<p>Testing thread_id: {conversation.external_thread_id}</p>",
                'is_html': True,
                'thread_id': conversation.external_thread_id  # Try adding thread_id
            }
            
            try:
                result = async_to_sync(client._make_request)('POST', 'emails', data=data)
                print(f"✅ Success with thread_id!")
                print(f"   Response: {json.dumps(result, indent=2)}")
                return True
            except Exception as e:
                error_str = str(e)
                if 'unknown field' in error_str.lower() or 'invalid' in error_str.lower():
                    print(f"❌ thread_id not supported: {error_str}")
                else:
                    print(f"⚠️ Other error: {error_str}")
                    
        # Test what fields are actually accepted
        print(f"\n📋 Testing minimal email to check response...")
        service = EmailService()
        result = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': 'test@example.com', 'display_name': 'Test'}],
            subject=f"Field test - {datetime.now().strftime('%H:%M:%S')}",
            body="<p>Testing response fields</p>"
        )
        
        if result.get('success'):
            response = result.get('response', {})
            print(f"\n📨 Response fields available:")
            for key, value in response.items():
                print(f"   {key}: {value}")
                
        return True

if __name__ == "__main__":
    test_thread_id()