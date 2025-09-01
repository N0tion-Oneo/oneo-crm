#!/usr/bin/env python
"""
Simple direct test of email sending
"""
import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection
from communications.channels.email.service import EmailService
from asgiref.sync import async_to_sync

# Get tenant
tenant = Tenant.objects.get(schema_name='oneotalent')
print(f"Tenant: {tenant.name}")

with schema_context(tenant.schema_name):
    # Get Gmail connection
    conn = UserChannelConnection.objects.filter(channel_type='gmail').first()
    print(f"Gmail: {conn.account_name}")
    print(f"UniPile ID: {conn.unipile_account_id}")
    
    # Create service
    service = EmailService()
    
    # Send email - CORRECT FORMAT for UniPile
    result = async_to_sync(service.send_email)(
        account_id=conn.unipile_account_id,
        to=[{'identifier': 'test@example.com', 'display_name': 'Test'}],
        subject=f'Direct Test - {datetime.now().strftime("%H:%M:%S")}',
        body='<p>Direct test email</p>',
        cc=None,
        bcc=None
    )
    
    if result.get('success'):
        print(f"✅ SUCCESS! Tracking: {result.get('tracking_id')}")
    else:
        print(f"❌ Failed: {result.get('error')}")