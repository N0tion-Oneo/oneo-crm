#!/usr/bin/env python
"""Test the connections endpoint"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django_tenants.utils import schema_context

User = get_user_model()

# Test with oneotalent tenant
with schema_context('oneotalent'):
    # Get josh user
    user = User.objects.filter(email='josh@oneodigital.com').first()
    if not user:
        print("User josh@oneodigital.com not found")
        sys.exit(1)
    
    print(f"Using user: {user.email}")
    
    # Create API client with proper host header for tenant
    client = APIClient()
    client.force_authenticate(user=user)
    client.defaults['HTTP_HOST'] = 'oneotalent.localhost'
    
    # Test the connections endpoint
    url = '/api/v1/communications/connections/'
    
    print(f"\nTesting GET {url}")
    
    response = client.get(url, format='json')
    
    print(f"\nResponse status: {response.status_code}")
    
    if response.status_code == 200:
        # Check if response is paginated
        if isinstance(response.data, dict) and 'results' in response.data:
            connections = response.data['results']
            print(f"Found {response.data.get('count', len(connections))} connections (paginated)")
        else:
            connections = response.data if isinstance(response.data, list) else [response.data]
            print(f"Found {len(connections)} connections")
        
        for conn in connections:
            print(f"\n  Connection ID: {conn.get('id')}")
            print(f"  Channel Type: {conn.get('channelType')}")
            print(f"  Account Name: {conn.get('accountName')}")
            print(f"  External Account ID: {conn.get('externalAccountId')}")
            print(f"  Is Active: {conn.get('isActive')}")
            print(f"  Auth Status: {conn.get('authStatus')}")
            print(f"  Account Status: {conn.get('accountStatus')}")
            
        # Filter by channel type
        whatsapp_conns = [c for c in connections if c.get('channelType') == 'whatsapp']
        linkedin_conns = [c for c in connections if c.get('channelType') == 'linkedin']
        
        print(f"\nWhatsApp connections: {len(whatsapp_conns)}")
        print(f"LinkedIn connections: {len(linkedin_conns)}")
    else:
        print(f"Error: {response.data}")