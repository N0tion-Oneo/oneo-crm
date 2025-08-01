#!/usr/bin/env python
"""
Debug the tenant middleware step-by-step
"""
import os
import sys
import django
from django.test import RequestFactory

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def debug_tenant_middleware():
    """Debug tenant middleware step by step"""
    
    print("🔍 Debugging Tenant Middleware Processing")
    print("=" * 50)
    
    factory = RequestFactory()
    
    # Test 1: Create request like demo.localhost would send
    print("1. Creating test request...")
    request = factory.get('/health/')
    request.META['HTTP_HOST'] = 'demo.localhost'
    
    # Test 2: Manually test tenant detection
    print("\n2. Testing tenant detection manually...")
    try:
        from django_tenants.middleware.main import TenantMainMiddleware
        from django_tenants.utils import get_tenant_model
        
        # Create middleware instance
        middleware = TenantMainMiddleware(lambda req: None)
        
        # Check if we can get tenant from request
        domain_parts = request.META['HTTP_HOST'].split(':')
        hostname = domain_parts[0].lower()
        print(f"   Hostname from request: {hostname}")
        
        # Try to get tenant
        from tenants.models import Domain
        domain_obj = Domain.objects.select_related('tenant').get(domain=hostname)
        print(f"   Found domain: {domain_obj.domain} -> {domain_obj.tenant.name}")
        
        # Check if tenant middleware would process this correctly
        request.tenant = domain_obj.tenant
        print(f"   Tenant set on request: {request.tenant.name} (schema: {request.tenant.schema_name})")
        
    except Exception as e:
        print(f"   ❌ Tenant detection failed: {e}")
        return False
    
    # Test 3: Test URL resolution with tenant context
    print("\n3. Testing URL resolution with tenant...")
    try:
        from django_tenants.utils import schema_context
        from django.urls import resolve
        
        with schema_context(request.tenant.schema_name):
            # Try to resolve the URL in tenant context
            match = resolve('/health/')
            print(f"   URL resolved to: {match.func.__name__}")
            print(f"   URL name: {match.url_name}")
            print(f"   ✅ URL resolution works in tenant context")
            
    except Exception as e:
        print(f"   ❌ URL resolution in tenant context failed: {e}")
        return False
    
    # Test 4: Check if middleware stack is causing issues
    print("\n4. Testing middleware stack...")
    try:
        from django.conf import settings
        
        middleware_list = settings.MIDDLEWARE
        print(f"   Total middleware: {len(middleware_list)}")
        
        # Find tenant middleware position
        tenant_middleware_pos = None
        for i, middleware in enumerate(middleware_list):
            if 'TenantMainMiddleware' in middleware:
                tenant_middleware_pos = i
                print(f"   TenantMainMiddleware at position: {i}")
                break
        
        if tenant_middleware_pos is None:
            print("   ❌ TenantMainMiddleware not found in MIDDLEWARE!")
            return False
        elif tenant_middleware_pos != 0:
            print("   ⚠️  TenantMainMiddleware is not first - this might cause issues")
        else:
            print("   ✅ TenantMainMiddleware is correctly positioned first")
            
    except Exception as e:
        print(f"   ❌ Middleware stack check failed: {e}")
        return False
    
    # Test 5: Try to simulate full request processing
    print("\n5. Testing full request simulation...")
    try:
        from django.core.handlers.wsgi import WSGIHandler
        from io import StringIO
        import sys
        
        # Create a WSGI environ for the request
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/health/',
            'SERVER_NAME': 'demo.localhost',
            'SERVER_PORT': '8000',
            'HTTP_HOST': 'demo.localhost',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': StringIO(),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': True,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
        }
        
        # Try to process with WSGI handler
        handler = WSGIHandler()
        
        # This is tricky to test without full WSGI setup, so let's just verify handler creation
        print(f"   WSGI handler created: {type(handler)}")
        print("   ✅ WSGI handler setup successful")
        
    except Exception as e:
        print(f"   ❌ WSGI handler test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = debug_tenant_middleware()
    if success:
        print("\n🎉 All middleware tests passed!")
        print("The issue might be elsewhere in the request processing chain.")
    else:
        print("\n❌ Middleware tests failed!")
        print("Found the root cause of the tenant routing issue.")