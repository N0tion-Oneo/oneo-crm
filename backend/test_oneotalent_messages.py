#!/usr/bin/env python3
"""
Test WhatsApp message sending with OneOTalent tenant
"""
import requests
import json
import time

# Fresh JWT token for oneotalent
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzU1NzA1MzkzLCJpYXQiOjE3NTU3MDE3OTMsImp0aSI6IjQ1MWM2OWRlZmNmYzQxNWZiZTQzY2ZjMTIxYjg0NzBhIiwidXNlcl9pZCI6MX0.TR4tTni2Cp4yI_dg611sj5EdP3jvMN_N6fFwQLMLAxs"

# OneOTalent tenant URL
base_url = "http://oneotalent.localhost:8000"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

def test_tenant_accessibility():
    """Test basic tenant API accessibility"""
    print("🔍 Testing OneOTalent Tenant Accessibility")
    print("-" * 50)
    
    # Test basic endpoint
    url = f"{base_url}/api/v1/communications/whatsapp/accounts/"
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ WhatsApp accounts endpoint accessible")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        elif response.status_code == 401:
            print("❌ Authentication failed")
            return False
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_message_sending(chat_id, message_text):
    """Test sending a message to OneOTalent tenant"""
    print(f"\n📤 Testing Message Send to OneOTalent")
    print(f"Chat ID: {chat_id}")
    print(f"Message: '{message_text}'")
    print("-" * 50)
    
    url = f"{base_url}/api/v1/communications/whatsapp/chats/{chat_id}/send/"
    data = {"text": message_text}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"✅ Status: {response.status_code}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            result = response.json()
            
            # Extract key information
            success = result.get('success')
            message_info = result.get('message', {})
            conversation_id = result.get('conversation_id')
            conversation_name = result.get('conversation_name')
            
            print(f"✅ Success: {success}")
            print(f"✅ Message ID: {message_info.get('id')}")
            print(f"✅ Status: {message_info.get('status')}")
            print(f"✅ Direction: {message_info.get('direction')}")
            print(f"✅ Conversation: {conversation_name}")
            print(f"✅ Conversation ID: {conversation_id}")
            
            print(f"\n📋 Full Response:")
            print(json.dumps(result, indent=2))
            
            return result
            
        else:
            print(f"❌ Non-JSON response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def test_conversation_retrieval():
    """Test retrieving conversations from OneOTalent tenant"""
    print(f"\n📋 Testing Conversation Retrieval")
    print("-" * 50)
    
    url = f"{base_url}/api/v1/communications/whatsapp/chats/"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"✅ Status: {response.status_code}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            result = response.json()
            
            chats = result.get('chats', [])
            print(f"✅ Found {len(chats)} conversations")
            
            for i, chat in enumerate(chats[:3]):  # Show first 3
                print(f"  {i+1}. ID: {chat.get('id')}, Name: {chat.get('name', 'No name')}")
                print(f"     Messages: {chat.get('message_count', 0)}, Unread: {chat.get('unread_count', 0)}")
            
            if len(chats) > 3:
                print(f"     ... and {len(chats) - 3} more")
                
            return result
            
        else:
            print(f"❌ Non-JSON response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def run_oneotalent_tests():
    """Run comprehensive tests for OneOTalent tenant"""
    print("🚀 ONEOTALENT TENANT TESTING")
    print("=" * 60)
    
    # Test 1: Basic accessibility
    accessible = test_tenant_accessibility()
    
    if not accessible:
        print("\n❌ Tenant not accessible. Stopping tests.")
        return
    
    # Test 2: Message sending
    test_messages = [
        ("oneotalent_chat_001", "Hello OneOTalent! 🎯"),
        ("talent_recruitment_002", "Testing recruitment message flow"),
        ("candidate_chat_003", "Candidate communication test ✨")
    ]
    
    sent_messages = []
    for chat_id, message in test_messages:
        result = test_message_sending(chat_id, message)
        if result:
            sent_messages.append(result)
        time.sleep(0.5)  # Brief pause between requests
    
    # Test 3: Conversation retrieval
    conversations = test_conversation_retrieval()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ONEOTALENT TEST SUMMARY")
    print("=" * 60)
    
    print(f"✅ Tenant Accessible: {'Yes' if accessible else 'No'}")
    print(f"✅ Messages Sent: {len(sent_messages)}/{len(test_messages)}")
    print(f"✅ Conversations Retrieved: {'Yes' if conversations else 'No'}")
    
    if len(sent_messages) == len(test_messages) and conversations:
        print("\n🎉 ALL ONEOTALENT TESTS PASSED!")
        print("\n🔥 OneOTalent tenant is fully operational for WhatsApp messaging!")
    else:
        print("\n⚠️  Some tests had issues. Review results above.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    run_oneotalent_tests()