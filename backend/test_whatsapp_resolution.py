#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from pipelines.models import Pipeline, Field, Record

# Get a user from oneotalent tenant
User = get_user_model()

# First, create a test contact with a phone number in the CRM
with schema_context('oneotalent'):
    # Check if we have a contacts pipeline
    contacts_pipeline = Pipeline.objects.filter(slug='contacts').first()
    
    if not contacts_pipeline:
        print("No contacts pipeline found. Creating one...")
        contacts_pipeline = Pipeline.objects.create(
            name='Contacts',
            slug='contacts',
            description='Contact records',
            icon='user',
            color='blue'
        )
        
        # Add phone field
        Field.objects.create(
            pipeline=contacts_pipeline,
            name='phone',
            label='Phone',
            field_type='phone',
            required=False
        )
        
        # Add name field
        Field.objects.create(
            pipeline=contacts_pipeline,
            name='name',
            label='Name',
            field_type='text',
            required=True
        )
    
    # Get a user to be the creator
    creator = User.objects.first()
    
    # Create a test contact with a WhatsApp phone number
    test_phone = '+27782270354'  # This is from our WhatsApp conversations (with country code)
    test_name = 'John Smith (Test Contact)'
    
    # Check what fields exist in the contacts pipeline
    all_fields = Field.objects.filter(pipeline=contacts_pipeline)
    print(f"Available fields: {[(f.name, f.field_type) for f in all_fields]}")
    
    # Use the actual field names (not labels)
    phone_field_name = 'phone_number'  # Based on the error output
    name_field_name = 'first_name'     # Based on the error output
    
    # Check if record already exists using the correct field name
    existing_record = Record.objects.filter(
        pipeline=contacts_pipeline,
        **{f'data__{phone_field_name}': test_phone}
    ).first()
    
    if not existing_record and creator:
        # Build data with correct field names
        record_data = {
            name_field_name: test_name,
            phone_field_name: test_phone
        }
            
        test_contact = Record.objects.create(
            pipeline=contacts_pipeline,
            data=record_data,
            created_by=creator,
            updated_by=creator
        )
        print(f"Created test contact: {test_name} with phone {test_phone}")
        print(f"Record ID: {test_contact.id}")
    else:
        print(f"Contact already exists: {existing_record.data.get('name')} with phone {test_phone}")
        print(f"Record ID: {existing_record.id}")
    
    # Now test the WhatsApp API to see if it resolves the contact
    user = User.objects.first()
    if user:
        print(f"\nUsing user: {user.email}")
        token = str(RefreshToken.for_user(user).access_token)
        
        # Test the API
        headers = {
            'Authorization': f'Bearer {token}',
            'Host': 'oneotalent.localhost'
        }
        
        print("\n" + "=" * 70)
        print("Testing WhatsApp Live Inbox with Contact Resolution...")
        print("=" * 70)
        
        response = requests.get(
            'http://localhost:8000/api/v1/communications/whatsapp/inbox/live/',
            headers=headers,
            params={'limit': 5}
        )
        
        if response.status_code == 200:
            data = response.json()
            conversations = data.get('conversations', [])
            
            # Look for the conversation with our test phone number
            for conv in conversations:
                participants = conv.get('participants', [])
                for p in participants:
                    # Check both with and without + prefix
                    participant_phone = p.get('phone', '')
                    if participant_phone in [test_phone, test_phone.lstrip('+'), test_phone[1:]]:
                        print(f"\n✅ Found conversation with {test_phone}")
                        print(f"  Participant name: {p.get('name')}")
                        print(f"  Has contact: {p.get('has_contact')}")
                        print(f"  Contact ID: {p.get('contact_id')}")
                        print(f"  Should show: '{test_name}' instead of just phone number")
                        
                        if p.get('name') == test_name:
                            print(f"  🎉 SUCCESS: Contact name resolved correctly!")
                        else:
                            print(f"  ❌ ISSUE: Contact name not resolved (showing '{p.get('name')}')")
                        break
        else:
            print(f"Error: {response.status_code}")
            print(response.text[:500])
    else:
        print("No users found in oneotalent tenant")