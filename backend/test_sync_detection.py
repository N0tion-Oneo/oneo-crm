#!/usr/bin/env python
"""
Quick test to verify attendee and direction detection are working
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Channel, ChatAttendee, Message
from communications.utils.account_owner_detection import AccountOwnerDetector
from communications.utils.message_direction import determine_message_direction

# Switch to oneotalent schema
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    print("\n🔍 Testing WhatsApp Sync Detection")
    
    # Get WhatsApp channel
    channel = Channel.objects.filter(channel_type='whatsapp').first()
    if not channel:
        print("❌ No WhatsApp channel found")
        exit(1)
    
    print(f"✅ Channel: {channel.name}")
    
    # Check attendees
    print("\n📋 Attendee Analysis:")
    attendees = ChatAttendee.objects.filter(channel=channel)
    owner_count = attendees.filter(is_self=True).count()
    customer_count = attendees.filter(is_self=False).count()
    
    print(f"  Total attendees: {attendees.count()}")
    print(f"  Business owners (is_self=True): {owner_count}")
    print(f"  Customers (is_self=False): {customer_count}")
    
    # Show examples
    if owner_count > 0:
        owner = attendees.filter(is_self=True).first()
        print(f"  Owner example: {owner.name} - {owner.provider_id}")
    
    if customer_count > 0:
        customer = attendees.filter(is_self=False).first()
        print(f"  Customer example: {customer.name} - {customer.provider_id}")
    
    # Check message directions
    print("\n📋 Message Direction Analysis:")
    messages = Message.objects.filter(channel=channel)
    outbound = messages.filter(direction='out').count()
    inbound = messages.filter(direction='in').count()
    
    print(f"  Total messages: {messages.count()}")
    print(f"  Outbound (from business): {outbound}")
    print(f"  Inbound (from customers): {inbound}")
    print(f"  Ratio: {outbound}:{inbound}")
    
    # Show recent examples with sender info
    print("\n📋 Recent Message Examples:")
    recent = messages.select_related('sender').order_by('-created_at')[:10]
    
    for msg in recent:
        if msg.sender:
            sender_info = f"{msg.sender.name} (is_self={msg.sender.is_self})"
        else:
            sender_info = "Unknown sender"
        
        content_preview = msg.content[:50] if msg.content else "[No content]"
        print(f"  [{msg.direction:3}] {sender_info}: {content_preview}...")
    
    print("\n✅ Detection test complete!")