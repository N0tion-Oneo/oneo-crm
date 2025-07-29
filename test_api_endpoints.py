#!/usr/bin/env python
"""
Test script to validate API endpoints are working
"""
import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_api_endpoints():
    """Test API endpoints with proper tenant setup"""
    
    print("🧪 Testing Phase 5 API Endpoints")
    print("=" * 50)
    
    # Create a test client
    client = Client()
    
    # Test tenant health check first
    print("1. Testing tenant health check...")
    try:
        response = client.get('/health/', HTTP_HOST='demo.localhost')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
            print("   ✅ Tenant health check working")
        else:
            print(f"   ❌ Tenant health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Tenant health check error: {e}")
        return False
    
    # Test API endpoints
    endpoints_to_test = [
        '/api/v1/',
        '/api/v1/pipelines/',
        '/api/v1/schema/',
        '/pipelines/',  # Root level
        '/graphql/',
    ]
    
    print("\n2. Testing API endpoints...")
    for endpoint in endpoints_to_test:
        try:
            response = client.get(endpoint, HTTP_HOST='demo.localhost')
            status = "✅" if response.status_code in [200, 401, 403] else "❌"
            print(f"   {endpoint}: {response.status_code} {status}")
            
            # For debugging, show some response content
            if response.status_code == 404:
                print(f"      404 - Endpoint not found")
            elif response.status_code == 500:
                print(f"      500 - Server error")
                
        except Exception as e:
            print(f"   {endpoint}: ❌ Error - {e}")
    
    print("\n3. Testing URL routing...")
    try:
        from django.urls import reverse
        from django.urls.exceptions import NoReverseMatch
        
        # Test if we can reverse some key URLs
        try:
            pipeline_url = reverse('api:pipeline-list')
            print(f"   Pipeline list URL: {pipeline_url} ✅")
        except NoReverseMatch as e:
            print(f"   Pipeline list URL: ❌ {e}")
            
    except Exception as e:
        print(f"   URL reversal test failed: {e}")
    
    print("\n4. Testing GraphQL schema...")
    try:
        from api.graphql.strawberry_schema import schema
        print(f"   GraphQL schema loaded: ✅")
        
        # Test a simple introspection
        introspection_query = "{ __schema { queryType { name } } }"
        result = schema.execute_sync(introspection_query)
        if result.errors:
            print(f"   GraphQL errors: {result.errors}")
        else:
            print(f"   GraphQL introspection: ✅")
            
    except Exception as e:
        print(f"   GraphQL schema test failed: {e}")
    
    return True

if __name__ == "__main__":
    test_api_endpoints()