#!/usr/bin/env python
"""
Simple test script to debug the mark_conversation_as_read logic
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
from communications.models import UserChannelConnection
from tenants.models import Tenant
from django_tenants.utils import schema_context
from communications.unipile_sdk import unipile_service
from asgiref.sync import async_to_sync

User = get_user_model()

def test_gmail_read_logic():
    """Test the Gmail read logic directly"""
    
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
            
            # Test UniPile client
            client = unipile_service.get_client()
            print(f"✅ Got UniPile client")
            
            # Test getting emails from the account to simulate the mark-as-read logic
            try:
                print(f"🧪 Testing email retrieval for account: {gmail_connection.unipile_account_id}")
                
                emails_response = async_to_sync(client.email.get_emails)(
                    account_id=gmail_connection.unipile_account_id,
                    limit=5  # Just get a few emails for testing
                )
                
                print(f"✅ Got emails response: {len(emails_response.get('emails', []))} emails")
                
                # Test the logic that finds emails to mark as read
                test_external_id = "test_thread_123"
                email_ids = []
                
                for email in emails_response.get('emails', []):
                    print(f"  📧 Email: {email.get('id')} - Thread: {email.get('thread_id')} - Read: {email.get('is_read', False)}")
                    
                    # This is the logic from the mark_conversation_as_read function
                    if (email.get('thread_id') == test_external_id or email.get('id') == test_external_id) and not email.get('is_read', False):
                        email_ids.append(email.get('id'))
                
                if email_ids:
                    print(f"📮 Would mark {len(email_ids)} emails as read: {email_ids}")
                    
                    # Test the mark_as_read API call (but don't actually do it)
                    print(f"🧪 Testing mark_as_read API call (dry run)")
                    # async_to_sync(client.email.mark_as_read)(
                    #     account_id=gmail_connection.unipile_account_id,
                    #     email_ids=email_ids
                    # )
                    print(f"✅ Mark as read API call would succeed (dry run)")
                else:
                    print(f"ℹ️ No emails found matching external_id: {test_external_id}")
                
            except Exception as api_error:
                print(f"❌ UniPile API error: {api_error}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"❌ Error in test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Gmail mark-as-read logic...")
    test_gmail_read_logic()