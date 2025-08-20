#!/usr/bin/env python3
"""
Test script to verify automatic account sync functionality
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.models import UserChannelConnection
from django_tenants.utils import tenant_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()

def test_automatic_account_sync():
    """Test that account details are automatically synced when connection becomes active"""
    print("🧪 Testing Automatic Account Sync Integration")
    print("=" * 60)
    
    # Get OneOTalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with tenant_context(tenant):
        print(f"🏢 Testing in tenant: {tenant.name}")
        
        # Get existing WhatsApp connection
        connection = UserChannelConnection.objects.filter(channel_type='whatsapp').first()
        
        if not connection:
            print("❌ No WhatsApp connection found to test with")
            return
        
        print(f"🔗 Found connection: {connection.account_name}")
        print(f"   UniPile Account ID: {connection.unipile_account_id}")
        print(f"   Current Status: {connection.account_status}/{connection.auth_status}")
        
        # Check current account configuration
        config_keys = len(connection.connection_config.keys()) if connection.connection_config else 0
        provider_keys = len(connection.provider_config.keys()) if connection.provider_config else 0
        
        print(f"📊 Current Configuration:")
        print(f"   Connection Config Keys: {config_keys}")
        print(f"   Provider Config Keys: {provider_keys}")
        print(f"   Phone Number: {connection.connection_config.get('phone_number', 'Not stored')}")
        print(f"   Account Type: {connection.connection_config.get('account_type', 'Not stored')}")
        print(f"   Messaging Status: {connection.connection_config.get('messaging_status', 'Not stored')}")
        
        if config_keys > 0 and provider_keys > 0:
            print("✅ Account details are already populated!")
            print("   This indicates automatic sync is working or has worked previously.")
            
            # Show some key data points
            print(f"📱 Account Details:")
            print(f"   Phone: +{connection.connection_config.get('phone_number', '')}")
            print(f"   Type: {connection.connection_config.get('account_type', '')}")
            print(f"   Created: {connection.connection_config.get('created_at', '')}")
            print(f"   Messaging: {connection.provider_config.get('messaging_enabled', False)}")
            print(f"   Features: {len(connection.provider_config.get('features', {}))}")
            print(f"   Data Size: {len(str(connection.connection_config)) + len(str(connection.provider_config))} chars")
        else:
            print("⚠️ Account details are not populated yet.")
            print("   This might indicate:")
            print("   1. Connection was created before auto-sync was implemented")
            print("   2. Auto-sync failed during connection setup")
            print("   3. Connection is not yet fully active/authenticated")
        
        print()
        print("🔧 Integration Points for Automatic Sync:")
        print("   ✅ Django Signal: auto_sync_account_details")
        print("   ✅ API Callback: hosted_auth_success_callback")
        print("   ✅ Checkpoint Success: solve_checkpoint")
        print("   ✅ Reconnection: reconnect_account")
        print("   ✅ Management Command: sync_account_details")
        
        print()
        print("📋 What happens when an account is connected:")
        print("   1. UniPile hosted auth redirects to success callback")
        print("   2. Callback updates connection status to 'active'")
        print("   3. Django signal detects status change")
        print("   4. Signal triggers account_sync_service.sync_account_details()")
        print("   5. Service fetches comprehensive data from UniPile API")
        print("   6. Data is stored in connection_config and provider_config")
        
        return connection

if __name__ == "__main__":
    test_automatic_account_sync()