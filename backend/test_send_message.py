#!/usr/bin/env python3
"""
Test send message functionality end-to-end
"""
import os
import sys
import django
import requests
import time
import json

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Message, Conversation, Channel
from django.contrib.auth import get_user_model

User = get_user_model()

def test_send_message():
    """Test sending a message and verify webhook processing"""
    
    # Get the oneotalent tenant
    try:
        tenant = Tenant.objects.get(schema_name='oneotalent')
    except Tenant.DoesNotExist:
        print("❌ oneotalent tenant not found")
        return
    
    with schema_context(tenant.schema_name):
        # Get the WhatsApp connection
        connection = UserChannelConnection.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not connection:
            print("❌ WhatsApp connection not found")
            return
        
        print(f"✅ Found WhatsApp connection: {connection.account_name}")
        
        # Get existing conversation for Vanessa
        conversation = Conversation.objects.filter(
            external_thread_id='1T1s9uwKX3yXDdHr9p9uWQ'
        ).first()
        
        if not conversation:
            print("❌ Conversation with Vanessa not found")
            return
        
        print(f"✅ Found conversation: {conversation.id}")
        
        # Check messages before sending
        messages_before = Message.objects.filter(conversation=conversation).count()
        print(f"📊 Messages before: {messages_before}")
        
        # Send a test message via API
        print("📤 Sending test message...")
        
        api_url = f"http://oneotalent.localhost:8000/api/v1/communications/messages/send/"
        
        # Get user token (simplified for testing)
        user = connection.user
        print(f"👤 Sending as user: {user.username}")
        
        # Create session to get CSRF token
        session = requests.Session()
        
        # Get CSRF token
        csrf_response = session.get(f"http://oneotalent.localhost:8000/api/v1/communications/connections/")
        
        message_data = {
            'conversation_id': f"whatsapp_{conversation.external_thread_id}",
            'content': f'Test message from script at {time.strftime("%H:%M:%S")}',
            'type': 'whatsapp'
        }
        
        print(f"📝 Message data: {json.dumps(message_data, indent=2)}")
        
        try:
            # Try without authentication first to see the response
            response = requests.post(api_url, json=message_data, timeout=10)
            print(f"📡 API Response Status: {response.status_code}")
            print(f"📡 API Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ Message sent successfully!")
                
                # Wait a moment for webhook processing
                time.sleep(2)
                
                # Check messages after sending
                messages_after = Message.objects.filter(conversation=conversation).count()
                print(f"📊 Messages after: {messages_after}")
                
                if messages_after > messages_before:
                    print("✅ Message record created in database!")
                    
                    # Get the latest message
                    latest_message = Message.objects.filter(conversation=conversation).order_by('-created_at').first()
                    print(f"📄 Latest message: {latest_message.content[:50]}...")
                    print(f"📄 Direction: {latest_message.direction}")
                    print(f"📄 Status: {latest_message.status}")
                else:
                    print("⚠️ No new message record found in database")
            else:
                print(f"❌ Message sending failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error sending message: {e}")

if __name__ == '__main__':
    test_send_message()