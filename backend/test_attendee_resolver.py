#!/usr/bin/env python
"""
Test the attendee resolver for LinkedIn
"""
import os
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection
from communications.record_communications.unipile_integration import AttendeeResolver
from communications.unipile.core.client import UnipileClient
from asgiref.sync import async_to_sync

# Use oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    print("🏢 Testing in tenant: oneotalent")
    
    # Get LinkedIn connection
    linkedin_conn = UserChannelConnection.objects.filter(
        channel_type='linkedin'
    ).first()
    
    if linkedin_conn:
        print(f"\n📡 LinkedIn connection: {linkedin_conn.account_name}")
        print(f"   UniPile Account ID: {linkedin_conn.unipile_account_id}")
        
        # Initialize UniPile client
        from django.conf import settings
        client = UnipileClient(
            dsn=settings.UNIPILE_DSN,
            access_token=settings.UNIPILE_API_KEY
        )
        
        # Initialize attendee resolver
        resolver = AttendeeResolver(client)
        
        # Test identifiers
        identifiers = {
            'linkedin': ['robbiecowan']
        }
        
        print(f"\n🔍 Testing attendee resolution for: {identifiers}")
        
        # Try to resolve attendees
        attendee_map = resolver.resolve_messaging_attendees(
            identifiers=identifiers,
            channel_type='linkedin',
            account_id=linkedin_conn.unipile_account_id
        )
        
        print(f"\n📊 Result:")
        if attendee_map:
            print(f"   ✅ Found {len(attendee_map)} attendees:")
            for provider_id, info in attendee_map.items():
                print(f"      - Provider ID: {provider_id}")
                print(f"        Attendee ID: {info.get('attendee_id')}")
                print(f"        Name: {info.get('name')}")
        else:
            print("   ❌ No attendees found")
            
            # Let's try to fetch the profile directly
            print("\n🔍 Trying direct profile fetch...")
            try:
                profile_response = async_to_sync(client.users.get_user_profile)(
                    user_id='robbiecowan',
                    account_id=linkedin_conn.unipile_account_id
                )
                
                if profile_response:
                    print("   ✅ Profile found:")
                    print(f"      Response: {profile_response}")
                else:
                    print("   ❌ No profile found")
                    
            except Exception as e:
                print(f"   ❌ Error fetching profile: {e}")
                import traceback
                traceback.print_exc()
                
            # Let's also try to list all attendees to see what's available
            print("\n📋 Listing all attendees for this account...")
            try:
                attendees_response = async_to_sync(client.messaging.list_attendees)(
                    account_id=linkedin_conn.unipile_account_id,
                    limit=10
                )
                
                if attendees_response and 'items' in attendees_response:
                    print(f"   Found {len(attendees_response['items'])} attendees:")
                    for att in attendees_response['items'][:5]:
                        print(f"      - Name: {att.get('name')}")
                        print(f"        ID: {att.get('id')}")
                        print(f"        Provider ID: {att.get('provider_id')}")
                else:
                    print("   No attendees found")
                    
            except Exception as e:
                print(f"   ❌ Error listing attendees: {e}")
    else:
        print("❌ No LinkedIn connection found")