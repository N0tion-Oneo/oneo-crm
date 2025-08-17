#!/usr/bin/env python3
"""
Comprehensive WhatsApp testing with UniPile - Test connection, metadata, and message flow
"""

import os
import django
import asyncio
import json
import requests
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import UserChannelConnection, Message, ChannelType
from communications.unipile_sdk import unipile_service, UnipileClient
from django.conf import settings

async def test_whatsapp_connection():
    """Test WhatsApp connection via hosted auth"""
    print("🔗 TESTING WHATSAPP HOSTED AUTHENTICATION")
    print("=" * 60)
    
    try:
        client = unipile_service.get_client()
        
        # Test hosted auth link for WhatsApp
        hosted_result = await client.account.request_hosted_link(
            providers='whatsapp',
            success_redirect_url='https://oneocrm.com/auth/success',
            failure_redirect_url='https://oneocrm.com/auth/error',
            name='WhatsApp Test Connection',
            notify_url='https://webhooks.oneocrm.com/webhooks/unipile/'
        )
        
        print("✅ WhatsApp hosted auth link created:")
        print(json.dumps(hosted_result, indent=2))
        
        # Extract the hosted auth URL
        hosted_url = hosted_result.get('hosted_link_url', hosted_result.get('url', ''))
        if hosted_url:
            print(f"\n🌐 Visit this URL to connect WhatsApp:")
            print(f"   {hosted_url}")
            print(f"\n📱 Instructions:")
            print(f"   1. Open the URL above in your browser")
            print(f"   2. Scan the QR code with WhatsApp")
            print(f"   3. Complete the authentication")
            print(f"   4. Check webhook for account creation notification")
        
        return hosted_result
        
    except Exception as e:
        print(f"❌ WhatsApp hosted auth failed: {e}")
        return None

async def test_whatsapp_accounts():
    """Test getting WhatsApp accounts and their metadata"""
    print("\n📱 TESTING WHATSAPP ACCOUNTS")
    print("=" * 40)
    
    try:
        client = unipile_service.get_client()
        
        # Get all accounts
        accounts = await client.account.get_accounts()
        
        whatsapp_accounts = []
        for account in accounts:
            if account.get('provider', '').lower() == 'whatsapp':
                whatsapp_accounts.append(account)
        
        print(f"Found {len(whatsapp_accounts)} WhatsApp accounts")
        
        for account in whatsapp_accounts:
            print(f"\n📱 WhatsApp Account Details:")
            print(json.dumps(account, indent=2))
            
            # Test getting specific account details
            account_id = account.get('id')
            if account_id:
                try:
                    detailed_account = await client.account.get_account(account_id)
                    print(f"\n📋 Detailed Account Info:")
                    print(json.dumps(detailed_account, indent=2))
                except Exception as e:
                    print(f"❌ Failed to get detailed account info: {e}")
        
        return whatsapp_accounts
        
    except Exception as e:
        print(f"❌ Failed to get WhatsApp accounts: {e}")
        return []

async def test_whatsapp_chats(account_id):
    """Test getting WhatsApp chats and their metadata"""
    print(f"\n💬 TESTING WHATSAPP CHATS FOR ACCOUNT: {account_id}")
    print("=" * 60)
    
    try:
        client = unipile_service.get_client()
        
        # Get chats for the account
        chats_response = await client.messaging.get_all_chats(
            account_id=account_id,
            limit=10
        )
        
        print(f"📋 Chats Response Structure:")
        print(json.dumps(chats_response, indent=2))
        
        # Extract chats from response
        chats = chats_response.get('items', chats_response.get('chats', []))
        
        print(f"\nFound {len(chats)} chats")
        
        for i, chat in enumerate(chats[:3]):  # Show first 3 chats
            print(f"\n💬 Chat {i+1} Details:")
            print(json.dumps(chat, indent=2))
            
            # Test getting chat attendees
            chat_id = chat.get('id')
            if chat_id:
                try:
                    attendees = await client.messaging.get_chat_attendees(chat_id)
                    print(f"\n👥 Chat Attendees:")
                    print(json.dumps(attendees, indent=2))
                except Exception as e:
                    print(f"❌ Failed to get chat attendees: {e}")
        
        return chats
        
    except Exception as e:
        print(f"❌ Failed to get WhatsApp chats: {e}")
        return []

