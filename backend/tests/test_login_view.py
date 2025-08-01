#!/usr/bin/env python

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import json
from django.test import RequestFactory
from django.db import connection
from django_tenants.utils import schema_context
from authentication.views import LoginView
from authentication.serializers import LoginSerializer

print("=== Testing LoginView ===")

# Test the serializer first
print("\n=== Testing LoginSerializer ===")
data = {"username": "test@testorg.co.za", "password": "Test123!"}
serializer = LoginSerializer(data=data)
print(f"Serializer is_valid(): {serializer.is_valid()}")
if serializer.is_valid():
    print(f"Validated data: {serializer.validated_data}")
else:
    print(f"Serializer errors: {serializer.errors}")

# Test the view
print("\n=== Testing LoginView with Request ===")
try:
    with schema_context('testorg'):
        print(f"Current schema: {connection.schema_name}")
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.post(
            '/auth/login/',
            data=json.dumps(data),
            content_type='application/json',
            HTTP_X_TENANT='testorg'
        )
        
        # Set schema manually since we're not using middleware
        request.tenant = type('Tenant', (), {'schema_name': 'testorg'})()
        
        # Create view instance and call post method
        view = LoginView()
        
        print("Calling view.post()...")
        import asyncio
        response = asyncio.run(view.post(request))
        
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content.decode()}")

except Exception as e:
    print(f"Error in LoginView test: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")