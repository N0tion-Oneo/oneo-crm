#!/usr/bin/env python
"""
Test script to verify email sending functionality
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
from pipelines.models import Record, Pipeline
from communications.models import UserChannelConnection
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync

User = get_user_model()

def test_email_sending():
    """Test email sending via the new endpoint"""
    
    print("=" * 60)
    print("Testing Email Sending Functionality")
    print("=" * 60)
    
    # Get a test user
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("❌ No superuser found. Please create one first.")
        return
    
    print(f"✅ Using user: {user.email}")
    
    # Get an email connection
    connection = UserChannelConnection.objects.filter(
        user=user,
        channel_type__in=['gmail', 'outlook', 'email']
    ).first()
    
    if not connection:
        print("❌ No email connection found for user. Please connect an email account first.")
        return
    
    print(f"✅ Found email connection: {connection.account_name} ({connection.channel_type})")
    print(f"   UniPile Account ID: {connection.unipile_account_id}")
    
    # Get a test record
    record = Record.objects.first()
    if not record:
        print("❌ No records found. Please create a record first.")
        return
    
    print(f"✅ Using record: {record.id}")
    
    # Test payload
    test_email = {
        'account_id': connection.unipile_account_id,
        'to': [{'identifier': 'test@example.com', 'display_name': 'Test User'}],
        'subject': f'Test Email - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        'body': '''
        <html>
        <body>
            <h2>Test Email from Oneo CRM</h2>
            <p>This is a test email sent via the UniPile integration.</p>
            <p>Features tested:</p>
            <ul>
                <li>HTML formatting</li>
                <li>UniPile API integration</li>
                <li>Record context sending</li>
            </ul>
            <p>Best regards,<br>Oneo CRM Team</p>
        </body>
        </html>
        ''',
        'cc': None,
        'bcc': None,
        'reply_to': None
    }
    
    print("\n📧 Test email details:")
    print(f"   To: {test_email['to'][0]['identifier']}")
    print(f"   Subject: {test_email['subject']}")
    
    # Initialize email service
    service = EmailService(account_identifier=connection.account_name)
    
    # Test 1: Verify connection
    print("\n🔍 Test 1: Verifying email account connection...")
    try:
        # Try to fetch a few emails to verify the connection works
        result = async_to_sync(service.get_emails)(
            account_id=connection.unipile_account_id,
            folder='INBOX',
            limit=1
        )
        
        if result.get('success'):
            print("   ✅ Email account connection is working")
        else:
            print(f"   ❌ Failed to verify connection: {result.get('error')}")
            return
    except Exception as e:
        print(f"   ❌ Error verifying connection: {str(e)}")
        return
    
    # Test 2: Send test email
    print("\n📤 Test 2: Sending test email...")
    
    response = input("Do you want to send a test email? (y/n): ")
    if response.lower() != 'y':
        print("   Skipped")
        return
    
    # Get recipient email
    recipient = input("Enter recipient email address (or press Enter for test@example.com): ").strip()
    if recipient:
        test_email['to'][0]['identifier'] = recipient
    
    try:
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
        else:
            print(f"   ❌ Failed to send email: {result.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Error sending email: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)

def check_unipile_config():
    """Check if UniPile is properly configured"""
    print("\n🔧 Checking UniPile Configuration...")
    
    try:
        from oneo_crm.settings import unipile_settings
        
        if unipile_settings.is_configured():
            print("   ✅ Global UniPile configuration found")
            print(f"   DSN: {unipile_settings.dsn[:30]}...")
        else:
            print("   ❌ UniPile not configured. Please set UNIPILE_DSN and UNIPILE_API_KEY")
            return False
            
    except Exception as e:
        print(f"   ❌ Error checking configuration: {str(e)}")
        return False
    
    # Check tenant config if in multi-tenant mode
    try:
        from django.db import connection
        if hasattr(connection, 'tenant'):
            tenant = connection.tenant
            if hasattr(tenant, 'unipile_config'):
                if tenant.unipile_config.is_configured():
                    print(f"   ✅ Tenant UniPile configuration found for: {tenant.name}")
                else:
                    print(f"   ⚠️ Tenant {tenant.name} has no UniPile configuration")
    except:
        pass
    
    return True

if __name__ == "__main__":
    # First check configuration
    if check_unipile_config():
        # Then run the test
        test_email_sending()
    else:
        print("\n❌ Please configure UniPile before testing email sending")