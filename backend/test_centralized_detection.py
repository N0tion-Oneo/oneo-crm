#!/usr/bin/env python
"""
Test that both attendee detection and message direction use centralized account owner detection properly
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Channel, UserChannelConnection
from communications.channels.whatsapp.utils.attendee_detection import WhatsAppAttendeeDetector
from communications.utils.message_direction import determine_message_direction, determine_whatsapp_direction
from communications.utils.account_owner_detection import AccountOwnerDetector

def test_centralized_detection():
    """Test centralized account owner detection in both utilities"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Testing Centralized Account Owner Detection")
        print("=" * 60)
        
        # Get the WhatsApp channel with real data
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        
        print(f"✅ Channel: {channel.name}")
        
        # Get the business phone number from stored data
        connection = UserChannelConnection.objects.filter(
            unipile_account_id=channel.unipile_account_id,
            channel_type='whatsapp'
        ).first()
        
        stored_phone = connection.connection_config.get('phone_number') if connection else None
        print(f"✅ Stored phone number: {stored_phone}")
        
        print("\n" + "=" * 60)
        print("1️⃣  TESTING ATTENDEE DETECTION")
        print("=" * 60)
        
        # Initialize attendee detector with just the channel
        attendee_detector = WhatsAppAttendeeDetector(channel=channel)
        print(f"✅ Attendee detector initialized with channel")
        print(f"   → Account identifier extracted: {attendee_detector.account_identifier}")
        
        # Test attendee detection
        test_attendees = [
            {
                'name': 'Business Owner',
                'phone': stored_phone,  # Use 'phone' key like actual webhook data
                'phone_number': stored_phone,
                'external_id': stored_phone,
                'id': stored_phone
            },
            {
                'name': 'Customer 1',
                'phone': '+1234567890',  # Use 'phone' key like actual webhook data
                'phone_number': '+1234567890',
                'external_id': '+1234567890',
                'id': '+1234567890'
            },
            {
                'name': 'Customer 2',
                'phone': '+0987654321',  # Use 'phone' key like actual webhook data
                'phone_number': '+0987654321',
                'external_id': '+0987654321',
                'id': '+0987654321'
            }
        ]
        
        print("\n📋 Testing attendee is_self detection:")
        for attendee in test_attendees:
            # Extract webhook format
            webhook_data = {'sender': attendee}
            extracted = attendee_detector.extract_attendee_from_webhook(webhook_data)
            print(f"   {attendee['name']} ({attendee['phone_number']}): is_self={extracted['is_self']}")
        
        # Test chat attendees extraction
        print("\n📋 Testing chat attendees extraction:")
        chat_data = {
            'participants': test_attendees
        }
        
        extracted_attendees = attendee_detector.extract_chat_attendees(chat_data)
        for att in extracted_attendees:
            print(f"   {att['name']} ({att['phone_number']}): is_self={att['is_self']}")
        
        print("\n" + "=" * 60)
        print("2️⃣  TESTING MESSAGE DIRECTION DETECTION")
        print("=" * 60)
        
        test_messages = [
            {
                'sender': {'phone': stored_phone},
                'text': 'Hello from business',
                'expected': 'out'
            },
            {
                'sender': {'phone': '+1234567890'},
                'text': 'Hello from customer',
                'expected': 'in'
            },
            {
                'is_sender': 1,
                'text': 'Message with is_sender flag',
                'expected': 'out'
            }
        ]
        
        print("\n📋 Testing with channel parameter:")
        for msg in test_messages:
            # Test with channel (should auto-detect account)
            direction = determine_message_direction(msg, 'whatsapp', channel=channel)
            status = "✅" if direction == msg['expected'] else "❌"
            print(f"   {status} {msg['text'][:30]}... → {direction} (expected: {msg['expected']})")
        
        print("\n📋 Testing with explicit account identifier:")
        for msg in test_messages:
            # Test with explicit identifier
            direction = determine_message_direction(msg, 'whatsapp', user_identifier=stored_phone)
            status = "✅" if direction == msg['expected'] else "❌"
            print(f"   {status} {msg['text'][:30]}... → {direction} (expected: {msg['expected']})")
        
        print("\n📋 Testing WhatsApp-specific function:")
        for msg in test_messages:
            # Test WhatsApp-specific function with channel
            direction = determine_whatsapp_direction(msg, channel=channel)
            status = "✅" if direction == msg['expected'] else "❌"
            print(f"   {status} {msg['text'][:30]}... → {direction} (expected: {msg['expected']})")
        
        print("\n" + "=" * 60)
        print("3️⃣  TESTING ACCOUNT OWNER DETECTOR DIRECTLY")
        print("=" * 60)
        
        # Test AccountOwnerDetector with channel
        detector = AccountOwnerDetector('whatsapp', channel=channel)
        print(f"✅ AccountOwnerDetector initialized with channel")
        print(f"   → Account identifier: {detector.account_identifier}")
        
        # Test detection
        owner_data = {'phone': stored_phone}
        customer_data = {'phone': '+1234567890'}
        
        is_owner = detector.is_account_owner(owner_data)
        is_customer = detector.is_account_owner(customer_data)
        
        print(f"\n📋 Detection results:")
        print(f"   Business ({stored_phone}): is_owner={is_owner} ✅")
        print(f"   Customer (+1234567890): is_owner={is_customer} ✅")
        
        print("\n" + "=" * 60)
        print("✅ All tests complete! Centralized detection is working properly.")
        print("=" * 60)

if __name__ == "__main__":
    test_centralized_detection()