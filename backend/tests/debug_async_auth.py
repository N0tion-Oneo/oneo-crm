#!/usr/bin/env python

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import asyncio
from django.contrib.auth import authenticate, get_user_model
from django.db import connection
from django_tenants.utils import schema_context, get_tenant_model
from asgiref.sync import sync_to_async

User = get_user_model()

print("=== Async Authentication Debug ===")

async def test_async_auth():
    try:
        Tenant = get_tenant_model()
        tenant = await sync_to_async(Tenant.objects.get)(schema_name='testorg')
        
        print(f"Testing async authentication within schema_context('{tenant.schema_name}')")
        
        with schema_context(tenant.schema_name):
            print(f"Current schema inside context: {connection.schema_name}")
            
            # Test sync authentication first
            print("\n1. Testing sync authenticate() inside schema_context:")
            auth_user_sync = authenticate(username='test@testorg.co.za', password='Test123!')
            print(f"sync authenticate() result: {auth_user_sync}")
            
            # Test async authentication
            print("\n2. Testing async authenticate() inside schema_context:")
            auth_user_async = await sync_to_async(authenticate)(username='test@testorg.co.za', password='Test123!')
            print(f"async authenticate() result: {auth_user_async}")
            
            # Test with request parameter
            from django.test import RequestFactory
            factory = RequestFactory()
            request = factory.post('/login/')
            request.tenant = tenant
            
            print("\n3. Testing async authenticate() with request parameter:")
            auth_user_request = await sync_to_async(authenticate)(
                request=request, 
                username='test@testorg.co.za', 
                password='Test123!'
            )
            print(f"async authenticate(request=request, ...) result: {auth_user_request}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

# Run the async test
asyncio.run(test_async_auth())

print("\n=== Debug Complete ===")