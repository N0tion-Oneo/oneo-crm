#!/usr/bin/env python
"""
Check if account owner exists as an attendee
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Channel, ChatAttendee, UserChannelConnection

def check_account_owner_attendee():
    """Check if account owner exists as an attendee"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Checking Account Owner Attendee")
        print("=" * 60)
        
        # Get the WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        
        print(f"✅ Channel: {channel.name}")
        
        # Get the connection to find the account phone
        connection = UserChannelConnection.objects.filter(
            unipile_account_id=channel.unipile_account_id,
            channel_type='whatsapp'
        ).first()
        
        if connection and connection.connection_config:
            account_phone = connection.connection_config.get('phone_number')
            print(f"📞 Account phone: {account_phone}")
            
            # Look for attendee with this phone
            if account_phone:
                # Try different formats
                phone_normalized = account_phone.replace('+', '')
                provider_id = f"{phone_normalized}@s.whatsapp.net"
                
                # Search for account owner attendee
                owner_attendees = ChatAttendee.objects.filter(
                    channel=channel,
                    is_self=True
                )
                
                print(f"\n👥 Attendees marked as is_self=True:")
                for att in owner_attendees:
                    print(f"   - {att.name}")
                    print(f"     External ID: {att.external_attendee_id}")
                    print(f"     Provider ID: {att.provider_id}")
                    print(f"     Phone: {att.metadata.get('phone_number') if att.metadata else 'N/A'}")
                
                # Search by provider_id
                by_provider = ChatAttendee.objects.filter(
                    channel=channel,
                    provider_id=provider_id
                ).first()
                
                if by_provider:
                    print(f"\n✅ Found attendee by provider_id ({provider_id}):")
                    print(f"   Name: {by_provider.name}")
                    print(f"   Is self: {by_provider.is_self}")
                else:
                    print(f"\n❌ No attendee found with provider_id: {provider_id}")
                
                # Search by external_id (phone number without @)
                by_external = ChatAttendee.objects.filter(
                    channel=channel,
                    external_attendee_id=phone_normalized
                ).first()
                
                if by_external:
                    print(f"\n✅ Found attendee by external_id ({phone_normalized}):")
                    print(f"   Name: {by_external.name}")
                    print(f"   Is self: {by_external.is_self}")
                else:
                    print(f"\n❌ No attendee found with external_id: {phone_normalized}")
                
                # Check all attendees with this phone in metadata
                with_phone = ChatAttendee.objects.filter(
                    channel=channel,
                    metadata__phone_number=account_phone
                )
                
                print(f"\n👥 Attendees with phone {account_phone} in metadata:")
                for att in with_phone:
                    print(f"   - {att.name} (is_self={att.is_self})")
        
        # List all attendees to see what we have
        print(f"\n📋 All attendees in channel (first 10):")
        all_attendees = ChatAttendee.objects.filter(channel=channel).order_by('name')[:10]
        for att in all_attendees:
            print(f"   - {att.name}")
            print(f"     External ID: {att.external_attendee_id}")
            print(f"     Is self: {att.is_self}")

if __name__ == "__main__":
    check_account_owner_attendee()