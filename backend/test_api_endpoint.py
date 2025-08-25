#!/usr/bin/env python
"""
Test the API endpoint directly to see what it returns
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from communications.channels.whatsapp.api_views import get_chat_messages_local_first, get_whatsapp_chats_local_first

User = get_user_model()

def test_api_endpoints():
    """Test API endpoints directly"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Testing API Endpoints Directly")
        print("=" * 60)
        
        # Get a user for the request
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return
            
        print(f"✅ Using user: {user.username}")
        
        # Create a request factory
        factory = RequestFactory()
        
        # Test get_whatsapp_chats_local_first
        print("\n📱 Testing get_whatsapp_chats_local_first:")
        request = factory.get('/api/whatsapp/chats/', {
            'account_id': 'mp9Gis3IRtuh9V5oSxZdSA',
            'limit': 10
        })
        request.user = user
        
        try:
            response = get_whatsapp_chats_local_first(request)
            data = response.data
            
            if data.get('success'):
                print(f"   ✅ Success! Got {len(data.get('chats', []))} chats")
                
                # Show chats with message counts
                for chat in data.get('chats', [])[:5]:
                    print(f"\n   Chat: {chat.get('name', 'Unknown')}")
                    print(f"     ID: {chat.get('id')}")
                    print(f"     Message count: {chat.get('message_count', 0)}")
                    print(f"     Last message: {chat.get('last_message', {}).get('content', 'None')[:50] if chat.get('last_message') else 'None'}")
                    
                    # Test getting messages for this chat
                    if chat.get('message_count', 0) > 0:
                        print(f"\n   🔍 Testing get_chat_messages_local_first for chat {chat.get('id')}:")
                        msg_request = factory.get(f"/api/whatsapp/chats/{chat.get('id')}/messages/", {
                            'limit': 5
                        })
                        msg_request.user = user
                        
                        try:
                            msg_response = get_chat_messages_local_first(msg_request, chat.get('id'))
                            msg_data = msg_response.data
                            
                            if msg_data.get('success'):
                                messages = msg_data.get('messages', [])
                                print(f"     ✅ Got {len(messages)} messages")
                                
                                for msg in messages[:3]:
                                    sender_name = msg.get('sender', {}).get('name', 'Unknown')
                                    content = msg.get('content', 'No content')[:40]
                                    direction = msg.get('direction', 'unknown')
                                    print(f"       [{direction}] {sender_name}: {content}")
                            else:
                                print(f"     ❌ Failed: {msg_data.get('error')}")
                        except Exception as e:
                            print(f"     ❌ Error getting messages: {e}")
            else:
                print(f"   ❌ Failed: {data.get('error')}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Test a specific chat we know has messages
        print("\n🔍 Testing specific chat 'sp8yWrO2XiqS33wjw9lqWQ' (Josh Cowan):")
        msg_request = factory.get("/api/whatsapp/chats/sp8yWrO2XiqS33wjw9lqWQ/messages/", {
            'limit': 10
        })
        msg_request.user = user
        
        try:
            msg_response = get_chat_messages_local_first(msg_request, 'sp8yWrO2XiqS33wjw9lqWQ')
            msg_data = msg_response.data
            
            if msg_data.get('success'):
                messages = msg_data.get('messages', [])
                print(f"   ✅ Got {len(messages)} messages")
                
                for msg in messages[:5]:
                    sender_name = msg.get('sender', {}).get('name', 'Unknown')
                    sender_id = msg.get('sender', {}).get('id', 'Unknown')
                    content = msg.get('content', 'No content')[:50]
                    direction = msg.get('direction', 'unknown')
                    print(f"   [{direction}] {sender_name} ({sender_id}): {content}")
            else:
                print(f"   ❌ Failed: {msg_data.get('error')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_api_endpoints()