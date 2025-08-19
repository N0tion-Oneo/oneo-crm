#!/usr/bin/env python
"""
Test script to debug the mark_conversation_as_read function
"""
import os
import sys
import django

# Add the backend directory to Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

# Initialize Django
django.setup()

# Now we can import Django models and functions
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from communications.api.inbox_views import mark_conversation_as_read
from communications.models import UserChannelConnection
from tenants.models import Tenant
from django_tenants.utils import schema_context

User = get_user_model()

def test_mark_conversation_as_read():
    """Test the mark_conversation_as_read function with debug logging"""
    
    # Get the oneotalent tenant (has Gmail connection)
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        try:
            # Get the specific user with Gmail connection
            user = User.objects.filter(email='josh@oneodigital.com').first()
            if not user:
                print("❌ User josh@oneodigital.com not found in oneotalent tenant")
                return
                
            print(f"✅ Found user: {user.email}")
            
            # Get user's channel connections
            connections = UserChannelConnection.objects.filter(user=user)
            print(f"✅ Found {connections.count()} channel connections")
            
            for connection in connections:
                print(f"  - {connection.channel_type}: {connection.unipile_account_id} ({connection.auth_status})")
            
            # Find a Gmail connection
            gmail_connection = connections.filter(channel_type='gmail').first()
            if not gmail_connection:
                print("❌ No Gmail connection found")
                return
                
            print(f"✅ Found Gmail connection: {gmail_connection.unipile_account_id}")
            
            # Create a mock request
            factory = RequestFactory()
            request = factory.post('/api/v1/communications/conversations/test_conversation/mark-read/')
            request.user = user
            
            # Test with a fake conversation ID to see what error we get
            test_conversation_id = "gmail_test_thread_123"
            
            print(f"\n🧪 Testing mark_conversation_as_read with ID: {test_conversation_id}")
            
            # Call the function
            response = mark_conversation_as_read(request, test_conversation_id)
            
            print(f"✅ Function returned status: {response.status_code}")
            print(f"✅ Function returned data: {response.data}")
            
        except Exception as e:
            print(f"❌ Error in test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing mark_conversation_as_read function...")
    test_mark_conversation_as_read()