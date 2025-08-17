#!/usr/bin/env python3
"""
Test WhatsApp metadata from UniPile using direct API calls
"""

import requests
import json
import os
from datetime import datetime

# UniPile configuration from environment or hardcoded values
UNIPILE_DSN = os.getenv('UNIPILE_DSN', 'https://your-subdomain.unipile.com')
UNIPILE_API_KEY = os.getenv('UNIPILE_API_KEY', 'your-api-key')

def test_unipile_connection():
    """Test basic UniPile connection"""
    print("🔗 TESTING UNIPILE CONNECTION")
    print("=" * 50)
    
    headers = {
        'X-API-KEY': UNIPILE_API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        # Test basic accounts endpoint
        url = f"{UNIPILE_DSN}/api/v1/accounts"
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            accounts = response.json()
            print(f"✅ Connection successful!")
            print(f"Found {len(accounts)} accounts")
            
            whatsapp_accounts = [acc for acc in accounts if acc.get('provider', '').lower() == 'whatsapp']
            print(f"WhatsApp accounts: {len(whatsapp_accounts)}")
            
            return whatsapp_accounts
        else:
            print(f"❌ Connection failed: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return []

def test_whatsapp_hosted_auth():
    """Test WhatsApp hosted authentication"""
    print("\n📱 TESTING WHATSAPP HOSTED AUTH")
    print("=" * 50)
    
    headers = {
        'X-API-KEY': UNIPILE_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        url = f"{UNIPILE_DSN}/api/v1/hosted/accounts/link"
        
        data = {
            "providers": ["whatsapp"],
            "success_redirect_url": "https://oneocrm.com/auth/success",
            "failure_redirect_url": "https://oneocrm.com/auth/error",
            "name": "WhatsApp Test Connection",
            "notify_url": "https://webhooks.oneocrm.com/webhooks/unipile/"
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✅ Hosted auth created successfully!")
            print(json.dumps(result, indent=2))
            
            hosted_url = result.get('hosted_link_url', result.get('url', ''))
            if hosted_url:
                print(f"\n🌐 Visit this URL to connect WhatsApp:")
                print(f"   {hosted_url}")
            
            return result
        else:
            print(f"❌ Hosted auth failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Hosted auth error: {e}")
        return None

def analyze_whatsapp_account(account):
    """Analyze WhatsApp account metadata"""
    print(f"\n📋 ANALYZING WHATSAPP ACCOUNT: {account.get('id')}")
    print("=" * 60)
    
    print(f"📱 Account Details:")
    print(f"   ID: {account.get('id')}")
    print(f"   Provider: {account.get('provider')}")
    print(f"   Status: {account.get('status')}")
    print(f"   Display Name: {account.get('display_name', 'N/A')}")
    print(f"   Phone Number: {account.get('phone_number', 'N/A')}")
    print(f"   Verified: {account.get('verified', 'N/A')}")
    print(f"   Created: {account.get('created_at', 'N/A')}")
    print(f"   Updated: {account.get('updated_at', 'N/A')}")
    
    # Business profile info
    business_profile = account.get('business_profile', {})
    if business_profile:
        print(f"\n🏢 Business Profile:")
        print(f"   Description: {business_profile.get('description', 'N/A')}")
        print(f"   Category: {business_profile.get('category', 'N/A')}")
        print(f"   Address: {business_profile.get('address', 'N/A')}")
        print(f"   Website: {business_profile.get('website', 'N/A')}")
    
    # Metadata
    metadata = account.get('metadata', {})
    if metadata:
        print(f"\n📊 Metadata:")
        print(json.dumps(metadata, indent=4))

def test_whatsapp_chats(account_id):
    """Test getting WhatsApp chats"""
    print(f"\n💬 TESTING WHATSAPP CHATS")
    print("=" * 50)
    
    headers = {
        'X-API-KEY': UNIPILE_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        url = f"{UNIPILE_DSN}/api/v1/chats"
        params = {
            'account_id': account_id,
            'limit': 5
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Handle different response formats
            chats = result.get('items', result.get('chats', []))
            
            print(f"✅ Found {len(chats)} chats")
            
            for i, chat in enumerate(chats[:2]):  # Show first 2 chats
                print(f"\n💬 Chat {i+1}:")
                print(f"   ID: {chat.get('id')}")
                print(f"   Type: {chat.get('type', chat.get('chat_type', 'N/A'))}")
                print(f"   Name: {chat.get('name', 'N/A')}")
                print(f"   Participants: {len(chat.get('attendees', chat.get('participants', [])))}")
                print(f"   Last Message: {chat.get('last_message_at', 'N/A')}")
                print(f"   Unread Count: {chat.get('unread_count', 0)}")
                
                # Show attendees
                attendees = chat.get('attendees', chat.get('participants', []))
                if attendees:
                    print(f"   👥 Participants:")
                    for attendee in attendees[:3]:  # Show first 3
                        print(f"      - {attendee.get('name', attendee.get('phone', 'Unknown'))}")
            
            return chats
        else:
            print(f"❌ Failed to get chats: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Chat retrieval error: {e}")
        return []

def test_whatsapp_messages(account_id, chat_id=None):
    """Test getting WhatsApp messages"""
    print(f"\n📩 TESTING WHATSAPP MESSAGES")
    print("=" * 50)
    
    headers = {
        'X-API-KEY': UNIPILE_API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        url = f"{UNIPILE_DSN}/api/v1/messages"
        params = {
            'account_id': account_id,
            'limit': 3
        }
        
        if chat_id:
            params['chat_id'] = chat_id
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Handle different response formats
            messages = result.get('items', result.get('messages', []))
            
            print(f"✅ Found {len(messages)} messages")
            
            for i, message in enumerate(messages):
                print(f"\n📩 Message {i+1}:")
                print(f"   ID: {message.get('id')}")
                print(f"   Type: {message.get('type', 'text')}")
                print(f"   Direction: {'Outbound' if message.get('from_me') else 'Inbound'}")
                print(f"   From: {message.get('from', 'N/A')}")
                print(f"   To: {message.get('to', 'N/A')}")
                print(f"   Content: {message.get('text', message.get('content', 'N/A'))[:100]}...")
                print(f"   Timestamp: {message.get('timestamp', message.get('created_at', 'N/A'))}")
                
                # Attachments
                attachments = message.get('attachments', [])
                if attachments:
                    print(f"   📎 Attachments: {len(attachments)}")
                    for att in attachments[:2]:  # Show first 2
                        print(f"      - Type: {att.get('type', 'N/A')}, Name: {att.get('name', 'N/A')}")
                
                # Metadata
                metadata = message.get('metadata', {})
                if metadata:
                    print(f"   📊 Metadata Keys: {list(metadata.keys())}")
                    # Show important metadata
                    for key in ['sender_attendee_id', 'message_source', 'delivery_status']:
                        if key in metadata:
                            print(f"      {key}: {metadata[key]}")
            
            return messages
        else:
            print(f"❌ Failed to get messages: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Message retrieval error: {e}")
        return []

def show_webhook_examples():
    """Show example WhatsApp webhook structures"""
    print(f"\n📡 WHATSAPP WEBHOOK EXAMPLES")
    print("=" * 50)
    
    webhooks = {
        "account_connected": {
            "event_type": "creation_success", 
            "account_id": "whatsapp_123456",
            "provider": "whatsapp",
            "account": {
                "id": "whatsapp_123456",
                "provider": "whatsapp",
                "phone_number": "+1234567890",
                "display_name": "My Business",
                "verified": True,
                "business_profile": {
                    "description": "We help businesses grow",
                    "category": "business_services",
                    "address": "123 Business St, City, State"
                }
            }
        },
        "message_received": {
            "event_type": "message.received",
            "account_id": "whatsapp_123456", 
            "message": {
                "id": "msg_789012",
                "chat_id": "chat_345678",
                "type": "text",
                "text": "Hello! I'm interested in your services.",
                "from": "+0987654321",
                "to": "+1234567890",
                "timestamp": "2024-08-16T19:15:00Z",
                "from_me": False,
                "attachments": [],
                "metadata": {
                    "sender_attendee_id": "attendee_abc123",
                    "chat_type": "individual",
                    "message_source": "whatsapp",
                    "delivery_status": "delivered"
                }
            }
        },
        "message_with_attachment": {
            "event_type": "message.received",
            "account_id": "whatsapp_123456",
            "message": {
                "id": "msg_789013",
                "chat_id": "chat_345678", 
                "type": "image",
                "text": "",
                "from": "+0987654321",
                "to": "+1234567890",
                "timestamp": "2024-08-16T19:16:00Z",
                "from_me": False,
                "attachments": [
                    {
                        "id": "att_456789",
                        "type": "image",
                        "name": "photo.jpg",
                        "mime_type": "image/jpeg",
                        "size": 245760,
                        "url": "https://unipile-attachments.s3.amazonaws.com/..."
                    }
                ],
                "metadata": {
                    "sender_attendee_id": "attendee_abc123",
                    "chat_type": "individual", 
                    "message_source": "whatsapp",
                    "delivery_status": "delivered"
                }
            }
        }
    }
    
    for event_name, webhook_data in webhooks.items():
        print(f"\n📡 {event_name.replace('_', ' ').title()}:")
        print(json.dumps(webhook_data, indent=2))

def main():
    """Main test function"""
    print("🚀 WHATSAPP METADATA TESTING WITH UNIPILE")
    print("=" * 80)
    
    # Check configuration
    if UNIPILE_DSN == 'https://your-subdomain.unipile.com':
        print("⚠️ Please set UNIPILE_DSN environment variable")
    if UNIPILE_API_KEY == 'your-api-key':
        print("⚠️ Please set UNIPILE_API_KEY environment variable")
    
    print(f"📋 Configuration:")
    print(f"   DSN: {UNIPILE_DSN}")
    print(f"   API Key: {'*' * len(UNIPILE_API_KEY) if UNIPILE_API_KEY else 'Not set'}")
    
    # Test connection and get accounts
    whatsapp_accounts = test_unipile_connection()
    
    if whatsapp_accounts:
        # Analyze first WhatsApp account
        account = whatsapp_accounts[0]
        analyze_whatsapp_account(account)
        
        account_id = account.get('id')
        
        # Test chats
        chats = test_whatsapp_chats(account_id)
        
        # Test messages
        chat_id = chats[0].get('id') if chats else None
        messages = test_whatsapp_messages(account_id, chat_id)
        
    else:
        print("\n⚠️ No WhatsApp accounts found. Creating hosted auth link...")
        test_whatsapp_hosted_auth()
    
    # Show webhook examples
    show_webhook_examples()
    
    print(f"\n✅ TESTING COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()