#!/usr/bin/env python
"""
Test email sending without reply_to to isolate the issue
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

def test_email_scenarios():
    """Test different email scenarios to isolate the issue"""
    
    print("=" * 60)
    print("Testing Email Scenarios")
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
        
        service = EmailService()
        
        # Test 1: Send without reply_to (should work)
        print(f"\n📧 Test 1: Send without reply_to")
        result1 = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': 'admin@growthlist.co', 'display_name': ''}],
            subject=f"Test without reply - {datetime.now().strftime('%H:%M:%S')}",
            body="<p>This email has no reply_to field.</p>"
        )
        print(f"   Result: {'✅ Success' if result1.get('success') else '❌ Failed'}")
        if result1.get('success'):
            print(f"   ID: {result1.get('response', {}).get('id')}")
        
        # Test 2: Send with a UniPile message ID we just created
        if result1.get('success'):
            unipile_id = result1.get('response', {}).get('id')
            print(f"\n📧 Test 2: Reply to UniPile ID: {unipile_id}")
            
            result2 = async_to_sync(service.send_email)(
                account_id=conn.unipile_account_id,
                to=[{'identifier': 'admin@growthlist.co', 'display_name': ''}],
                subject=f"Reply to UniPile message - {datetime.now().strftime('%H:%M:%S')}",
                body=f"<p>Replying to UniPile ID: {unipile_id}</p>",
                reply_to=unipile_id
            )
            print(f"   Result: {'✅ Success' if result2.get('success') else '❌ Failed'}")
            if not result2.get('success'):
                print(f"   Error: {result2.get('error')}")
        
        # Test 3: Check what external IDs we have stored
        print(f"\n📧 Test 3: Check stored external IDs")
        
        # Find outbound messages with external IDs
        outbound_msgs = Message.objects.filter(
            direction='outbound',
            external_message_id__isnull=False
        ).exclude(external_message_id='').order_by('-created_at')[:3]
        
        print(f"   Recent outbound messages:")
        for msg in outbound_msgs:
            print(f"   - {msg.external_message_id} ({msg.created_at.strftime('%Y-%m-%d %H:%M')})")
        
        # Find inbound messages with external IDs
        inbound_msgs = Message.objects.filter(
            direction='inbound',
            external_message_id__isnull=False
        ).exclude(external_message_id='').order_by('-created_at')[:3]
        
        print(f"\n   Recent inbound messages:")
        for msg in inbound_msgs:
            ext_id = msg.external_message_id
            # Check format
            if ext_id.startswith('<'):
                print(f"   - {ext_id} (angle bracket format)")
            elif '@' in ext_id and '.' in ext_id:
                print(f"   - {ext_id} (email format)")
            else:
                print(f"   - {ext_id} (UniPile format)")
        
        print("\n" + "=" * 60)
        print("Analysis complete!")
        return True

if __name__ == "__main__":
    test_email_scenarios()