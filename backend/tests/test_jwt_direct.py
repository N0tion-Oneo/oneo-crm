#!/usr/bin/env python

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.request import Request
from authentication.jwt_authentication import TenantAwareJWTAuthentication
from authentication.jwt_views import current_user_view
from django_tenants.utils import get_tenant_model
from django.contrib.auth import get_user_model

print("=== Direct JWT Authentication Test ===")

# Test token
token_string = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUzOTA4NjYwLCJpYXQiOjE3NTM5MDUwNjAsImp0aSI6ImIzZjBmNTFjYWY2NDRlZjJhN2I4ZGZmZjNiOGEyNDFiIiwidXNlcl9pZCI6MSwiZW1haWwiOiJ0ZXN0QHRlc3RvcmcuY28uemEiLCJ1c2VyX3R5cGUiOiJhZG1pbiJ9.PCI39C-1m39rhIlCIM8RS_zqWR664rxQ5kTEx0_L49s"

try:
    # Create request with JWT token
    factory = APIRequestFactory()
    request = factory.get('/auth/me/')
    request.META['HTTP_AUTHORIZATION'] = f'Bearer {token_string}'
    
    # Add tenant context
    Tenant = get_tenant_model()
    tenant = Tenant.objects.get(schema_name='testorg')
    request.tenant = tenant
    
    print(f"Request created with tenant: {tenant.schema_name}")
    print(f"Authorization header: {request.META.get('HTTP_AUTHORIZATION', 'None')}")
    
    # Test our custom JWT authentication directly
    jwt_auth = TenantAwareJWTAuthentication()
    auth_result = jwt_auth.authenticate(request)
    
    print(f"Direct JWT auth result: {auth_result}")
    
    if auth_result:
        user, token = auth_result
        print(f"Authenticated user: {user}")
        print(f"User email: {user.email}")
        print(f"Token payload: {token}")
        
        # Test the view directly
        print("\n=== Testing view directly ===")
        
        # Create DRF request
        drf_request = Request(request)
        drf_request.user = user
        drf_request.auth = token
        
        # Call the view
        response = current_user_view(drf_request)
        print(f"View response status: {response.status_code}")
        print(f"View response data: {response.data}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")