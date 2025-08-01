#!/usr/bin/env python3

import requests
import json

def test_frontend_api_calls():
    """Debug what URLs the frontend should be calling"""
    
    print("🔍 Frontend API Debug Test")
    print("=" * 50)
    
    # Test the URLs that the frontend dynamic configuration should generate
    test_cases = [
        {
            'name': 'Demo GraphQL (what frontend should call)',
            'url': 'http://demo.localhost:8000/graphql/',
            'origin': 'http://demo.localhost:3000'
        },
        {
            'name': 'Demo tenant info API',
            'url': 'http://demo.localhost:8000/api/v1/auth/tenant_info/',
            'origin': 'http://demo.localhost:3000'
        },
        {
            'name': 'Main registration API',
            'url': 'http://localhost:8000/api/v1/tenants/register/',
            'origin': 'http://localhost:3000'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📍 Testing: {test_case['name']}")
        print(f"   URL: {test_case['url']}")
        print(f"   Origin: {test_case['origin']}")
        
        # Test CORS preflight
        preflight_headers = {
            'Origin': test_case['origin'],
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type, X-Tenant'
        }
        
        try:
            preflight_response = requests.options(test_case['url'], headers=preflight_headers, timeout=5)
            cors_origin = preflight_response.headers.get('Access-Control-Allow-Origin', 'NOT SET')
            print(f"   CORS Preflight: {preflight_response.status_code} -> {cors_origin}")
        except requests.exceptions.RequestException as e:
            print(f"   CORS Preflight: FAILED - {str(e)}")
        
        # Test GET request
        get_headers = {
            'Origin': test_case['origin'],
            'X-Tenant': 'demo' if 'demo.localhost' in test_case['url'] else None
        }
        get_headers = {k: v for k, v in get_headers.items() if v is not None}
        
        try:
            get_response = requests.get(test_case['url'], headers=get_headers, timeout=5)
            print(f"   GET Request: {get_response.status_code}")
            
            if get_response.status_code == 404:
                print(f"   ❌ 404 ERROR - Endpoint not found!")
            elif get_response.status_code == 200:
                print(f"   ✅ Endpoint accessible")
            else:
                print(f"   ⚠️  Status: {get_response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   GET Request: FAILED - {str(e)}")

def test_graphql_login_directly():
    """Test GraphQL login directly to see if it works"""
    
    print(f"\n\n🔧 Direct GraphQL Login Test")
    print("=" * 50)
    
    url = 'http://demo.localhost:8000/graphql/'
    headers = {
        'Content-Type': 'application/json',
        'Origin': 'http://demo.localhost:3000',
        'X-Tenant': 'demo'
    }
    
    # Exact same GraphQL mutation that frontend should send
    payload = {
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
                permissions
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
    
    print(f"📤 POST {url}")
    print(f"📋 Headers: {headers}")
    print(f"📨 Payload: {json.dumps(payload['variables'], indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"🔒 CORS: {response.headers.get('Access-Control-Allow-Origin', 'NOT SET')}")
        
        if response.status_code == 404:
            print("❌ 404 ERROR - GraphQL endpoint not found!")
            print("This explains the frontend 404 error.")
            return False
        elif response.status_code == 200:
            data = response.json()
            if 'errors' in data and data['errors']:
                print(f"❌ GraphQL Errors: {data['errors']}")
                return False
            
            login_result = data.get('data', {}).get('login', {})
            if login_result.get('success'):
                print("✅ GraphQL login working!")
                user = login_result.get('user', {})
                print(f"👤 User: {user.get('firstName')} {user.get('lastName')}")
                return True
            else:
                print(f"❌ Login failed: {login_result.get('errors', [])}")
                return False
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"💥 Request failed: {str(e)}")
        return False

def check_url_routing():
    """Check if there are any URL routing issues"""
    
    print(f"\n\n🛣️  URL Routing Check")
    print("=" * 50)
    
    # Check various URL patterns that might be causing issues
    urls_to_check = [
        'http://demo.localhost:8000/',
        'http://demo.localhost:8000/graphql',  # without trailing slash
        'http://demo.localhost:8000/graphql/',  # with trailing slash
        'http://demo.localhost:8000/api/',
        'http://demo.localhost:8000/api/v1/',
        'http://demo.localhost:8000/api/v1/auth/',
        'http://demo.localhost:8000/api/v1/auth/tenant_info/',
    ]
    
    for url in urls_to_check:
        try:
            response = requests.get(url, timeout=5, headers={'X-Tenant': 'demo'})
            status_emoji = "✅" if response.status_code == 200 else "❌" if response.status_code == 404 else "⚠️"
            print(f"   {status_emoji} {url} -> {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"   💥 {url} -> {str(e)}")

if __name__ == '__main__':
    print("🧪 Frontend 404 Error Debug")
    print("Investigating what's causing the 404 error...")
    print("=" * 60)
    
    # Test API endpoints
    test_frontend_api_calls()
    
    # Test GraphQL directly
    graphql_success = test_graphql_login_directly()
    
    # Check URL routing
    check_url_routing()
    
    print("\n" + "=" * 60)
    print("📊 Debug Results")
    print("=" * 60)
    
    if graphql_success:
        print("✅ GraphQL endpoint is working correctly")
        print("🔍 The 404 error might be a frontend configuration issue")
        print("\nPossible causes:")
        print("• Frontend cache needs clearing")
        print("• Dynamic URL generation not working in browser")
        print("• Browser making request to wrong URL")
    else:
        print("❌ GraphQL endpoint has issues")
        print("🔧 Backend needs investigation")
    
    print(f"\n💡 Next steps:")
    print("1. Check browser developer tools -> Network tab")
    print("2. See what exact URL the frontend is requesting")
    print("3. Compare with working URLs above")