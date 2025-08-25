#!/usr/bin/env python
"""
Test complete webhook flow with centralized account owner detection
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Channel, UserChannelConnection, ChatAttendee, Message, Conversation

# Import the handler directly from the file path
import importlib.util
spec = importlib.util.spec_from_file_location(
    'webhook_handlers', 
    '/Users/joshcowan/Oneo CRM/backend/communications/webhooks/handlers.py'
)
handlers_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handlers_module)
UnipileWebhookHandler = handlers_module.UnipileWebhookHandler

def test_webhook_flow():
    """Test complete webhook flow with attendee creation"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Testing Complete Webhook Flow")
        print("=" * 60)
        
        # Get the WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        
        print(f"✅ Channel: {channel.name}")
        
        # Get the connection
        connection = UserChannelConnection.objects.filter(
            unipile_account_id=channel.unipile_account_id,
            channel_type='whatsapp'
        ).first()
        
        if not connection:
            print("❌ No connection found")
            return
            
        stored_phone = connection.connection_config.get('phone_number')
        print(f"✅ Business phone: {stored_phone}")
        
        # Clean up any existing test messages
        test_message_id = "test_msg_12345"
        test_conversation_id = "test_conv_12345"
        
        # Delete test conversation and messages
        Conversation.objects.filter(external_thread_id=test_conversation_id).delete()
        Message.objects.filter(external_message_id=test_message_id).delete()
        
        print("\n" + "=" * 60)
        print("1️⃣  SIMULATING INBOUND MESSAGE WEBHOOK")
        print("=" * 60)
        
        # Create webhook data for an inbound message from a customer
        webhook_data = {
            'account_id': channel.unipile_account_id,
            'message_id': test_message_id,
            'id': test_message_id,
            'text': 'Hello, I need help with my order',
            'from': '+1234567890',  # Customer phone
            'sender': {
                'phone': '+1234567890',
                'name': 'John Customer',
                'id': '+1234567890'
            },
            'conversation_id': test_conversation_id,
            'timestamp': datetime.now().isoformat()
        }
        
        print("📨 Webhook data:")
        print(f"   From: {webhook_data['from']} (Customer)")
        print(f"   Message: {webhook_data['text']}")
        
        # Initialize webhook handler
        handler = UnipileWebhookHandler()
        
        # Process the webhook
        result = handler.handle_message_received(channel.unipile_account_id, webhook_data)
        
        print("\n✅ Webhook processing result:")
        print(f"   Success: {result.get('success')}")
        print(f"   Message ID: {result.get('message_id')}")
        print(f"   Conversation ID: {result.get('conversation_id')}")
        
        # Verify the message was created
        if result.get('success'):
            message = Message.objects.filter(external_message_id=test_message_id).first()
            if message:
                print("\n📧 Message created:")
                print(f"   ID: {message.id}")
                print(f"   Direction: {message.direction}")
                print(f"   Content: {message.content}")
                print(f"   Has sender: {'Yes' if message.sender else 'No'}")
                
                if message.sender:
                    print(f"\n👤 Sender attendee:")
                    print(f"   Name: {message.sender.name}")
                    print(f"   Phone: {message.sender.metadata.get('phone_number') if message.sender.metadata else 'N/A'}")
                    print(f"   Is self: {message.sender.is_self}")
                    print(f"   External ID: {message.sender.external_attendee_id}")
            else:
                print("❌ Message not found in database")
        else:
            print(f"❌ Webhook processing failed: {result.get('error')}")
        
        print("\n" + "=" * 60)
        print("2️⃣  SIMULATING OUTBOUND MESSAGE WEBHOOK")
        print("=" * 60)
        
        # Create webhook data for an outbound message from business
        outbound_message_id = "test_out_msg_12345"
        outbound_webhook_data = {
            'account_id': channel.unipile_account_id,
            'message_id': outbound_message_id,
            'id': outbound_message_id,
            'text': 'Hi John, we can help you with that order',
            'from': stored_phone,  # Business phone
            'sender': {
                'phone': stored_phone,
                'name': 'Business Support',
                'id': stored_phone
            },
            'is_sender': 1,  # Indicates message is from account owner
            'conversation_id': test_conversation_id,
            'timestamp': datetime.now().isoformat()
        }
        
        print("📨 Outbound webhook data:")
        print(f"   From: {outbound_webhook_data['from']} (Business)")
        print(f"   Message: {outbound_webhook_data['text']}")
        
        # Process the outbound webhook
        outbound_result = handler.handle_message_received(channel.unipile_account_id, outbound_webhook_data)
        
        print("\n✅ Outbound webhook processing result:")
        print(f"   Success: {outbound_result.get('success')}")
        print(f"   Message ID: {outbound_result.get('message_id')}")
        
        # Verify the outbound message
        if outbound_result.get('success'):
            out_message = Message.objects.filter(external_message_id=outbound_message_id).first()
            if out_message:
                print("\n📧 Outbound message created:")
                print(f"   Direction: {out_message.direction}")
                print(f"   Has sender: {'Yes' if out_message.sender else 'No'}")
                
                if out_message.sender:
                    print(f"\n👤 Business sender attendee:")
                    print(f"   Name: {out_message.sender.name}")
                    print(f"   Is self: {out_message.sender.is_self}")
        
        print("\n" + "=" * 60)
        print("3️⃣  VERIFYING ATTENDEE RECORDS")
        print("=" * 60)
        
        # Check all attendees created
        attendees = ChatAttendee.objects.filter(channel=channel).order_by('-created_at')[:5]
        
        print(f"\n📋 Recent attendees (showing last 5):")
        for attendee in attendees:
            phone = attendee.metadata.get('phone_number') if attendee.metadata else 'N/A'
            print(f"   {attendee.name}: is_self={attendee.is_self}, phone={phone}")
        
        # Check conversation attendees
        conversation = Conversation.objects.filter(external_thread_id=test_conversation_id).first()
        if conversation:
            conv_attendees = conversation.conversation_attendees.all()
            print(f"\n🔗 Conversation attendees ({conv_attendees.count()} total):")
            for ca in conv_attendees:
                print(f"   {ca.attendee.name}: role={ca.role}, active={ca.is_active}")
        
        print("\n" + "=" * 60)
        print("✅ Webhook flow test complete!")
        print("=" * 60)

if __name__ == "__main__":
    test_webhook_flow()