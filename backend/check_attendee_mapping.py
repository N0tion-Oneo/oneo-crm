#!/usr/bin/env python3
import os
import django
from pathlib import Path
import sys

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import tenant_context
from tenants.models import Tenant
from communications.models import ChatAttendee, Channel

tenant = Tenant.objects.get(schema_name='oneotalent')
with tenant_context(tenant):
    channel = Channel.objects.filter(channel_type='whatsapp').first()
    
    # Check if we have an attendee with this provider_id
    target_provider_id = '27845855518@s.whatsapp.net'
    attendee = ChatAttendee.objects.filter(
        channel=channel, 
        provider_id=target_provider_id
    ).first()
    
    if attendee:
        print(f'✅ Found attendee: "{attendee.name}" (provider_id: {attendee.provider_id})')
    else:
        print(f'❌ No attendee found with provider_id: {target_provider_id}')
        print(f'📋 Available attendees with real names:')
        for att in ChatAttendee.objects.filter(channel=channel).exclude(name__contains='@s.whatsapp.net')[:10]:
            print(f'  - "{att.name}" (provider_id: {att.provider_id})')