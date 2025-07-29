#!/usr/bin/env python
"""
Test the simplest possible tenant URL configuration
"""
import os
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_simple_tenant_config():
    """Test the simplest tenant configuration"""
    
    print("🧪 Testing Simple Tenant URL Configuration")
    print("=" * 50)
    
    # Create a test URL configuration in memory
    from django.urls import path
    from django.http import JsonResponse
    
    def simple_view(request):
        return JsonResponse({
            "message": "Simple view works!",
            "tenant": getattr(request, 'tenant', None).name if hasattr(request, 'tenant') else "No tenant",
            "host": request.META.get('HTTP_HOST', 'No host')
        })
    
    # Test with the in-memory URL patterns
    from django.test import Client
    
    # Override URL configuration temporarily
    original_urlconf = settings.ROOT_URLCONF
    
    # Create temporary URL module
    import sys
    from types import ModuleType
    
    temp_urls = ModuleType('temp_urls')
    temp_urls.urlpatterns = [
        path('simple/', simple_view, name='simple_view'),
    ]
    
    sys.modules['temp_urls'] = temp_urls
    
    # Test with temporary URLs
    settings.ROOT_URLCONF = 'temp_urls'
    
    try:
        client = Client()
        
        print("1. Testing simple view with public schema...")
        response = client.get('/simple/', HTTP_HOST='localhost')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        
        print("\n2. Testing simple view with tenant schema...")
        response = client.get('/simple/', HTTP_HOST='demo.localhost')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
            print("   🎉 TENANT ROUTING WORKS!")
        else:
            print("   ❌ Tenant routing still broken")
            
    finally:
        # Restore original URL configuration
        settings.ROOT_URLCONF = original_urlconf
        if 'temp_urls' in sys.modules:
            del sys.modules['temp_urls']

if __name__ == "__main__":
    test_simple_tenant_config()