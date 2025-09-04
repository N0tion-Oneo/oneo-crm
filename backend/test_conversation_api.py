#!/usr/bin/env python
"""
Test the conversation messages API endpoint directly
"""
import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Conversation
from pipelines.models import Record
from communications.record_communications.api import RecordCommunicationsViewSet
from rest_framework.test import force_authenticate

User = get_user_model()

# Use oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    print(f"🏢 Testing in tenant: {tenant.name} ({tenant.schema_name})")
    
    # Get a user for authentication
    user = User.objects.filter(is_active=True).first()
    
    # Get the record and a conversation
    record = Record.objects.get(id=93)
    print(f"\n📄 Record: {record.id}")
    
    # Get first conversation
    viewset = RecordCommunicationsViewSet()
    conversation_ids = list(viewset._get_record_conversation_ids(record))
    
    if not conversation_ids:
        print("❌ No conversations found")
    else:
        conversation = Conversation.objects.get(id=conversation_ids[0])
        print(f"💬 Testing with conversation: {conversation.id}")
        print(f"   Subject: {conversation.subject}")
        
        # Create request using DRF's APIRequestFactory
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.get(
            f'/api/v1/communications/records/{record.id}/conversation-messages/',
            {'conversation_id': str(conversation.id), 'limit': 5}
        )
        force_authenticate(request, user=user)
        
        # Create viewset and call method
        viewset = RecordCommunicationsViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        # Call the conversation_messages action
        response = viewset.conversation_messages(request, pk=record.id)
        
        print(f"\n📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.data
            print(f"✅ Success! Messages count: {data.get('count', 0)}")
            if data.get('results'):
                print(f"   First message: {data['results'][0].get('content', '')[:100]}")
        else:
            print(f"❌ Error: {response.data}")