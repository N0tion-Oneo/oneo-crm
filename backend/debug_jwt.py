#!/usr/bin/env python

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, get_tenant_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.test import RequestFactory
from rest_framework.request import Request

print("=== JWT Authentication Debug ===")

# Get the token from our login
token_string = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUzOTA4NjYwLCJpYXQiOjE3NTM5MDUwNjAsImp0aSI6ImIzZjBmNTFjYWY2NDRlZjJhN2I4ZGZmZjNiOGEyNDFiIiwidXNlcl9pZCI6MSwiZW1haWwiOiJ0ZXN0QHRlc3RvcmcuY28uemEiLCJ1c2VyX3R5cGUiOiJhZG1pbiJ9.PCI39C-1m39rhIlCIM8RS_zqWR664rxQ5kTEx0_L49s"

try:
    # Test 1: Parse the JWT token
    print("\n=== Test 1: JWT Token Parsing ===")
    token = AccessToken(token_string)
    print(f"Token valid: {token}")
    print(f"Token payload: {token.payload}")
    
    # Test 2: Test JWT authentication outside tenant context
    print("\n=== Test 2: JWT Authentication (Public Schema) ===")
    User = get_user_model()
    
    factory = RequestFactory()
    request = factory.get('/test/')
    request.META['HTTP_AUTHORIZATION'] = f'Bearer {token_string}'
    drf_request = Request(request)
    
    jwt_auth = JWTAuthentication()
    auth_result = jwt_auth.authenticate(drf_request)
    print(f"Auth result (public schema): {auth_result}")
    
    # Test 3: Test JWT authentication in tenant context
    print("\n=== Test 3: JWT Authentication (Tenant Schema) ===")
    Tenant = get_tenant_model()
    tenant = Tenant.objects.get(schema_name='testorg')
    
    with schema_context(tenant.schema_name):
        print(f"Current schema: {tenant.schema_name}")
        
        # Try to get the user in tenant context
        try:
            user = User.objects.get(id=1)
            print(f"User found in tenant: {user}")
        except User.DoesNotExist:
            print("User not found in tenant schema!")
        
        # Test JWT auth in tenant context
        request.tenant = tenant  # Simulate tenant middleware
        drf_request = Request(request)
        
        auth_result_tenant = jwt_auth.authenticate(drf_request)
        print(f"Auth result (tenant schema): {auth_result_tenant}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Debug Complete ===")