#!/usr/bin/env python
"""Test the send_message endpoint with authentication"""
import os
import sys
import django
from django.utils import timezone
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django_tenants.utils import schema_context
from pipelines.models import Record

User = get_user_model()

# Test with oneotalent tenant
with schema_context('oneotalent'):
    # Get or create a test user
    user = User.objects.filter(email='josh@oneodigital.com').first()
    if not user:
        print("User josh@oneodigital.com not found, creating...")
        user = User.objects.create_superuser(
            email='josh@oneodigital.com',
            username='josh',
            password='admin123'
        )
    
    print(f"Using user: {user.email}")
    
    # Create API client with proper host header for tenant
    client = APIClient()
    client.force_authenticate(user=user)
    # Set the host header to match the tenant domain
    client.defaults['HTTP_HOST'] = 'oneotalent.localhost'
    
    # Get Vanessa Brown's record from Contacts pipeline
    from pipelines.models import Pipeline
    
    contacts_pipeline = Pipeline.objects.filter(name__icontains='contact').first()
    if not contacts_pipeline:
        print("Contacts pipeline not found")
        sys.exit(1)
    
    # Look for Vanessa Brown's record
    record = Record.objects.filter(
        pipeline=contacts_pipeline,
        data__name__icontains='vanessa'
    ).first() or Record.objects.filter(
        pipeline=contacts_pipeline,
        data__first_name__icontains='vanessa'
    ).first()
    
    if not record:
        print("Vanessa Brown record not found in Contacts pipeline")
        # Fall back to any record in contacts pipeline
        record = Record.objects.filter(pipeline=contacts_pipeline).first()
        if not record:
            print("No records found in Contacts pipeline")
            sys.exit(1)
    
    print(f"Using record: {record.id} - {record.data.get('name', record.data.get('first_name', 'Unknown'))}")
    
    # First, let's check if there are any WhatsApp/LinkedIn connections
    from communications.models import UserChannelConnection
    connections = UserChannelConnection.objects.filter(
        user=user,
        channel_type__in=['whatsapp', 'linkedin']
    )
    
    print(f"\nFound {connections.count()} messaging connections:")
    for conn in connections:
        print(f"  - {conn.channel_type}: {conn.unipile_account_id} ({conn.account_name})")
    
    # Check if there's an existing WhatsApp conversation for this record
    from communications.record_communications.models import RecordCommunicationLink
    from communications.models import Conversation
    
    # Look for WhatsApp conversations specifically
    existing_link = RecordCommunicationLink.objects.filter(
        record=record,
        conversation__channel__channel_type='whatsapp'
    ).select_related('conversation', 'conversation__channel').first()
    
    if existing_link and existing_link.conversation:
        print(f"\nFound existing WhatsApp conversation: {existing_link.conversation.id}")
        print(f"  Chat ID: {existing_link.conversation.external_thread_id}")
        conversation_id = str(existing_link.conversation.id)
    else:
        print("\nNo existing WhatsApp conversation, will create new chat")
        conversation_id = None
    
    # Test the endpoint
    url = f'/api/v1/communications/records/{record.id}/send_message/'
    
    # Use a real account if available, otherwise use test data
    if connections.exists():
        # Try WhatsApp first since we have a real number
        conn = connections.filter(channel_type='whatsapp').first() or connections.first()
        
        if conn.channel_type == 'whatsapp':
            # Use a real phone number for testing
            data = {
                'from_account_id': conn.unipile_account_id,
                'text': f'Test message from Oneo CRM - {timezone.now().strftime("%H:%M:%S")}',
            }
            
            # Test creating/finding chat with a phone number
            # Always test with 'to' field to test the find_or_create logic
            # Use a different number to test new chat creation
            import random
            # Use the account's own number for testing (since we know it works)
            data['to'] = '+27720720047'  # The account's own number
            print(f"  Testing with number: {data['to']}")
            
            # Optionally also test with conversation_id
            # if conversation_id:
            #     data['conversation_id'] = conversation_id
                
        else:
            data = {
                'from_account_id': conn.unipile_account_id,
                'text': 'Test message from backend',
                'to': 'test-linkedin-id'
            }
    else:
        data = {
            'from_account_id': 'test_account',
            'text': 'Test message',
            'to': '+1234567890'
        }
    
    print(f"\nTesting POST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    response = client.post(url, data, format='json')
    
    print(f"\nResponse status: {response.status_code}")
    print(f"Response data: {json.dumps(response.data if hasattr(response, 'data') else response.content.decode(), indent=2)}")