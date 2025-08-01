#!/usr/bin/env python

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import authenticate, get_user_model
from django.db import connection
from django_tenants.utils import schema_context, get_tenant_model

User = get_user_model()

print("=== Detailed Authentication Debug ===")

try:
    Tenant = get_tenant_model()
    tenant = Tenant.objects.get(schema_name='testorg')
    
    print(f"Testing authentication within schema_context('{tenant.schema_name}')")
    
    with schema_context(tenant.schema_name):
        print(f"Current schema inside context: {connection.schema_name}")
        
        # Test user lookup first
        try:
            user = User.objects.get(email='test@testorg.co.za')
            print(f"User found: {user}")
            print(f"User is_active: {user.is_active}")
            print(f"User check_password('Test123!'): {user.check_password('Test123!')}")
        except User.DoesNotExist:
            print("User not found!")
        
        # Test authentication
        print("\nTesting authenticate() inside schema_context:")
        auth_user = authenticate(username='test@testorg.co.za', password='Test123!')
        print(f"authenticate() result: {auth_user}")
        
        # Test with request parameter (this might be the issue)
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post('/login/')
        request.tenant = tenant
        
        print("\nTesting authenticate() with request parameter:")
        auth_user_with_request = authenticate(request=request, username='test@testorg.co.za', password='Test123!')
        print(f"authenticate(request=request, ...) result: {auth_user_with_request}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Debug Complete ===")