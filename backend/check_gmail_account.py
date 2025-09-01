#!/usr/bin/env python
"""
Check the actual email address of the connected Gmail account
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import UserChannelConnection, Channel

print("=" * 80)
print("GMAIL ACCOUNT DETAILS")
print("=" * 80)

with schema_context('oneotalent'):
    # Get Gmail connections
    gmail_connections = UserChannelConnection.objects.filter(
        channel_type='gmail',
        is_active=True
    )
    
    print(f"\nFound {gmail_connections.count()} Gmail connection(s):")
    
    for conn in gmail_connections:
        print(f"\n📧 Connection: {conn.account_name}")
        print(f"   Account ID: {conn.unipile_account_id}")
        print(f"   Status: {conn.auth_status}")
        print(f"   User: {conn.user.email if conn.user else 'No user'}")
        
        # Check metadata for email address
        if conn.connection_config:
            print(f"   Connection config: {conn.connection_config}")
        if conn.provider_config:
            print(f"   Provider config: {conn.provider_config}")
        # UserChannelConnection doesn't have metadata field
        # The actual email might be stored in the channel or determined from the account
            
    # Also check channels
    print("\n" + "-" * 40)
    print("Gmail Channels:")
    
    gmail_channels = Channel.objects.filter(
        channel_type='gmail'
    )
    
    for channel in gmail_channels:
        print(f"\n📮 Channel: {channel.name}")
        print(f"   Account ID: {channel.unipile_account_id}")
        print(f"   Status: {channel.auth_status}")
        if channel.metadata:
            print(f"   Metadata: {channel.metadata}")
            if 'email' in channel.metadata:
                print(f"   ✉️ Email Address: {channel.metadata.get('email')}")

print("\n" + "=" * 80)