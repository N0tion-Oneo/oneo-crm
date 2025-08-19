#!/usr/bin/env python3
"""
Test the actual backend API endpoint to ensure both infinite scroll and contact names work
"""
import os
import sys
import django
import asyncio
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from communications.models import UserChannelConnection


async def test_backend_api():
    """Test the actual backend API with a simulated request"""
    print("🧪 Testing backend API with pagination and contact names...")
    
    # Create test client
    client = Client()
    
    # Create a test user (should exist from previous testing)
    User = get_user_model()
    try:
        user = User.objects.get(email='admin@example.com')
        print(f"✅ Using existing test user: {user.email}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            email='admin@example.com',
            username='admin',
            password='testpass123'
        )
        print(f"✅ Created test user: {user.email}")
    
    # Login the user
    client.login(username='admin', password='testpass123')
    
    # Check for existing WhatsApp connections
    connections = UserChannelConnection.objects.filter(
        user=user,
        channel_type='whatsapp',
        is_active=True
    )
    
    if not connections.exists():
        # Create a test connection
        connection = UserChannelConnection.objects.create(
            user=user,
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA',  # Known test account
            account_name='Test WhatsApp',
            account_status='active',
            auth_status='authenticated',
            is_active=True
        )
        print(f"✅ Created test WhatsApp connection: {connection.id}")
    else:
        connection = connections.first()
        print(f"✅ Using existing WhatsApp connection: {connection.id}")
    
    # Test the API endpoints
    print(f"\n🔍 Testing WhatsApp accounts endpoint...")
    
    response = client.get('/api/v1/communications/whatsapp/accounts/')
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = json.loads(response.content)
        print(f"Accounts: {len(data.get('accounts', []))}")
        
        if data.get('accounts'):
            account_id = data['accounts'][0]['id']
            print(f"Testing with account ID: {account_id}")
            
            # Test chats endpoint with pagination
            print(f"\n🔍 Testing chats endpoint with pagination...")
            
            response = client.get('/api/v1/communications/whatsapp/chats/', {
                'account_id': account_id,
                'limit': 3  # Test with small limit
            })
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                chat_data = json.loads(response.content)
                print(f"Success: {chat_data.get('success')}")
                print(f"Total chats: {chat_data.get('total')}")
                print(f"Has more: {chat_data.get('has_more')}")
                print(f"Cursor: {chat_data.get('cursor')}")
                
                chats = chat_data.get('chats', [])
                print(f"\n📋 Found {len(chats)} chats:")
                
                for i, chat in enumerate(chats):
                    print(f"  Chat {i+1}:")
                    print(f"    - ID: {chat.get('id')}")
                    print(f"    - Name: '{chat.get('name')}'")
                    print(f"    - Provider ID: {chat.get('provider_chat_id')}")
                    print(f"    - Is group: {chat.get('is_group')}")
                    print(f"    - Attendees: {len(chat.get('attendees', []))}")
                    
                    # Show attendee details
                    for attendee in chat.get('attendees', []):
                        print(f"      👤 {attendee.get('provider_id')} → '{attendee.get('name')}'")
                
                # Test pagination with cursor if available
                if chat_data.get('has_more') and chat_data.get('cursor'):
                    print(f"\n🔍 Testing pagination with cursor...")
                    
                    response = client.get('/api/v1/communications/whatsapp/chats/', {
                        'account_id': account_id,
                        'limit': 3,
                        'cursor': chat_data.get('cursor')
                    })
                    
                    if response.status_code == 200:
                        next_page = json.loads(response.content)
                        print(f"Next page chats: {len(next_page.get('chats', []))}")
                        print(f"Next page has more: {next_page.get('has_more')}")
                        
                        for i, chat in enumerate(next_page.get('chats', [])):
                            print(f"  Page 2 Chat {i+1}: '{chat.get('name')}'")
                    else:
                        print(f"Pagination failed: {response.status_code}")
                        print(response.content.decode())
                
            else:
                print(f"Chats API failed: {response.status_code}")
                print(response.content.decode())
        
    else:
        print(f"Accounts API failed: {response.status_code}")
        print(response.content.decode())


if __name__ == "__main__":
    asyncio.run(test_backend_api())