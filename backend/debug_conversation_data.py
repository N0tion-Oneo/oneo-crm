#!/usr/bin/env python3
"""
Debug conversation data structure for WhatsApp identity separation
"""

import os
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Message, Conversation, Channel

def debug_conversation_structure():
    """Debug the actual conversation data structure"""
    print("🔍 DEBUGGING CONVERSATION DATA STRUCTURE")
    print("=" * 80)
    
    with schema_context('oneotalent'):
        # Get recent WhatsApp conversations
        whatsapp_channels = Channel.objects.filter(channel_type='whatsapp')
        
        if not whatsapp_channels.exists():
            print("❌ No WhatsApp channels found")
            return
        
        print(f"📱 Found {whatsapp_channels.count()} WhatsApp channels")
        
        for channel in whatsapp_channels:
            print(f"\n🔄 Channel: {channel.name}")
            print(f"   ID: {channel.id}")
            print(f"   Account ID: {channel.unipile_account_id}")
            
            # Get conversations for this channel
            conversations = Conversation.objects.filter(
                channel=channel
            ).order_by('-created_at')[:5]
            
            print(f"   Conversations: {conversations.count()}")
            
            for conv in conversations:
                print(f"\n   💬 Conversation: {conv.id}")
                print(f"      Subject: {conv.subject[:50]}...")
                print(f"      Thread ID: {conv.external_thread_id}")
                
                # Get messages for this conversation
                messages = Message.objects.filter(
                    conversation=conv
                ).order_by('-received_at')[:10]
                
                print(f"      Messages: {messages.count()}")
                
                # Analyze each message
                customer_contacts = set()
                business_accounts = set()
                
                for i, msg in enumerate(messages):
                    print(f"\n      📨 Message {i+1}:")
                    print(f"         ID: {msg.id}")
                    print(f"         Contact Email: {msg.contact_email}")
                    print(f"         Direction: {msg.direction}")
                    print(f"         Content: {msg.content[:30]}...")
                    
                    # Check metadata
                    metadata = msg.metadata or {}
                    print(f"         Metadata keys: {list(metadata.keys())}")
                    
                    # Key metadata fields
                    contact_name = metadata.get('contact_name')
                    sender_attendee_id = metadata.get('sender_attendee_id')
                    is_sender = metadata.get('is_sender')
                    chat_id = metadata.get('chat_id')
                    
                    print(f"         Contact Name: {contact_name}")
                    print(f"         Sender Attendee ID: {sender_attendee_id}")
                    print(f"         Is Sender: {is_sender}")
                    print(f"         Chat ID: {chat_id}")
                    
                    # Determine if this is business or customer
                    if msg.contact_email == '27720720047@s.whatsapp.net' or is_sender == 1:
                        business_accounts.add(msg.contact_email)
                        print(f"         🏢 BUSINESS MESSAGE")
                    else:
                        customer_contacts.add((msg.contact_email, contact_name or msg.contact_email))
                        print(f"         👤 CUSTOMER MESSAGE")
                
                print(f"\n      📊 Conversation Analysis:")
                print(f"         Business Accounts: {business_accounts}")
                print(f"         Customer Contacts: {customer_contacts}")
                
                # Show what the last message would resolve to
                last_message = messages[0] if messages else None
                if last_message:
                    print(f"\n      🎯 Last Message Analysis:")
                    print(f"         Contact Email: {last_message.contact_email}")
                    print(f"         Contact Name: {last_message.metadata.get('contact_name')}")
                    
                    is_business = last_message.contact_email == '27720720047@s.whatsapp.net'
                    print(f"         Is Business: {is_business}")
                    
                    if is_business:
                        print("         ⚠️  PROBLEM: Last message is from business!")
                        print("         ⚠️  This would cause incorrect contact display!")
                        
                        # Find customer contact from other messages
                        customer_message = None
                        for msg in messages:
                            if msg.contact_email != '27720720047@s.whatsapp.net':
                                customer_message = msg
                                break
                        
                        if customer_message:
                            print(f"         ✅ Customer found: {customer_message.contact_email}")
                            print(f"         ✅ Customer name: {customer_message.metadata.get('contact_name')}")
                        else:
                            print("         ❌ No customer messages found!")

def show_ideal_conversation_api_structure():
    """Show what the ideal conversation API should return"""
    print(f"\n🎯 IDEAL CONVERSATION API STRUCTURE")
    print("=" * 60)
    
    ideal_structure = {
        "conversations": [
            {
                "id": "conv_123",
                "type": "whatsapp",
                "last_message": {
                    # This could be from business OR customer
                    "content": "Yes, please get the Nivea deodorant",
                    "direction": "outbound",
                    "contact_email": "27720720047@s.whatsapp.net",  # Business
                    "timestamp": "2025-08-16T18:15:00Z"
                },
                # SOLUTION: Include all messages or customer contact separately
                "customer_contact": {
                    "name": "Vanessa",
                    "whatsapp_id": "27849977040@s.whatsapp.net", 
                    "phone_number": "+27849977040",
                    "profile_picture": "wapp://mp9Gis3IRtuh9V5oSxZdSA/27849977040@s.whatsapp.net.jpg"
                },
                # OR: Include recent messages
                "recent_messages": [
                    # Multiple messages to find customer contact
                ],
                "unread_count": 2,
                "participants": [
                    {
                        "name": "Vanessa",  # Should be customer, never business
                        "email": "27849977040@s.whatsapp.net"
                    }
                ]
            }
        ]
    }
    
    print(json.dumps(ideal_structure, indent=2))

def main():
    """Main debug function"""
    debug_conversation_structure()
    show_ideal_conversation_api_structure()
    
    print(f"\n🔧 FIXES NEEDED:")
    print("1. Backend API should include customer_contact in conversation response")
    print("2. OR: Backend API should include recent_messages array")
    print("3. OR: Frontend should load full conversation messages to find customer")
    print("4. WhatsAppIdentityHandler needs access to multiple messages, not just last_message")

if __name__ == '__main__':
    main()