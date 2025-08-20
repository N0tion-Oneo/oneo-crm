#!/usr/bin/env python3
"""
Test the specific attendee retrieval approach
"""
import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import tenant_context
from tenants.models import Tenant
from communications.models import Channel, Conversation, ChatAttendee
from communications.services.comprehensive_sync import comprehensive_sync_service

def test_before_after():
    """Test the specific attendee sync improvement"""
    
    # Get tenant context
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with tenant_context(tenant):
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        
        print("📊 BEFORE improved sync:")
        
        # Get the problem conversation
        problem_conv = Conversation.objects.filter(
            channel=channel,
            external_thread_id='Koj4tacYXrii5kAkW86dNw'
        ).first()
        
        if problem_conv:
            print(f"  - Subject: '{problem_conv.subject}'")
            print(f"  - Messages: {problem_conv.messages.count()}")
            print(f"  - Attendees in metadata: {len(problem_conv.metadata.get('attendees', []))}")
        
        # Check if we have the attendee
        target_provider_id = "27845855518@s.whatsapp.net"
        attendee = ChatAttendee.objects.filter(
            channel=channel,
            provider_id=target_provider_id
        ).first()
        
        if attendee:
            print(f"  - ✅ Attendee exists: '{attendee.name}'")
        else:
            print(f"  - ❌ Missing attendee for: {target_provider_id}")

if __name__ == "__main__":
    test_before_after()