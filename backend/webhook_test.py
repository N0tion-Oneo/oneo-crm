#!/usr/bin/env python
"""
Test sending a test email to trigger webhooks
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

def send_test_email():
    """Send a test email to trigger webhook"""
    
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
            
            # Send a test email to yourself (should trigger a webhook)
            try:
                print(f"🧪 Sending test email to trigger webhook...")
                
                response = async_to_sync(client.email.send_email)(
                    account_id=gmail_connection.unipile_account_id,
                    to=['josh@oneodigital.com'],  # Send to yourself
                    subject='🧪 Test Email for Webhook Trigger - ' + str(int(time.time())),
                    body='This is a test email sent via UniPile API to trigger webhook reception. If you see this, the send functionality works. Now check if you receive it as a webhook.',
                    is_html=False
                )
                
                print(f"✅ Email sent successfully!")
                print(f"📧 Response: {response}")
                print(f"🔍 Check your Django logs for incoming webhook in ~5-10 seconds...")
                
            except Exception as api_error:
                print(f"❌ Failed to send email: {api_error}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"❌ Error in test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import time
    print("🧪 Sending test email to trigger webhook...")
    send_test_email()