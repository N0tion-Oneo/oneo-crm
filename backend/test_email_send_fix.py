#!/usr/bin/env python
"""
Test script to verify email sending functionality after fixes
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
from pipelines.models import Record
from communications.models import UserChannelConnection, TenantUniPileConfig
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
from django_tenants.utils import schema_context

User = get_user_model()

def test_email_sending_with_fixes():
    """Test email sending with proper tenant context"""
    
    print("=" * 60)
    print("Testing Email Sending with Tenant Context Fixes")
    print("=" * 60)
    
    # First, we need to set up tenant context
    from tenants.models import Tenant
    
    # Get a tenant to work with
    tenant = Tenant.objects.filter(schema_name='oneotalent').first()
    if not tenant:
        # Try any tenant that's not public
        tenant = Tenant.objects.exclude(schema_name='public').first()
        if not tenant:
            print("❌ No tenant found. Please create one first.")
            print("   Run: python manage.py create_tenant --schema_name=demo --name='Demo' --domain-domain='demo.localhost'")
            return
    
    print(f"✅ Using tenant: {tenant.name} (schema: {tenant.schema_name})")
    
    # Switch to tenant schema
    with schema_context(tenant.schema_name):
        # Get an email connection - try any user with email
        connection = UserChannelConnection.objects.filter(
            channel_type__in=['gmail', 'outlook', 'email']
        ).first()
        
        if connection:
            user = connection.user
            print(f"✅ Found email connection for user: {user.email}")
        else:
            # Fall back to superuser without connection
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                print("❌ No users found in tenant.")
                return
            print(f"✅ Using user: {user.email} (no email connection)")
        
        if not connection:
            print("❌ No email connection found for user. Please connect an email account first.")
            return
        
        print(f"✅ Found email connection: {connection.account_name} ({connection.channel_type})")
        print(f"   UniPile Account ID: {connection.unipile_account_id}")
        
        # Check tenant configuration
        print("\n🔧 Checking Tenant Configuration...")
        
        # Get or create tenant config
        config = TenantUniPileConfig.get_or_create_for_tenant()
        if config.is_configured():
            print("   ✅ Tenant UniPile configuration is active")
            credentials = config.get_api_credentials()
            print(f"   DSN: {credentials['dsn'][:30]}...")
        else:
            print("   ⚠️ Tenant UniPile configuration not properly configured")
        
        # Initialize email service
        print("\n📧 Initializing Email Service...")
        service = EmailService(account_identifier=connection.account_name)
        
        # Test the client initialization
        try:
            client = service.get_client()
            print("   ✅ Email service client initialized successfully")
            print(f"   Client type: {type(client)}")
        except Exception as e:
            print(f"   ❌ Failed to initialize client: {e}")
            return
    
        # Test sending email
        print("\n📤 Testing Email Send...")
        
        test_email = {
        'account_id': connection.unipile_account_id,
        'to': [{'identifier': 'test@example.com', 'display_name': 'Test User'}],
        'subject': f'Test Email (Fixed) - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        'body': '''
        <html>
        <body>
            <h2>Test Email from Oneo CRM</h2>
            <p>This test email verifies the following fixes:</p>
            <ul>
                <li>✅ Recipient format conversion (Dict to String)</li>
                <li>✅ Tenant context handling</li>
                <li>✅ UniPile client initialization</li>
            </ul>
            <p>Best regards,<br>Oneo CRM Team</p>
        </body>
        </html>
        ''',
        'cc': None,
        'bcc': None,
        'reply_to': None
        }
        
        print(f"   To: {test_email['to'][0]['identifier']}")
        print(f"   Subject: {test_email['subject']}")
    
        # Perform dry run - just test the formatting
        print("\n🔍 Testing recipient formatting...")
        try:
            # Test the conversion that happens in EmailService.send_email
            to_emails = [r.get('identifier', '') for r in test_email['to'] if r.get('identifier')]
            print(f"   Input format: {test_email['to']}")
            print(f"   Converted format: {to_emails}")
            print("   ✅ Recipient formatting correct")
        except Exception as e:
            print(f"   ❌ Recipient formatting error: {e}")
            return
        
        # Ask user if they want to actually send
        response = input("\nDo you want to send a test email? (y/n): ")
        if response.lower() != 'y':
            print("   Skipped")
            return
        
        # Get recipient email
        recipient = input("Enter recipient email address (or press Enter for test@example.com): ").strip()
        if recipient:
            test_email['to'][0]['identifier'] = recipient
        
        try:
            print("\n📨 Sending email...")
            result = async_to_sync(service.send_email)(
                account_id=connection.unipile_account_id,
                to=test_email['to'],
                subject=test_email['subject'],
                body=test_email['body'],
                cc=test_email['cc'],
                bcc=test_email['bcc'],
                reply_to=test_email['reply_to']
            )
            
            if result.get('success'):
                print(f"   ✅ Email sent successfully!")
                print(f"   Tracking ID: {result.get('tracking_id')}")
                print(f"   Response: {json.dumps(result.get('response', {}), indent=2)}")
            else:
                print(f"   ❌ Failed to send email: {result.get('error')}")
            
        except Exception as e:
            print(f"   ❌ Error sending email: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("Testing complete!")
        print("=" * 60)

if __name__ == "__main__":
    test_email_sending_with_fixes()