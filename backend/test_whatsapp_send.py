#!/usr/bin/env python3
"""
Test script to verify WhatsApp message sending functionality
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import requests
import json
from datetime import datetime

def test_message_sending():
    """Test the WhatsApp message sending API"""
    
    print("🧪 Testing WhatsApp Message Sending API")
    print("=" * 50)
    
    # API endpoint
    base_url = "http://localhost:8000"
    
    # Test data - you'll need to replace these with real values
    test_chat_id = "test_chat_123"  # Replace with a real chat ID from your conversations
    test_message = f"Test message from API at {datetime.now().strftime('%H:%M:%S')}"
    
    # You'll need a valid JWT token - get this from your frontend login
    # For now, we'll test the endpoint structure
    headers = {
        'Content-Type': 'application/json',
        # 'Authorization': 'Bearer YOUR_JWT_TOKEN_HERE'
    }
    
    payload = {
        'text': test_message,
        'type': 'text'
    }
    
    print(f"📤 Testing endpoint: POST {base_url}/api/v1/communications/whatsapp/chats/{test_chat_id}/send/")
    print(f"📝 Message: '{test_message}'")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print()
    
    # Make the request
    try:
        response = requests.post(
            f"{base_url}/api/v1/communications/whatsapp/chats/{test_chat_id}/send/",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            try:
                response_data = response.json()
                print(f"✅ Response JSON: {json.dumps(response_data, indent=2)}")
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response: {response.text}")
        else:
            print(f"📄 Response Text: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    print()
    print("=" * 50)
    print("🎯 Test completed!")
    print()
    print("📋 To run a complete test:")
    print("1. Make sure Django server is running: python manage.py runserver")
    print("2. Get a valid JWT token from the frontend login")
    print("3. Get a real chat_id from existing conversations")
    print("4. Update this script with the token and chat_id")
    print("5. Run the test again")

def test_url_resolution():
    """Test that the URL routing is working correctly"""
    
    print("🔗 Testing URL Resolution")
    print("-" * 30)
    
    try:
        from django.urls import reverse, resolve
        from django.test import Client
        
        # Test URL reverse resolution
        try:
            url = reverse('whatsapp-send-message', kwargs={'chat_id': 'test123'})
            print(f"✅ URL reverse resolution: {url}")
        except Exception as e:
            print(f"❌ URL reverse failed: {e}")
        
        # Test URL resolve
        try:
            test_path = '/api/v1/communications/whatsapp/chats/test123/send/'
            resolver = resolve(test_path)
            print(f"✅ URL resolve: {resolver.func.__name__} from {resolver.func.__module__}")
        except Exception as e:
            print(f"❌ URL resolve failed: {e}")
            
    except Exception as e:
        print(f"❌ URL testing failed: {e}")

def check_database_models():
    """Check that all required models exist and can be imported"""
    
    print("🗄️  Testing Database Models")
    print("-" * 30)
    
    try:
        from communications.models import (
            Channel, Conversation, Message, MessageDirection, 
            MessageStatus, UserChannelConnection, ChatAttendee
        )
        print("✅ All communication models imported successfully")
        
        # Test model relationships
        print(f"   - Channel model: {Channel.__name__}")
        print(f"   - Conversation model: {Conversation.__name__}")
        print(f"   - Message model: {Message.__name__}")
        print(f"   - ChatAttendee model: {ChatAttendee.__name__}")
        print(f"   - UserChannelConnection model: {UserChannelConnection.__name__}")
        
        # Test enum values
        print(f"   - MessageDirection.OUTBOUND: {MessageDirection.OUTBOUND}")
        print(f"   - MessageStatus.PENDING: {MessageStatus.PENDING}")
        
    except ImportError as e:
        print(f"❌ Model import failed: {e}")
    except Exception as e:
        print(f"❌ Model testing failed: {e}")

def check_services():
    """Check that all required services exist and can be imported"""
    
    print("⚙️  Testing Services")
    print("-" * 20)
    
    try:
        from communications.unipile_sdk import unipile_service
        print("✅ UniPile service imported")
        
        from communications.services.conversation_naming import conversation_naming_service  
        print("✅ Conversation naming service imported")
        
    except ImportError as e:
        print(f"❌ Service import failed: {e}")
    except Exception as e:
        print(f"❌ Service testing failed: {e}")

if __name__ == "__main__":
    print("🚀 WhatsApp Message Sending Test Suite")
    print("=" * 60)
    print()
    
    # Run all tests
    check_database_models()
    print()
    check_services() 
    print()
    test_url_resolution()
    print()
    test_message_sending()