#!/usr/bin/env python
"""
Test that both direction detection and attendee detection are properly using account owner information
"""
import os
import sys
import django
import asyncio
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from tenants.models import Tenant
from django_tenants.utils import schema_context
from communications.models import Channel, UserChannelConnection, Message, ChatAttendee
from authentication.models import CustomUser
# Not needed for this test
from communications.utils.message_direction import determine_message_direction
from communications.utils.account_owner_detection import AccountOwnerDetector

async def test_direction_and_attendee():
    """Test both direction detection and attendee detection"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print(f"\n🔍 Testing Direction & Attendee Detection for tenant: {tenant.name}")
        
        # Get test user
        user = CustomUser.objects.get(email='josh@oneodigital.com')
        print(f"✅ User: {user.email}")
        
        # Get WhatsApp channel
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        print(f"✅ Channel: {channel.name} ({channel.id})")
        
        # Get connection to extract account identifier
        connection = UserChannelConnection.objects.filter(
            user=user,
            channel=channel
        ).first()
        
        if not connection:
            print("❌ No connection found")
            return
            
        account_identifier = connection.connection_config.get('phone_number')
        print(f"📞 Account identifier (business phone): {account_identifier}")
        
        # Test 1: Check AccountOwnerDetector
        print("\n📋 Test 1: AccountOwnerDetector")
        detector = AccountOwnerDetector('whatsapp', account_identifier)
        
        # Simulate owner data
        owner_data = {
            'phone': account_identifier,
            'id': account_identifier,
            'name': 'Business Account'
        }
        
        # Simulate customer data
        customer_data = {
            'phone': '+1234567890',
            'id': '+1234567890',
            'name': 'Customer'
        }
        
        is_owner = detector.is_account_owner(owner_data)
        is_customer = detector.is_account_owner(customer_data)
        
        print(f"  Owner detection: {is_owner} (should be True)")
        print(f"  Customer detection: {is_customer} (should be False)")
        
        # Test 2: Check message direction
        print("\n📋 Test 2: Message Direction Detection")
        
        # Simulate message from owner
        owner_message = {
            'sender': owner_data,
            'text': 'Hello from business',
            'id': 'msg_001'
        }
        
        # Simulate message from customer
        customer_message = {
            'sender': customer_data,
            'text': 'Hello from customer',
            'id': 'msg_002'
        }
        
        owner_direction = determine_message_direction(owner_message, 'whatsapp', account_identifier)
        customer_direction = determine_message_direction(customer_message, 'whatsapp', account_identifier)
        
        print(f"  Owner message direction: {owner_direction} (should be 'out')")
        print(f"  Customer message direction: {customer_direction} (should be 'in')")
        
        # Test 3: Check attendees in database
        print("\n📋 Test 3: Attendee Database Check")
        
        attendees = ChatAttendee.objects.filter(channel=channel)
        owner_attendees = []
        customer_attendees = []
        
        for attendee in attendees:
            if attendee.is_self:
                owner_attendees.append(attendee)
            else:
                customer_attendees.append(attendee)
        
        print(f"  Total attendees: {attendees.count()}")
        print(f"  Owner attendees (is_self=True): {len(owner_attendees)}")
        print(f"  Customer attendees (is_self=False): {len(customer_attendees)}")
        
        if owner_attendees:
            print(f"  Owner example: {owner_attendees[0].name} ({owner_attendees[0].provider_id})")
        if customer_attendees:
            print(f"  Customer example: {customer_attendees[0].name} ({customer_attendees[0].provider_id})")
        
        # Test 4: Check message directions in database
        print("\n📋 Test 4: Message Direction Database Check")
        
        messages = Message.objects.filter(channel=channel).order_by('-created_at')[:20]
        outbound_count = messages.filter(direction='out').count()
        inbound_count = messages.filter(direction='in').count()
        
        print(f"  Total recent messages: {messages.count()}")
        print(f"  Outbound messages: {outbound_count}")
        print(f"  Inbound messages: {inbound_count}")
        
        # Show some examples
        for msg in messages[:5]:
            sender_name = "Unknown"
            if msg.sender:
                sender_name = msg.sender.name
                is_self = msg.sender.is_self
            elif msg.metadata:
                sender_name = msg.metadata.get('attendee_name', 'Unknown')
                is_self = msg.metadata.get('is_self', False)
            else:
                is_self = False
            
            print(f"  - {msg.direction}: '{msg.content[:50]}...' from {sender_name} (is_self={is_self})")
        
        print("\n✅ Direction and Attendee Detection Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_direction_and_attendee())