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
        
        print("\nFetching WhatsApp Live Inbox data...")
        print("-" * 50)
        
        response = requests.get(
            'http://localhost:8000/api/v1/communications/whatsapp/inbox/live/',
            headers=headers,
            params={'limit': 2}  # Just get 2 conversations for full output
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Pretty print the full response
            print("\nFULL API RESPONSE:")
            print("=" * 70)
            print(json.dumps(data, indent=2))
            
        else:
            print(f"Error: {response.status_code}")
            print(response.text[:500])
    else:
        print("No users found in oneotalent tenant")