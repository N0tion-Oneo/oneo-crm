#!/usr/bin/env python3
"""
Debug why the specific attendee is not found
"""
import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import tenant_context
from tenants.models import Tenant
from communications.models import Channel, ChatAttendee

def debug_missing_attendee():
    """Debug why attendee 27845855518@s.whatsapp.net is not found"""
    
    # Get tenant context
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with tenant_context(tenant):
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        
        target_provider_id = "27845855518@s.whatsapp.net"
        # Extract phone number
        target_phone = target_provider_id.split('@')[0]  # "27845855518"
        
        print(f"🔍 Looking for attendee with:")
        print(f"  - Full provider_id: {target_provider_id}")
        print(f"  - Phone number: {target_phone}")
        
        # Check if we have any attendee with similar phone number
        similar_attendees = ChatAttendee.objects.filter(
            channel=channel,
            provider_id__contains=target_phone
        )
        
        print(f"\n📱 Attendees with phone {target_phone}:")
        for attendee in similar_attendees:
            print(f"  - '{attendee.name}' (provider_id: {attendee.provider_id})")
            
        if not similar_attendees.exists():
            print(f"  ❌ No attendees found with phone {target_phone}")
            
        # Check attendees with similar patterns
        print(f"\n🔍 All attendees starting with '278' (South Africa):")
        sa_attendees = ChatAttendee.objects.filter(
            channel=channel,
            provider_id__startswith='278'
        )
        
        for attendee in sa_attendees[:10]:  # First 10
            phone = attendee.provider_id.split('@')[0]
            print(f"  - '{attendee.name}' (phone: {phone})")
            
        # Most similar numbers
        print(f"\n🎯 Most similar phone numbers to {target_phone}:")
        for attendee in ChatAttendee.objects.filter(channel=channel).exclude(name__contains='@'):
            attendee_phone = attendee.provider_id.split('@')[0]
            # Check if phone numbers are similar (same prefix)
            if attendee_phone.startswith('2784') or attendee_phone.startswith('2785'):
                print(f"  - '{attendee.name}' (phone: {attendee_phone})")

if __name__ == "__main__":
    debug_missing_attendee()