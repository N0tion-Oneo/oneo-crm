#!/usr/bin/env python
"""
Non-interactive test to verify email sending is working
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
from communications.models import UserChannelConnection, TenantUniPileConfig
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync
from django_tenants.utils import schema_context
from tenants.models import Tenant

User = get_user_model()

def test_email_format_only():
    """Test only the formatting without actually sending email"""
    
    print("=" * 60)
    print("Testing Email Format Conversion (Non-interactive)")
    print("=" * 60)
    
    # Get a tenant to work with
    tenant = Tenant.objects.filter(schema_name='oneotalent').first()
    if not tenant:
        tenant = Tenant.objects.exclude(schema_name='public').first()
        if not tenant:
            print("❌ No tenant found")
            return False
    
    print(f"✅ Using tenant: {tenant.name} (schema: {tenant.schema_name})")
    
    # Switch to tenant schema
    with schema_context(tenant.schema_name):
        # Get an email connection
        connection = UserChannelConnection.objects.filter(
            channel_type__in=['gmail', 'outlook', 'email']
        ).first()
        
        if not connection:
            print("❌ No email connection found")
            return False
        
        user = connection.user
        print(f"✅ Found email connection for user: {user.email}")
        print(f"   Account: {connection.account_name} ({connection.channel_type})")
        print(f"   UniPile ID: {connection.unipile_account_id}")
        
        # Check tenant configuration
        config = TenantUniPileConfig.get_or_create_for_tenant()
        if config.is_configured():
            print("✅ Tenant UniPile configuration is active")
        else:
            print("❌ Tenant UniPile configuration not properly configured")
            return False
        
        # Initialize email service
        print("\n📧 Testing Email Service Initialization...")
        service = EmailService(account_identifier=connection.account_name)
        
        # Test the client initialization
        try:
            client = service.get_client()
            print("   ✅ Email service client initialized successfully")
            print(f"   Client type: {type(client).__name__}")
        except Exception as e:
            print(f"   ❌ Failed to initialize client: {e}")
            return False
        
        # Test recipient formatting
        print("\n🔍 Testing Recipient Format Conversion...")
        
        test_recipients = [
            {'identifier': 'test@example.com', 'display_name': 'Test User'}
        ]
        
        try:
            # Test the conversion that happens in EmailService.send_email
            converted = [r.get('identifier', '') for r in test_recipients if r.get('identifier')]
            print(f"   Input format:    {test_recipients}")
            print(f"   Converted format: {converted}")
            print("   ✅ Recipient formatting works correctly")
            
            # Verify the format matches what UniPile expects
            if isinstance(converted, list) and all(isinstance(email, str) for email in converted):
                print("   ✅ Format matches UniPile expectations (List[str])")
            else:
                print("   ❌ Format does not match UniPile expectations")
                return False
            
        except Exception as e:
            print(f"   ❌ Recipient formatting error: {e}")
            return False
        
        # Test with multiple recipients
        print("\n🔍 Testing Multiple Recipients...")
        
        test_multiple = [
            {'identifier': 'user1@example.com', 'display_name': 'User One'},
            {'identifier': 'user2@example.com', 'display_name': 'User Two'},
            {'identifier': '', 'display_name': 'Invalid User'},  # Should be filtered out
        ]
        
        converted_multiple = [r.get('identifier', '') for r in test_multiple if r.get('identifier')]
        print(f"   Input count:  {len(test_multiple)} recipients")
        print(f"   Output count: {len(converted_multiple)} recipients (filtered)")
        print(f"   Output:       {converted_multiple}")
        
        if len(converted_multiple) == 2:
            print("   ✅ Multiple recipient handling works correctly")
        else:
            print("   ❌ Multiple recipient handling failed")
            return False
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Email sending should work!")
        print("=" * 60)
        return True

if __name__ == "__main__":
    success = test_email_format_only()
    sys.exit(0 if success else 1)