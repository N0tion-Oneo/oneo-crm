#!/usr/bin/env python3

import requests
import json

def test_cors_configuration():
    """Test CORS configuration for frontend connections"""
    
    print("🌐 Testing Frontend-Backend Connection")
    print("=" * 50)
    
    # Test CORS preflight request from demo.localhost:3000
    print("\n1. Testing CORS preflight request from demo.localhost:3000")
    
    preflight_headers = {
        'Origin': 'http://demo.localhost:3000',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type, X-Tenant'
    }
    
    response = requests.options('http://demo.localhost:8000/graphql/', headers=preflight_headers)
    print(f"   Status: {response.status_code}")
    print(f"   Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'NOT SET')}")
    print(f"   Access-Control-Allow-Credentials: {response.headers.get('Access-Control-Allow-Credentials', 'NOT SET')}")
    
    if response.status_code == 200 and 'demo.localhost:3000' in response.headers.get('Access-Control-Allow-Origin', ''):
        print("   ✅ CORS preflight successful")
    else:
        print("   ❌ CORS preflight failed")
    
    # Test actual GraphQL request with origin header
    print("\n2. Testing GraphQL request with origin header")
    
    graphql_headers = {
        'Origin': 'http://demo.localhost:3000',
        'Content-Type': 'application/json',
        'X-Tenant': 'demo'
    }
    
    login_query = {
        "query": """
        mutation Login($input: LoginInput!) {
          login(input: $input) {
            success
            errors
            user {
              id
              email
              firstName
              lastName
            }
          }
        }
        """,
        "variables": {
            "input": {
                "username": "admin@demo.com",
                "password": "admin123",
                "rememberMe": False
            }
        }
    }
    
    response = requests.post('http://demo.localhost:8000/graphql/', 
                           json=login_query, 
                           headers=graphql_headers)
    
    print(f"   Status: {response.status_code}")
    print(f"   Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'NOT SET')}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('data', {}).get('login', {}).get('success'):
            print("   ✅ GraphQL login successful with CORS")
            return True
        else:
            print(f"   ❌ GraphQL login failed: {data}")
            return False
    else:
        print(f"   ❌ HTTP error: {response.text}")
        return False

def test_different_subdomains():
    """Test CORS with different tenant subdomains"""
    
    print("\n\n🏢 Testing Different Tenant Subdomains")
    print("=" * 50)
    
    subdomains = ['demo.localhost:3000', 'test.localhost:3000', 'localhost:3000']
    
    for subdomain in subdomains:
        print(f"\n   Testing origin: http://{subdomain}")
        
        headers = {
            'Origin': f'http://{subdomain}',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        # Use the matching backend subdomain
        backend_host = subdomain.replace(':3000', ':8000')
        backend_url = f'http://{backend_host}/graphql/'
        
        try:
            response = requests.options(backend_url, headers=headers, timeout=5)
            cors_origin = response.headers.get('Access-Control-Allow-Origin', 'NOT SET')
            
            if response.status_code == 200:
                print(f"   ✅ CORS OK for {subdomain} -> {cors_origin}")
            else:
                print(f"   ❌ CORS failed for {subdomain}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Connection failed for {subdomain}: {str(e)}")

if __name__ == '__main__':
    print("🧪 Frontend-Backend Connection Test")
    print("Testing CORS and API connectivity...")
    
    success = test_cors_configuration()
    test_different_subdomains()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Frontend-Backend Connection: WORKING")
        print("Frontend should now be able to connect successfully!")
    else:
        print("💥 Frontend-Backend Connection: FAILED")
        print("Check CORS configuration and backend status")