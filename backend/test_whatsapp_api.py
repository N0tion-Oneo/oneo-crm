#!/usr/bin/env python
import os
import sys
import django
import requests
import time
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

# Get a user from oneotalent tenant
User = get_user_model()
with schema_context('oneotalent'):
    user = User.objects.first()
    if user:
        print(f"Using user: {user.email}")
        token = str(RefreshToken.for_user(user).access_token)
        
        # Test the API
        headers = {
            'Authorization': f'Bearer {token}',
            'Host': 'oneotalent.localhost'
        }
        
        print("\nTesting WhatsApp Live Inbox API...")
        print("-" * 50)
        
        # Test with timing
        start_time = time.time()
        response = requests.get(
            'http://localhost:8000/api/v1/communications/whatsapp/inbox/live/',
            headers=headers,
            params={'limit': 10}
        )
        end_time = time.time()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {(end_time - start_time) * 1000:.2f}ms")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Conversations: {len(data.get('conversations', []))}")
            
            # Check all conversations for participant data
            convs = data.get('conversations', [])
            for i, conv in enumerate(convs[:5], 1):  # Show first 5 conversations
                print(f"\nConversation {i}:")
                print(f"  Name: {conv.get('name')}")
                print(f"  Is Group: {conv.get('is_group')}")
                print(f"  Participants: {len(conv.get('participants', []))}")
                if conv.get('participants'):
                    for p in conv['participants']:
                        is_self = p.get('is_self', False)
                        name = p.get('name', 'Unknown')
                        phone = p.get('phone', 'No phone')
                        print(f"    - {name} ({'Self' if is_self else phone})")
        else:
            print(f"Error: {response.text[:200]}")
    else:
        print("No users found in oneotalent tenant")