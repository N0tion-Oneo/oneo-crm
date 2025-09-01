#!/usr/bin/env python
"""
Quick test to verify email sending is working
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from communications.models import UserChannelConnection
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
from django_tenants.utils import schema_context
from tenants.models import Tenant

User = get_user_model()

def test_email_now():
    """Quick email send test"""
    
    print("=" * 60)
    print("Quick Email Send Test")
    print("=" * 60)
    
    # Get tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    print(f"✅ Using tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get email connection
        connection = UserChannelConnection.objects.filter(
            channel_type='gmail'
        ).first()
        
        if not connection:
            print("❌ No Gmail connection found")
            return False
        
        print(f"✅ Found: {connection.account_name}")
        print(f"   UniPile ID: {connection.unipile_account_id}")
        
        # Initialize service
        service = EmailService(account_identifier=connection.account_name)
        
        # Test email - CORRECT FORMAT
        test_email = {
            'account_id': connection.unipile_account_id,
            'to': [{'identifier': 'test@example.com', 'display_name': 'Test'}],
            'subject': f'Test - {datetime.now().strftime("%H:%M:%S")}',
            'body': '<p>Test email - all fixes applied</p>',
            'cc': None,
            'bcc': None,
            'reply_to': None
        }
        
        print(f"\n📧 Sending to: {test_email['to'][0]['identifier']}")
        
        try:
            result = async_to_sync(service.send_email)(
                account_id=test_email['account_id'],
                to=test_email['to'],
                subject=test_email['subject'],
                body=test_email['body'],
                cc=test_email['cc'],
                bcc=test_email['bcc'],
                reply_to=test_email['reply_to']
            )
            
            if result.get('success'):
                print(f"✅ SUCCESS! Tracking ID: {result.get('tracking_id')}")
                return True
            else:
                print(f"❌ Failed: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_email_now()
    sys.exit(0 if success else 1)