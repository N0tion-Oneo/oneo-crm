#!/usr/bin/env python
"""
Test email deduplication using tracking_id
"""
import os
import sys
import django
import json
from datetime import datetime, timedelta
import time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Conversation, Message
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_deduplication():
    """Test that webhook doesn't create duplicate messages"""
    
    print("=" * 60)
    print("Testing Email Deduplication with tracking_id")
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
        
        # Count messages before sending
        before_count = Message.objects.filter(
            created_at__gte=datetime.now() - timedelta(minutes=1)
        ).count()
        
        # Send a test email
        service = EmailService()
        subject = f"Dedup Test - {datetime.now().strftime('%H:%M:%S')}"
        
        print(f"\n📧 Sending email: {subject}")
        result = async_to_sync(service.send_email)(
            account_id=conn.unipile_account_id,
            to=[{'identifier': 'test@example.com', 'display_name': 'Test User'}],
            subject=subject,
            body='<p>Testing deduplication with tracking_id</p>'
        )
        
        if result.get('success'):
            tracking_id = result.get('tracking_id')
            unipile_id = result.get('response', {}).get('id')
            print(f"✅ Email sent successfully")
            print(f"   Tracking ID: {tracking_id}")
            print(f"   UniPile ID: {unipile_id}")
            
            # Check how many messages we have immediately after sending
            time.sleep(0.5)  # Small delay
            after_send = Message.objects.filter(
                created_at__gte=datetime.now() - timedelta(minutes=1)
            ).count()
            
            print(f"\n📊 Message count:")
            print(f"   Before: {before_count}")
            print(f"   After send: {after_send}")
            print(f"   Messages created: {after_send - before_count}")
            
            # Wait for webhook (usually takes 5-20 seconds)
            print(f"\n⏳ Waiting 20 seconds for webhook...")
            time.sleep(20)
            
            # Check again after webhook
            after_webhook = Message.objects.filter(
                created_at__gte=datetime.now() - timedelta(minutes=1)
            ).count()
            
            print(f"\n📊 Final count:")
            print(f"   After webhook: {after_webhook}")
            print(f"   Total messages created: {after_webhook - before_count}")
            
            # Find messages with this tracking_id
            messages_with_tracking = Message.objects.filter(
                metadata__tracking_id=tracking_id
            )
            
            print(f"\n🔍 Messages with tracking_id {tracking_id}:")
            print(f"   Count: {messages_with_tracking.count()}")
            
            for msg in messages_with_tracking:
                print(f"\n   Message {msg.id}:")
                print(f"     External ID: {msg.external_message_id}")
                print(f"     Created: {msg.created_at}")
                print(f"     Has webhook data: {'raw_webhook_data' in (msg.metadata or {})}")
                print(f"     Webhook processed: {msg.metadata.get('webhook_processed', False) if msg.metadata else False}")
            
            # Check if deduplication worked
            if after_webhook - before_count == 1:
                print(f"\n✅ SUCCESS: Only 1 message created (deduplication working!)")
                return True
            else:
                print(f"\n❌ FAILED: {after_webhook - before_count} messages created (expected 1)")
                return False
        else:
            print(f"❌ Failed to send email: {result.get('error')}")
            return False

if __name__ == "__main__":
    success = test_deduplication()
    sys.exit(0 if success else 1)