#!/usr/bin/env python3
"""
Test incoming WhatsApp webhook processing
"""
import requests
import json
import time
from datetime import datetime

def test_webhook_endpoint():
    """Test the webhook endpoint accessibility"""
    print("🔍 Testing Webhook Endpoint Accessibility")
    print("-" * 50)
    
    # Test the health endpoint first
    health_url = "http://localhost:8000/webhooks/health/"
    try:
        response = requests.get(health_url, timeout=5)
        print(f"✅ Health Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Health Response: {response.json()}")
        else:
            print(f"   Health Error: {response.text}")
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
    
    # Test the main webhook endpoint
    webhook_url = "http://localhost:8000/webhooks/unipile/"
    print(f"\\n📡 Testing Main Webhook: {webhook_url}")
    
    # Generate unique message ID
    import uuid
    unique_msg_id = f"webhook_test_msg_{str(uuid.uuid4())[:8]}"
    unique_chat_id = f"webhook_test_chat_{str(uuid.uuid4())[:8]}"
    
    # Simulate an incoming WhatsApp message webhook
    webhook_data = {
        "event": "message.received",
        "account_id": "mp9Gis3IRtuh9V5oSxZdSA",  # OneOTalent account ID
        "message": {
            "id": unique_msg_id,
            "chat_id": unique_chat_id,
            "conversation_id": unique_chat_id,
            "from": "sender_123",
            "sender_id": "sender_123",
            "text": "Hello! This is a test incoming message via webhook 📨",
            "content": "Hello! This is a test incoming message via webhook 📨",
            "timestamp": datetime.now().isoformat(),
            "direction": "inbound"
        },
        "timestamp": int(time.time()),
        "provider": "whatsapp"
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=webhook_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"✅ Webhook Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook Response: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"❌ Webhook Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Webhook Request Failed: {e}")
        return None

def test_whatsapp_specific_webhook():
    """Test the WhatsApp-specific webhook endpoint"""
    print("\\n📱 Testing WhatsApp-Specific Webhook")
    print("-" * 50)
    
    webhook_url = "http://localhost:8000/webhooks/whatsapp/"
    
    # Generate unique IDs for second test
    import uuid
    unique_msg_id2 = f"wa_msg_{str(uuid.uuid4())[:8]}"
    unique_chat_id2 = f"chat_from_contact_{str(uuid.uuid4())[:8]}"
    
    # Different webhook payload format that might be more realistic
    webhook_data = {
        "event": "message_received",
        "type": "message_received", 
        "account_id": "mp9Gis3IRtuh9V5oSxZdSA",
        "data": {
            "message": {
                "id": unique_msg_id2,
                "chat_id": unique_chat_id2,
                "from": "contact_789",
                "text": "Hey! How are you doing? This is an incoming WhatsApp message! 🎉",
                "timestamp": int(time.time()),
                "type": "text"
            },
            "contact": {
                "id": "contact_789",
                "name": "John Doe",
                "phone": "+1234567890"
            }
        },
        "timestamp": int(time.time())
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=webhook_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"✅ WhatsApp Webhook Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ WhatsApp Response: {json.dumps(result, indent=2)}")
            return result
        else:
            print(f"❌ WhatsApp Webhook Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ WhatsApp Webhook Request Failed: {e}")
        return None

def check_message_created():
    """Check if incoming messages were created in the database"""
    print("\\n🗄️ Checking Database for Incoming Messages")
    print("-" * 50)
    
    # We can't easily check the database from here due to tenant isolation
    # But we can test the API endpoints to see if messages appear
    
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1NzA1MzkzLCJpYXQiOjE3NTU3MDE3OTMsImp0aSI6IjQ1MWM2OWRlZmNmYzQxNWZiZTQzY2ZjMTIxYjg0NzBhIiwidXNlcl9pZCI6MX0.TR4tTni2Cp4yI_dg611sj5EdP3jvMN_N6fFwQLMLAxs"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Check for messages in the test chats we just sent webhooks for
    test_chats = ["webhook_test_chat_001", "chat_from_contact_789"]
    
    for chat_id in test_chats:
        try:
            messages_url = f"http://oneotalent.localhost:8000/api/v1/communications/whatsapp/chats/{chat_id}/messages/"
            response = requests.get(messages_url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                messages_data = response.json()
                messages = messages_data.get('messages', [])
                print(f"✅ Chat {chat_id}: Found {len(messages)} messages")
                
                for msg in messages[-2:]:  # Show last 2 messages
                    direction = "⬅️" if msg.get('direction') == 'in' else "➡️"
                    content = msg.get('text', '')[:50] + ('...' if len(msg.get('text', '')) > 50 else '')
                    print(f"   {direction} {content}")
            else:
                print(f"⚠️  Could not check chat {chat_id}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error checking chat {chat_id}: {e}")

def run_incoming_webhook_tests():
    """Run comprehensive incoming webhook tests"""
    print("🚀 INCOMING WEBHOOK TESTING")
    print("=" * 60)
    
    # Test 1: Basic webhook accessibility
    test_webhook_endpoint()
    
    # Brief pause
    time.sleep(1)
    
    # Test 2: WhatsApp-specific webhook
    test_whatsapp_specific_webhook()
    
    # Brief pause
    time.sleep(2)
    
    # Test 3: Check if messages were created
    check_message_created()
    
    print("\\n" + "=" * 60)
    print("📊 INCOMING WEBHOOK TEST SUMMARY")
    print("=" * 60)
    print("✅ Webhook endpoints tested")
    print("✅ Different payload formats tested")
    print("✅ Database checked for incoming messages")
    print("\\n🔍 If messages aren't appearing, the issue could be:")
    print("  • Webhook signature validation failing")
    print("  • Account ID not matching existing connection")
    print("  • Tenant routing issues")
    print("  • Message parsing or field mapping issues")
    
    print("\\n" + "=" * 60)

if __name__ == "__main__":
    run_incoming_webhook_tests()