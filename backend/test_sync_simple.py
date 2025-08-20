#!/usr/bin/env python3
"""
Simple sync test using Django management command context
"""
import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import tenant_context, schema_context
from tenants.models import Tenant
from communications.models import Channel, Conversation, ChatAttendee

def test_sync_results():
    """Check current state after sync"""
    
    # Get tenant context
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with tenant_context(tenant):
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
            
        print(f"📊 Current sync state for {channel.name}:")
        
        # Count attendees
        attendees_count = ChatAttendee.objects.filter(channel=channel).count()
        print(f"  - ChatAttendees: {attendees_count}")
        
        # Count conversations with messages
        conversations_with_messages = Conversation.objects.filter(
            channel=channel,
            messages__isnull=False
        ).distinct()
        
        print(f"  - Conversations with messages: {conversations_with_messages.count()}")
        
        # Show conversation names
        for conv in conversations_with_messages[:3]:  # Show first 3
            message_count = conv.messages.count()
            print(f"    - '{conv.subject}' ({message_count} messages)")
            
        # Check if we have the problematic conversation
        problem_conv = Conversation.objects.filter(
            channel=channel,
            external_thread_id='Koj4tacYXrii5kAkW86dNw'
        ).first()
        
        if problem_conv:
            print(f"\n🔍 Problem conversation analysis:")
            print(f"  - Subject: '{problem_conv.subject}'")
            print(f"  - Messages: {problem_conv.messages.count()}")
            print(f"  - Metadata attendees: {problem_conv.metadata.get('attendees', [])}")
            
            # Check if attendee exists for this conversation
            # From our debug, this chat has provider_id: "27845855518@s.whatsapp.net"
            target_provider_id = "27845855518@s.whatsapp.net"
            attendee = ChatAttendee.objects.filter(
                channel=channel,
                provider_id=target_provider_id
            ).first()
            
            if attendee:
                print(f"  - ✅ Matching attendee found: '{attendee.name}'")
            else:
                print(f"  - ❌ No attendee found for provider_id: {target_provider_id}")

if __name__ == "__main__":
    test_sync_results()