async def test_whatsapp_messages(account_id, chat_id=None):
    """Test getting WhatsApp messages and their metadata"""
    print(f"\n📩 TESTING WHATSAPP MESSAGES")
    print("=" * 50)
    
    try:
        client = unipile_service.get_client()
        
        # Get messages for the account
        params = {
            'account_id': account_id,
            'limit': 5
        }
        
        if chat_id:
            params['chat_id'] = chat_id
        
        messages_response = await client.messaging.get_all_messages(**params)
        
        print(f"📋 Messages Response Structure:")
        print(json.dumps(messages_response, indent=2))
        
        # Extract messages from response
        messages = messages_response.get('items', messages_response.get('messages', []))
        
        print(f"\nFound {len(messages)} messages")
        
        for i, message in enumerate(messages):
            print(f"\n📩 Message {i+1} Details:")
            print(json.dumps(message, indent=2))
            
            # Analyze message structure
            print(f"\n🔍 Message Analysis:")
            print(f"   ID: {message.get('id', 'N/A')}")
            print(f"   Type: {message.get('type', 'N/A')}")
            print(f"   Content: {message.get('text', message.get('content', 'N/A'))[:50]}...")
            print(f"   From: {message.get('from', 'N/A')}")
            print(f"   To: {message.get('to', 'N/A')}")
            print(f"   Timestamp: {message.get('timestamp', message.get('created_at', 'N/A'))}")
            print(f"   Attachments: {len(message.get('attachments', []))}")
            print(f"   Metadata: {message.get('metadata', {})}")
        
        return messages
        
    except Exception as e:
        print(f"❌ Failed to get WhatsApp messages: {e}")
        return []

async def test_whatsapp_attendees(account_id):
    """Test getting WhatsApp attendees (contacts) and their metadata"""
    print(f"\n👥 TESTING WHATSAPP ATTENDEES")
    print("=" * 50)
    
    try:
        client = unipile_service.get_client()
        
        # Get attendees for the account
        attendees_response = await client.messaging.get_all_attendees(
            account_id=account_id,
            limit=10
        )
        
        print(f"📋 Attendees Response Structure:")
        print(json.dumps(attendees_response, indent=2))
        
        # Extract attendees from response
        attendees = attendees_response.get('items', attendees_response.get('attendees', []))
        
        print(f"\nFound {len(attendees)} attendees")
        
        for i, attendee in enumerate(attendees[:5]):  # Show first 5
            print(f"\n👤 Attendee {i+1} Details:")
            print(json.dumps(attendee, indent=2))
            
            # Analyze attendee structure
            print(f"\n🔍 Attendee Analysis:")
            print(f"   ID: {attendee.get('id', 'N/A')}")
            print(f"   Name: {attendee.get('name', 'N/A')}")
            print(f"   Phone: {attendee.get('phone', 'N/A')}")
            print(f"   Email: {attendee.get('email', 'N/A')}")
            print(f"   Profile Picture: {attendee.get('profile_picture', attendee.get('picture', 'N/A'))}")
            print(f"   Status: {attendee.get('status', 'N/A')}")
            print(f"   Metadata: {attendee.get('metadata', {})}")
        
        return attendees
        
    except Exception as e:
        print(f"❌ Failed to get WhatsApp attendees: {e}")
        return []

async def test_send_whatsapp_message(account_id, chat_id):
    """Test sending a WhatsApp message"""
    print(f"\n📤 TESTING SEND WHATSAPP MESSAGE")
    print("=" * 50)
    
    try:
        client = unipile_service.get_client()
        
        # Test message content
        test_message = f"Test message from Oneo CRM - {datetime.now().strftime('%H:%M:%S')}"
        
        # Send message
        result = await client.messaging.send_message(
            chat_id=chat_id,
            text=test_message
        )
        
        print(f"📤 Send Result:")
        print(json.dumps(result, indent=2))
        
        # Analyze result
        if result.get('id'):
            print(f"✅ Message sent successfully!")
            print(f"   Message ID: {result.get('id')}")
            print(f"   Chat ID: {result.get('chat_id', chat_id)}")
            print(f"   Content: {test_message}")
        else:
            print(f"❌ Message send failed: {result}")
        
        return result
        
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {e}")
        return None

