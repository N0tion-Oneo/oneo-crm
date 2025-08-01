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
from django_tenants.utils import schema_context, get_tenant_model
from authentication.views import LoginView

print("=== Debugging LoginView Issues ===")

# Create a proper tenant for testing
try:
    Tenant = get_tenant_model()
    tenant = Tenant.objects.get(schema_name='testorg')
    print(f"Found tenant: {tenant.name} (schema: {tenant.schema_name})")
    
    # Create a mock request with proper tenant setup
    factory = RequestFactory()
    request = factory.post(
        '/auth/login/',
        data=json.dumps({"username": "test@testorg.co.za", "password": "Test123!"}),
        content_type='application/json',
        HTTP_X_TENANT='testorg',
        HTTP_HOST='testorg.localhost:8000'
    )
    
    # Set tenant on request (this is what TenantMainMiddleware does)
    request.tenant = tenant
    
    print(f"Request tenant: {request.tenant}")
    print(f"Request tenant schema: {request.tenant.schema_name}")
    
    # Create view instance and test
    view = LoginView()
    
    print("\nCalling LoginView.post()...")
    
    import asyncio
    response = asyncio.run(view.post(request))
    
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content.decode()}")
    
except Exception as e:
    print(f"Error in LoginView debug: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Debug Complete ===")