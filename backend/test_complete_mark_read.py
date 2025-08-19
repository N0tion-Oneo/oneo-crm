#!/usr/bin/env python
"""
Complete test for the mark_conversation_as_read functionality
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
from django.contrib.sessions.backends.db import SessionStore
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken
from communications.api.inbox_views import mark_conversation_as_read
from communications.models import UserChannelConnection
from tenants.models import Tenant
from django_tenants.utils import schema_context

User = get_user_model()

def test_complete_mark_as_read():
    """Test the complete mark_conversation_as_read flow"""
    
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
            
            # Get Gmail connection
            gmail_connection = UserChannelConnection.objects.filter(
                user=user,
                channel_type='gmail',
                auth_status='authenticated',
                account_status='active'
            ).first()
            
            if not gmail_connection:
                print("❌ No authenticated Gmail connection found")
                return
                
            print(f"✅ Found Gmail connection: {gmail_connection.unipile_account_id}")
            
            # Create a proper API request with JWT token
            factory = APIRequestFactory()
            request = factory.post('/api/v1/communications/conversations/test_conversation/mark-read/')
            
            # Set up authentication 
            request.user = user
            
            # Create a test conversation ID  
            test_conversation_id = "gmail_some_test_thread_id"
            
            print(f"\n🧪 Testing mark_conversation_as_read with ID: {test_conversation_id}")
            
            # Call the function directly
            response = mark_conversation_as_read(request, test_conversation_id)
            
            print(f"✅ Function returned status: {response.status_code}")
            print(f"✅ Function returned data: {response.data}")
            
            if response.status_code == 200:
                print("🎉 SUCCESS! The mark_conversation_as_read function works correctly!")
            else:
                print(f"⚠️ Function returned non-200 status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error in test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing complete mark_conversation_as_read functionality...")
    test_complete_mark_as_read()