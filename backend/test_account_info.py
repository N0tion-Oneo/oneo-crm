#!/usr/bin/env python
"""
Test to get account information from UniPile
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Channel, UserChannelConnection
from communications.unipile import UnipileClient
from django.conf import settings
from asgiref.sync import async_to_sync

def test_account_info():
    """Get account info from UniPile"""
    
    with schema_context('oneotalent'):
        print("\n=== UNIPILE ACCOUNT INFO TEST ===\n")
        
        # Initialize UniPile client
        dsn = getattr(settings, 'UNIPILE_DSN', 'https://api1.unipile.com:13111')
        access_token = settings.UNIPILE_API_KEY
        
        client = UnipileClient(dsn=dsn, access_token=access_token)
        
        # Get account info
        account_id = 'mp9Gis3IRtuh9V5oSxZdSA'
        
        print(f"Fetching account info for: {account_id}")
        
        try:
            # Get account details
            account_info = async_to_sync(client.account.get_account)(account_id)
            
            print("\nAccount Information:")
            print(json.dumps(account_info, indent=2))
            
            # Extract key fields
            if account_info:
                print("\n--- Key Fields ---")
                print(f"Name: {account_info.get('name')}")
                print(f"Type: {account_info.get('type')}")
                print(f"Provider: {account_info.get('provider')}")
                
                # Check for phone number in various fields
                phone = (
                    account_info.get('phone') or
                    account_info.get('phone_number') or
                    account_info.get('identifier') or
                    account_info.get('username')
                )
                print(f"Phone/Identifier: {phone}")
                
                # Check provider_id which might have the WhatsApp ID
                provider_id = account_info.get('provider_id')
                print(f"Provider ID: {provider_id}")
                
                # Check metadata
                metadata = account_info.get('metadata', {})
                if metadata:
                    print(f"Metadata: {json.dumps(metadata, indent=2)}")
        
        except Exception as e:
            print(f"Error getting account info: {e}")
            
        # Now let's update the connection with proper account identifier
        print("\n--- Updating Connection ---")
        conn = UserChannelConnection.objects.filter(
            unipile_account_id=account_id
        ).first()
        
        if conn:
            # Extract phone from account name
            import re
            match = re.search(r'\((\+?\d+)\)', conn.account_name)
            if match:
                phone_number = match.group(1)
                if not phone_number.startswith('+'):
                    phone_number = '+' + phone_number
                
                print(f"Extracted phone number: {phone_number}")
                
                # Update connection config
                if not conn.connection_config:
                    conn.connection_config = {}
                
                conn.connection_config['account_phone'] = phone_number
                conn.connection_config['account_identifier'] = phone_number + '@s.whatsapp.net'
                conn.save()
                
                print(f"✅ Updated connection config with account phone: {phone_number}")
                
                # Also update channel
                channel = Channel.objects.filter(
                    unipile_account_id=account_id
                ).first()
                
                if channel:
                    if not channel.connection_config:
                        channel.connection_config = {}
                    
                    channel.connection_config['account_phone'] = phone_number
                    channel.connection_config['account_identifier'] = phone_number + '@s.whatsapp.net'
                    channel.save()
                    
                    print(f"✅ Updated channel config with account phone: {phone_number}")

if __name__ == "__main__":
    test_account_info()