def test_webhook_structure():
    """Show example WhatsApp webhook structures"""
    print(f"\n📡 WHATSAPP WEBHOOK STRUCTURES")
    print("=" * 50)
    
    example_webhooks = {
        "message_received": {
            "event_type": "message.received",
            "account_id": "whatsapp_account_123",
            "message": {
                "id": "msg_456",
                "chat_id": "chat_789",
                "type": "text",
                "text": "Hello from WhatsApp!",
                "from": "+1234567890",
                "to": "+0987654321",
                "timestamp": "2024-01-15T10:30:00Z",
                "attachments": [],
                "metadata": {
                    "sender_attendee_id": "attendee_123",
                    "chat_type": "individual",
                    "message_source": "whatsapp"
                }
            }
        },
        "account_connected": {
            "event_type": "creation_success",
            "account_id": "whatsapp_account_123",
            "provider": "whatsapp",
            "account": {
                "id": "whatsapp_account_123",
                "provider": "whatsapp",
                "phone_number": "+1234567890",
                "display_name": "Business Account",
                "verified": True,
                "business_profile": {
                    "description": "My Business",
                    "category": "retail",
                    "address": "123 Main St"
                }
            }
        }
    }
    
    for event_type, webhook_data in example_webhooks.items():
        print(f"\n📡 {event_type.title()} Webhook:")
        print(json.dumps(webhook_data, indent=2))

async def check_existing_whatsapp_data():
    """Check existing WhatsApp data in database"""
    print(f"\n🗄️ CHECKING EXISTING WHATSAPP DATA")
    print("=" * 50)
    
    with schema_context('demo'):  # Check demo tenant
        # Check connections
        connections = UserChannelConnection.objects.filter(
            channel_type=ChannelType.WHATSAPP
        )
        
        print(f"📱 WhatsApp Connections: {connections.count()}")
        for conn in connections:
            print(f"   - {conn.account_name} ({conn.account_status})")
            print(f"     Account ID: {conn.unipile_account_id}")
            print(f"     Auth Status: {conn.auth_status}")
            print(f"     Last Sync: {conn.last_sync_at}")
        
        # Check messages
        messages = Message.objects.filter(
            channel__channel_type=ChannelType.WHATSAPP
        )[:5]
        
        print(f"\n📩 WhatsApp Messages: {messages.count()}")
        for msg in messages:
            print(f"   - {msg.direction}: '{msg.content[:30]}...'")
            print(f"     From: {msg.contact_email}")
            print(f"     Metadata: {msg.metadata}")

async def main():
    """Main test function"""
    print("🚀 COMPREHENSIVE WHATSAPP TESTING WITH UNIPILE")
    print("=" * 80)
    
    # Check existing data first
    await check_existing_whatsapp_data()
    
    # Test connection creation
    await test_whatsapp_connection()
    
    # Test getting accounts
    whatsapp_accounts = await test_whatsapp_accounts()
    
    if whatsapp_accounts:
        account_id = whatsapp_accounts[0].get('id')
        print(f"\n🎯 Using account ID: {account_id}")
        
        # Test getting chats
        chats = await test_whatsapp_chats(account_id)
        
        # Test getting messages
        messages = await test_whatsapp_messages(account_id)
        
        # Test getting attendees
        attendees = await test_whatsapp_attendees(account_id)
        
        # Test sending message if we have a chat
        if chats:
            chat_id = chats[0].get('id')
            if chat_id:
                await test_send_whatsapp_message(account_id, chat_id)
    else:
        print("\n⚠️ No WhatsApp accounts found. Please:")
        print("   1. Connect a WhatsApp account first using hosted auth")
        print("   2. Wait for the webhook to confirm account creation")
        print("   3. Re-run this test")
    
    # Show webhook structures
    test_webhook_structure()
    
    print(f"\n✅ WHATSAPP TESTING COMPLETE")
    print("=" * 50)

if __name__ == '__main__':
    asyncio.run(main())