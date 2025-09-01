#!/usr/bin/env python
"""
Test email sending via the API endpoint
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from pipelines.models import Record
from communications.record_communications.api import RecordCommunicationsViewSet
from django_tenants.utils import schema_context
from tenants.models import Tenant

User = get_user_model()

def test_email_api():
    """Test email sending through the API endpoint"""
    
    print("=" * 60)
    print("Testing Email Send via API Endpoint")
    print("=" * 60)
    
    # Get tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    print(f"✅ Using tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get user
        user = User.objects.filter(email='josh@oneodigital.com').first()
        if not user:
            user = User.objects.filter(is_superuser=True).first()
        print(f"✅ Using user: {user.email}")
        
        # Get record
        record = Record.objects.get(id=66)  # The record we've been testing with
        print(f"✅ Using record: {record.id}")
        
        # Create request
        factory = APIRequestFactory()
        
        # Get email connection for account ID
        from communications.models import UserChannelConnection
        connection = UserChannelConnection.objects.filter(
            user=user,
            channel_type='gmail'
        ).first()
        
        if not connection:
            print("❌ No Gmail connection found for user")
            return False
        
        print(f"✅ Using Gmail account: {connection.unipile_account_id}")
        
        # Prepare email data - matching what the API expects
        email_data = {
            'from_account_id': connection.unipile_account_id,
            'to': ['test@example.com'],  # Should be a list
            'subject': f'API Test - {datetime.now().strftime("%H:%M:%S")}',
            'body': '<p>Test from API endpoint</p>',
            'cc': [],
            'bcc': [],
            'reply_mode': None,
            'conversation_id': None
        }
        
        # Create POST request
        request = factory.post(
            f'/api/v1/communications/records/{record.id}/send_email/',
            data=email_data,
            content_type='application/json'
        )
        
        # Authenticate request
        force_authenticate(request, user=user)
        
        # Add tenant to request
        request.tenant = tenant
        
        # Call the view
        viewset = RecordCommunicationsViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': str(record.id)}
        
        print(f"\n📧 Sending email via API...")
        print(f"   From account: {email_data['from_account_id']}")
        print(f"   To: {email_data['to']}")
        print(f"   Subject: {email_data['subject']}")
        
        try:
            response = viewset.send_email(request, pk=record.id)
            
            if response.status_code == 200:
                data = response.data
                print(f"\n✅ SUCCESS via API!")
                print(f"   Tracking ID: {data.get('tracking_id')}")
                print(f"   Message ID: {data.get('message_id')}")
                return True
            else:
                print(f"\n❌ API returned {response.status_code}")
                print(f"   Error: {response.data}")
                return False
                
        except Exception as e:
            print(f"\n❌ API Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_email_api()
    sys.exit(0 if success else 1)