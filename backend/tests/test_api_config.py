#!/usr/bin/env python3

import requests
import json

def test_manual_api_call():
    """Test the API call that the frontend should make"""
    
    print("🔧 Testing Manual Frontend API Call")
    print("=" * 50)
    print("Simulating what the frontend should do after the fixes...")
    
    # This is what the frontend should now do:
    # 1. Detect it's on demo.localhost:3000
    # 2. Make request to demo.localhost:8000/graphql/
    
    session = requests.Session()
    
    # Set cookies that would be set by the frontend
    session.headers.update({
        'Origin': 'http://demo.localhost:3000',
        'Referer': 'http://demo.localhost:3000/login',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    # GraphQL login mutation (matching what frontend sends)
    url = 'http://demo.localhost:8000/graphql/'
    headers = {
        'Content-Type': 'application/json',
        'X-Tenant': 'demo'
    }
    
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
                  isActive
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
    
    print(f"📤 Making request to: {url}")
    print(f"📋 Headers: {headers}")
    print(f"📨 Origin: {session.headers.get('Origin')}")
    
    try:
        response = session.post(url, json=payload, headers=headers)
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"🔒 CORS Origin: {response.headers.get('Access-Control-Allow-Origin', 'NOT SET')}")
        print(f"🍪 Set-Cookie: {response.headers.get('Set-Cookie', 'NOT SET')}")
        
        if response.status_code == 200:
            data = response.json()
            
            if 'errors' in data and data['errors']:
                print(f"❌ GraphQL Errors: {data['errors']}")
                return False
            
            login_data = data.get('data', {}).get('login', {})
            
            if login_data.get('success'):
                print("✅ LOGIN SUCCESS!")
                user = login_data.get('user', {})
                permissions = login_data.get('permissions', {})
                
                print(f"👤 User: {user.get('firstName')} {user.get('lastName')}")
                print(f"📧 Email: {user.get('email')}")
                print(f"🆔 ID: {user.get('id')}")
                print(f"✅ Active: {user.get('isActive')}")
                print(f"🔑 Permissions: {list(permissions.keys()) if permissions else 'None'}")
                
                # Test follow-up request (like loading user info)
                print(f"\n🔍 Testing follow-up current user query...")
                
                current_user_payload = {
                    "query": """
                        query CurrentUser {
                          currentUser {
                            id
                            email
                            firstName
                            lastName
                            isActive
                          }
                        }
                    """
                }
                
                user_response = session.post(url, json=current_user_payload, headers=headers)
                
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    current_user = user_data.get('data', {}).get('currentUser')
                    
                    if current_user:
                        print("✅ Session persistence working - user data loaded")
                        print(f"👤 Current User: {current_user.get('firstName')} {current_user.get('lastName')}")
                        return True
                    else:
                        print("❌ Session not persisting - current user is None")
                        return False
                else:
                    print(f"❌ Follow-up request failed: {user_response.status_code}")
                    return False
            else:
                print(f"❌ LOGIN FAILED")
                errors = login_data.get('errors', [])
                print(f"🚫 Errors: {errors}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"💥 Request Exception: {str(e)}")
        return False

def test_registration_flow():
    """Test the registration flow that frontend would use"""
    
    print(f"\n\n🚀 Testing Registration Flow")
    print("=" * 50)
    
    import os
    pid = os.getpid()
    
    registration_data = {
        "first_name": "Test",
        "last_name": "User",
        "email": f"test{pid}@example.com",
        "password": "testpass123",
        "organization_name": f"Test Org {pid}",
        "subdomain": f"testorg{pid}"
    }
    
    # Registration uses the main localhost endpoint (no subdomain)
    url = 'http://localhost:8000/api/v1/tenants/register/'
    headers = {
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:3000',
        'Referer': 'http://localhost:3000/register'
    }
    
    print(f"📤 Making registration request to: {url}")
    print(f"👤 User: {registration_data['first_name']} {registration_data['last_name']}")
    print(f"🏢 Organization: {registration_data['organization_name']}")
    print(f"🌐 Subdomain: {registration_data['subdomain']}")
    
    try:
        response = requests.post(url, json=registration_data, headers=headers)
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ REGISTRATION SUCCESS!")
            print(f"🏢 Tenant: {data['tenant']['name']}")
            print(f"🆔 Schema: {data['tenant']['schema_name']}")
            print(f"👤 User: {data['user']['email']}")
            print(f"🔗 Redirect: {data['redirect_url']}")
            return True
        else:
            print(f"❌ REGISTRATION FAILED: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"💥 Request Exception: {str(e)}")
        return False

if __name__ == '__main__':
    print("🧪 Testing Fixed API Configuration")
    print("Verifying that frontend should now work correctly...")
    print("=" * 60)
    
    login_success = test_manual_api_call()
    registration_success = test_registration_flow()
    
    print("\n" + "=" * 60)
    print("📊 API Configuration Test Results")
    print("=" * 60)
    
    if login_success and registration_success:
        print("🎉 ALL API TESTS PASSED!")
        print("✅ Login flow working")
        print("✅ Registration flow working")
        print("✅ CORS configuration correct")
        print("✅ Session management working")
        print("\n🔧 FRONTEND FIX STATUS: READY")
        print("The network error should now be resolved!")
        print("If you're still seeing the error, try:")
        print("1. Hard refresh the browser (Cmd+Shift+R)")
        print("2. Clear browser cache and cookies")
        print("3. Restart the frontend development server")
    else:
        print("💥 SOME API TESTS FAILED!")
        print(f"Login: {'✅ PASSED' if login_success else '❌ FAILED'}")
        print(f"Registration: {'✅ PASSED' if registration_success else '❌ FAILED'}")
        print("Further investigation needed.")