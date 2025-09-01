#!/usr/bin/env python
"""
Debug email sending with detailed error logging
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
from communications.models import UserChannelConnection
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
import logging

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_email_send():
    """Test email sending with full error capture"""
    
    print("=" * 60)
    print("Testing Email Send with Detailed Error Logging")
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
        
        # Prepare test email
        test_to = [{'identifier': 'test@example.com', 'display_name': 'Test User'}]
        test_subject = f"Test Email Debug - {datetime.now().isoformat()}"
        test_body = """
        <p>This is a test email to debug the 500 error.</p>
        <p>Sent via UniPile API integration.</p>
        <p>Timestamp: {}</p>
        """.format(datetime.now().isoformat())
        
        print(f"\n📤 Sending test email:")
        print(f"   To: {test_to}")
        print(f"   Subject: {test_subject}")
        
        # Send email
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
                print(f"\n✅ Email sent successfully!")
                print(f"   Tracking ID: {result.get('tracking_id')}")
                return True
            else:
                print(f"\n❌ Failed to send email:")
                print(f"   Error: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"\n❌ Exception occurred:")
            print(f"   Type: {type(e).__name__}")
            print(f"   Message: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    test_email_send()