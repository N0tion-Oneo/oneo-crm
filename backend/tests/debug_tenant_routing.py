#!/usr/bin/env python
"""
Debug tenant routing issues
"""
import os
import sys
import django
from django.test import Client

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def debug_routing():
    """Debug tenant routing step by step"""
    
    print("🔍 Debugging Tenant Routing")
    print("=" * 40)
    
    # Test 1: Check if Django is configured correctly
    print("1. Testing Django configuration...")
    try:
        from django.conf import settings
        print(f"   ROOT_URLCONF: {settings.ROOT_URLCONF}")
        print(f"   TENANT_APPS: {len(settings.TENANT_APPS)} apps")
        print(f"   SHARED_APPS: {len(settings.SHARED_APPS)} apps")
        print("   ✅ Django configuration loaded")
    except Exception as e:
        print(f"   ❌ Django configuration error: {e}")
        return
    
    # Test 2: Check tenant middleware
    print("\n2. Testing tenant detection...")
    try:
        from django_tenants.utils import get_tenant_model
        Tenant = get_tenant_model()
        demo_tenant = Tenant.objects.get(schema_name='demo')
        print(f"   Demo tenant: {demo_tenant.name} ✅")
        
        from tenants.models import Domain
        demo_domain = Domain.objects.get(domain='demo.localhost')
        print(f"   Demo domain: {demo_domain.domain} -> {demo_domain.tenant.name} ✅")
    except Exception as e:
        print(f"   ❌ Tenant detection error: {e}")
        return
    
    # Test 3: Check URL patterns
    print("\n3. Testing URL patterns...")
    try:
        from django.urls import resolve, reverse
        from django.urls.exceptions import Resolver404
        
        # Test tenant URLs
        try:
            from oneo_crm.urls_tenants import urlpatterns as tenant_patterns
            print(f"   Tenant URL patterns: {len(tenant_patterns)} patterns ✅")
            
            # Print the patterns for debugging
            for i, pattern in enumerate(tenant_patterns):
                print(f"     {i+1}. {pattern.pattern} -> {pattern.callback}")
                
        except Exception as e:
            print(f"   ❌ Tenant URL patterns error: {e}")
            
    except Exception as e:
        print(f"   ❌ URL patterns error: {e}")
    
    # Test 4: Simulate request processing
    print("\n4. Testing request simulation...")
    try:
        client = Client()
        
        # Test with demo.localhost
        print("   Testing demo.localhost...")
        response = client.get('/', HTTP_HOST='demo.localhost')
        print(f"     Root: {response.status_code}")
        
        # Try admin (should work)
        response = client.get('/admin/', HTTP_HOST='demo.localhost')  
        print(f"     Admin: {response.status_code}")
        
        # Try health endpoint
        response = client.get('/health/', HTTP_HOST='demo.localhost')
        print(f"     Health: {response.status_code}")
        
        # Try to get the actual error details
        if response.status_code == 404:
            # Get the resolver to see what patterns are available
            from django.urls import get_resolver
            resolver = get_resolver()
            print(f"     Available patterns: {len(resolver.url_patterns)}")
            
    except Exception as e:
        print(f"   ❌ Request simulation error: {e}")
    
    # Test 5: Check if there are conflicts in URL configuration
    print("\n5. Testing URL configuration conflicts...")
    try:
        # Check for the duplicate namespace warning
        from django.core.checks import run_checks
        from django.core.checks.urls import check_url_config
        
        issues = run_checks(include_deployment_checks=False)
        if issues:
            print("   Django system check issues:")
            for issue in issues:
                print(f"     {issue.level}: {issue.msg}")
        else:
            print("   ✅ No Django system check issues")
            
    except Exception as e:
        print(f"   ❌ URL configuration check error: {e}")

if __name__ == "__main__":
    debug_routing()