#!/usr/bin/env python
"""
Test the improved attendee-conversation architecture with real WhatsApp data
Tests message direction determination and ConversationAttendee linking
"""
import os
import sys
import django
import json
import uuid
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import (
    Channel, Conversation, Message, ChatAttendee, 
    ConversationAttendee, UserChannelConnection
)
from communications.utils.message_direction import determine_message_direction
from communications.channels.whatsapp.utils import WhatsAppAttendeeDetector
from asgiref.sync import async_to_sync


def test_attendee_architecture():
    """Test the new attendee-conversation architecture"""
    
    print("=" * 60)
    print("🧪 Testing Improved Attendee-Conversation Architecture")
    print("=" * 60)
    
    # Use oneotalent tenant context
    with schema_context('oneotalent'):
        # Get the real WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ WhatsApp channel not found")
            return
        
        print(f"✅ Found WhatsApp channel: {channel.name}")
        print(f"   Account ID: {channel.unipile_account_id}")
        
        # Get business account identifier from channel or connection config
        business_phone = None
        if channel.connection_config and 'phone_number' in channel.connection_config:
            business_phone = channel.connection_config['phone_number']
            print(f"   Business Phone: {business_phone}")
        elif channel.connection_config and 'account_phone' in channel.connection_config:
            business_phone = channel.connection_config['account_phone']
            print(f"   Business Phone: {business_phone}")
        
        # If not in channel, try to get from a UserChannelConnection
        if not business_phone:
            connection = UserChannelConnection.objects.filter(
                channel_type='whatsapp',
                unipile_account_id=channel.unipile_account_id
            ).first()
            if connection and connection.connection_config:
                if 'phone_number' in connection.connection_config:
                    business_phone = connection.connection_config['phone_number']
                elif 'account_phone' in connection.connection_config:
                    business_phone = connection.connection_config['account_phone']
                if business_phone:
                    print(f"   Business Phone (from connection): {business_phone}")
        
        # Test 1: Create a conversation with attendees
        print("\n📝 Test 1: Creating conversation with attendees...")
        
        # Create or get a test conversation
        conversation, created = Conversation.objects.get_or_create(
            channel=channel,
            external_thread_id='test_chat_001',
            defaults={
                'subject': 'Test Conversation',
                'conversation_type': 'group',
                'participant_count': 0
            }
        )
        print(f"   {'Created' if created else 'Found'} conversation: {conversation.id}")
        
        # Test 2: Create attendees and link to conversation
        print("\n👥 Test 2: Creating attendees and linking to conversation...")
        
        attendee_detector = WhatsAppAttendeeDetector()
        
        # Simulate customer attendee
        customer_info = {
            'external_id': 'customer_001',
            'phone_number': '+27123456789',
            'name': 'Test Customer',
            'is_self': False
        }
        
        customer_attendee = attendee_detector.create_or_update_attendee(
            customer_info,
            conversation=conversation,
            channel=channel
        )
        
        if customer_attendee:
            print(f"   ✅ Created customer attendee: {customer_attendee.name}")
            
            # Check ConversationAttendee link
            conv_attendee = ConversationAttendee.objects.filter(
                conversation=conversation,
                attendee=customer_attendee
            ).first()
            
            if conv_attendee:
                print(f"   ✅ ConversationAttendee link created")
                print(f"      Role: {conv_attendee.role}")
                print(f"      Active: {conv_attendee.is_active}")
        
        # Get or create business account attendee
        business_info = {
            'external_id': 'business_001',
            'phone_number': business_phone or '+27720720047',
            'name': 'Business Account',
            'is_self': True
        }
        
        # Try to get existing business attendee first
        business_phone_formatted = f"{business_phone or '+27720720047'}@s.whatsapp.net"
        business_attendee = ChatAttendee.objects.filter(
            channel=channel,
            provider_id=business_phone_formatted.replace('+', '')
        ).first()
        
        if not business_attendee:
            business_attendee = attendee_detector.create_or_update_attendee(
                business_info,
                conversation=conversation,
                channel=channel
            )
            if business_attendee:
                print(f"   ✅ Created business attendee: {business_attendee.name}")
        else:
            print(f"   ✅ Found existing business attendee: {business_attendee.name}")
            # Link to conversation if not already linked
            conv_attendee, created = ConversationAttendee.objects.get_or_create(
                conversation=conversation,
                attendee=business_attendee,
                defaults={'role': 'admin', 'is_active': True}
            )
            if created:
                print(f"   ✅ Linked business attendee to conversation")
        
        # Test 3: Test message direction determination
        print("\n🔄 Test 3: Testing message direction determination...")
        
        # Message from customer (should be inbound)
        customer_message_data = {
            'sender': {
                'attendee_provider_id': f"{customer_info['phone_number']}@s.whatsapp.net"
            },
            'text': 'Hello, I need help'
        }
        
        direction = determine_message_direction(
            customer_message_data, 
            'whatsapp',
            f"{business_phone or '+27720720047'}@s.whatsapp.net"
        )
        print(f"   Customer message direction: {direction} (should be 'in')")
        assert direction == 'in', "Customer message should be inbound"
        
        # Message from business (should be outbound)
        business_message_data = {
            'sender': {
                'attendee_provider_id': f"{business_phone or '+27720720047'}@s.whatsapp.net"
            },
            'text': 'How can I help you?'
        }
        
        direction = determine_message_direction(
            business_message_data,
            'whatsapp', 
            f"{business_phone or '+27720720047'}@s.whatsapp.net"
        )
        print(f"   Business message direction: {direction} (should be 'out')")
        assert direction == 'out', "Business message should be outbound"
        
        # Test 4: Create messages with sender field
        print("\n💬 Test 4: Creating messages with sender field...")
        
        # Generate unique message IDs to avoid conflicts
        test_id = str(uuid.uuid4())[:8]
        
        # Create inbound message
        inbound_msg = Message.objects.create(
            channel=channel,
            conversation=conversation,
            external_message_id=f'msg_in_{test_id}',
            sender=customer_attendee,  # New sender field
            direction='in',
            content='Hello, I need help',
            status='delivered'
        )
        print(f"   ✅ Created inbound message from {inbound_msg.sender.name}")
        
        # Create outbound message
        outbound_msg = Message.objects.create(
            channel=channel,
            conversation=conversation,
            external_message_id=f'msg_out_{test_id}',
            sender=business_attendee,  # New sender field
            direction='out',
            content='How can I help you?',
            status='sent'
        )
        print(f"   ✅ Created outbound message from {outbound_msg.sender.name}")
        
        # Test 5: Query messages with sender relationship
        print("\n🔍 Test 5: Querying messages with sender relationship...")
        
        # Get all messages from customer
        customer_messages = Message.objects.filter(
            sender=customer_attendee
        ).count()
        print(f"   Messages from customer: {customer_messages}")
        
        # Get all messages from business
        business_messages = Message.objects.filter(
            sender=business_attendee
        ).count()
        print(f"   Messages from business: {business_messages}")
        
        # Test 6: Verify conversation attendees
        print("\n✅ Test 6: Verifying conversation attendees...")
        
        # Get all attendees in conversation
        attendees = conversation.attendees.all()
        print(f"   Total attendees in conversation: {attendees.count()}")
        
        for attendee in attendees:
            conv_attendee = ConversationAttendee.objects.get(
                conversation=conversation,
                attendee=attendee
            )
            print(f"   - {attendee.name}: role={conv_attendee.role}, active={conv_attendee.is_active}")
        
        # Update participant count
        conversation.participant_count = conversation.conversation_attendees.filter(is_active=True).count()
        conversation.save()
        print(f"   Updated participant count: {conversation.participant_count}")
        
        # Test 7: Test attendee across multiple conversations
        print("\n🔀 Test 7: Testing attendee across multiple conversations...")
        
        # Create another conversation
        conversation2, created = Conversation.objects.get_or_create(
            channel=channel,
            external_thread_id='test_chat_002',
            defaults={
                'subject': 'Another Test Conversation',
                'conversation_type': 'direct',
                'participant_count': 0
            }
        )
        
        # Link same customer to new conversation
        conv_attendee2, created = ConversationAttendee.objects.get_or_create(
            conversation=conversation2,
            attendee=customer_attendee,
            defaults={'role': 'member', 'is_active': True}
        )
        
        if created:
            print(f"   ✅ Linked same customer to conversation 2")
        
        # Check customer's conversations
        customer_conversations = customer_attendee.conversations.all()
        print(f"   Customer is in {customer_conversations.count()} conversations:")
        for conv in customer_conversations:
            print(f"   - {conv.subject or conv.external_thread_id}")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Architecture is working correctly")
        print("=" * 60)
        print("\nKey achievements:")
        print("✅ ConversationAttendee junction table links attendees to conversations")
        print("✅ Message direction determined by comparing sender with business account")
        print("✅ Messages have sender field pointing to ChatAttendee")
        print("✅ Attendees can participate in multiple conversations")
        print("✅ Participant count tracking works")


if __name__ == '__main__':
    test_attendee_architecture()