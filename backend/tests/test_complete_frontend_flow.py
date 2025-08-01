#!/usr/bin/env python3

import os
import sys
import django
import requests
import json

# Add the backend directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_complete_frontend_login_flow():
    """Test the complete frontend login flow exactly as the browser would do it"""
    
    print("🌐 Complete Frontend Login Flow Test")
    print("=" * 60)
    print("Simulating exactly what the frontend browser does...")
    
    # Create a session to maintain cookies like a browser
    session = requests.Session()
    
    print("\n📱 Step 1: User visits demo.localhost:3000/login")
    print("   Frontend loads and prepares to make login request...")
    
    # Step 1: GraphQL Login (authApi.login -> authGraphQL.login)
    print("\n🔑 Step 2: Frontend calls authApi.login(credentials)")
    print("   This calls authGraphQL.login() which POSTs to GraphQL endpoint...")
    
    graphql_url = 'http://demo.localhost:8000/graphql/'
    headers = {
        'Content-Type': 'application/json',
        'Origin': 'http://demo.localhost:3000',
        'X-Tenant': 'demo'
    }
    
    login_payload = {
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
    
    print(f"   POST {graphql_url}")
    
    login_response = session.post(graphql_url, json=login_payload, headers=headers)
    print(f"   Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"   ❌ GraphQL request failed: {login_response.text}")
        return False
    
    login_data = login_response.json()
    if 'errors' in login_data and login_data['errors']:
        print(f"   ❌ GraphQL errors: {login_data['errors']}")
        return False
    
    login_result = login_data.get('data', {}).get('login', {})
    if not login_result.get('success'):
        print(f"   ❌ Login failed: {login_result.get('errors', [])}")
        return False
    
    print("   ✅ GraphQL login successful!")
    user = login_result.get('user', {})
    print(f"   User: {user.get('firstName')} {user.get('lastName')} ({user.get('email')})")
    
    # Check if we got session cookies
    session_cookies = session.cookies.get_dict()
    print(f"   Cookies received: {list(session_cookies.keys())}")
    
    # Step 2: Get Tenant Info (authApi.getCurrentTenant)
    print("\n🏢 Step 3: Frontend calls authApi.getCurrentTenant()")
    print("   This calls api.get('/api/v1/auth/tenant_info/')...")
    
    tenant_url = 'http://demo.localhost:8000/api/v1/auth/tenant_info/'
    tenant_headers = {
        'Origin': 'http://demo.localhost:3000',
        'X-Tenant': 'demo'
    }
    
    print(f"   GET {tenant_url}")
    
    tenant_response = session.get(tenant_url, headers=tenant_headers)
    print(f"   Status: {tenant_response.status_code}")
    
    if tenant_response.status_code == 403:
        print("   ⚠️  403 Forbidden - Session cookies might not be working properly")
        print("   This could be the source of the 404-like error")
        
        # Let's check what cookies we have
        print(f"   Session cookies: {session_cookies}")
        
        # Try to check if the session is actually working with GraphQL
        print("\n🔍 Testing session with GraphQL currentUser query...")
        current_user_query = {
            "query": """
                query CurrentUser {
                  currentUser {
                    id
                    email
                    firstName
                    lastName
                  }
                }
            """
        }
        
        current_user_response = session.post(graphql_url, json=current_user_query, headers=headers)
        if current_user_response.status_code == 200:
            current_user_data = current_user_response.json()
            current_user = current_user_data.get('data', {}).get('currentUser')
            if current_user:
                print("   ✅ GraphQL session working - user is authenticated")
                print(f"   Current user: {current_user.get('email')}")
                
                # The issue might be that REST API and GraphQL use different session handling
                print("   🔍 Issue: GraphQL session working but REST API session not working")
                return "session_mismatch"
            else:
                print("   ❌ GraphQL session also broken")
                return False
        else:
            print("   ❌ GraphQL session check failed")
            return False
    
    elif tenant_response.status_code == 200:
        tenant_data = tenant_response.json()
        print("   ✅ Tenant info retrieved successfully!")
        print(f"   Tenant: {tenant_data.get('name', 'N/A')}")
        print(f"   Schema: {tenant_data.get('schema_name', 'N/A')}")
        
        # Step 3: Store tenant cookie (what frontend does next)
        print("\n🍪 Step 4: Frontend stores tenant cookie")
        print("   Cookies.set('oneo_tenant', tenantData.schema_name)...")
        
        # Simulate what frontend does
        tenant_schema = tenant_data.get('schema_name')
        if tenant_schema:
            session.cookies.set('oneo_tenant', tenant_schema)
            print(f"   Stored tenant cookie: {tenant_schema}")
        
        print("\n🎯 Step 5: Frontend redirects to dashboard")
        print("   router.push('/dashboard')")
        print("   ✅ Login flow completed successfully!")
        return True
    
    elif tenant_response.status_code == 404:
        print("   ❌ 404 Not Found - This is the error the frontend is seeing!")
        print("   The endpoint doesn't exist or URL is wrong")
        return False
    
    else:
        print(f"   ❌ Unexpected status: {tenant_response.status_code}")
        print(f"   Response: {tenant_response.text}")
        return False

def test_session_compatibility():
    """Test if Django session cookies work for both GraphQL and REST API"""
    
    print(f"\n\n🔗 Session Compatibility Test")
    print("=" * 50)
    print("Testing if GraphQL login creates sessions that work with REST API...")
    
    session = requests.Session()
    
    # Step 1: Login via GraphQL
    graphql_login_payload = {
        "query": """
            mutation Login($input: LoginInput!) {
              login(input: $input) {
                success
                user { id email }
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
    
    graphql_response = session.post(
        'http://demo.localhost:8000/graphql/',
        json=graphql_login_payload,
        headers={'Content-Type': 'application/json', 'X-Tenant': 'demo'}
    )
    
    if graphql_response.status_code == 200:
        login_data = graphql_response.json()
        if login_data.get('data', {}).get('login', {}).get('success'):
            print("✅ GraphQL login successful")
            
            cookies = session.cookies.get_dict()
            print(f"Cookies: {list(cookies.keys())}")
            
            # Step 2: Try REST API with same session
            rest_response = session.get(
                'http://demo.localhost:8000/api/v1/auth/tenant_info/',
                headers={'X-Tenant': 'demo'}
            )
            
            print(f"REST API response: {rest_response.status_code}")
            
            if rest_response.status_code == 200:
                print("✅ Session compatibility: GraphQL login works with REST API")
                return True
            elif rest_response.status_code == 403:
                print("❌ Session compatibility: GraphQL session doesn't work with REST API")
                return False
            else:
                print(f"⚠️  Unexpected REST API response: {rest_response.status_code}")
        else:
            print("❌ GraphQL login failed")
    else:
        print("❌ GraphQL request failed")
    
    return False

if __name__ == '__main__':
    print("🧪 Complete Frontend Flow Debug")
    print("Debugging the exact flow that causes the 404 error...")
    print("=" * 70)
    
    # Test complete login flow
    flow_result = test_complete_frontend_login_flow()
    
    # Test session compatibility
    session_compat = test_session_compatibility()
    
    print("\n" + "=" * 70)
    print("📊 Complete Flow Test Results")
    print("=" * 70)
    
    if flow_result == True:
        print("🎉 FRONTEND LOGIN FLOW: WORKING PERFECTLY!")
        print("✅ GraphQL login successful")
        print("✅ Tenant info retrieval successful")
        print("✅ Cookie handling working")
        print("✅ Complete flow ready for frontend")
    elif flow_result == "session_mismatch":
        print("⚠️  FRONTEND LOGIN FLOW: PARTIAL ISSUE")
        print("✅ GraphQL login working")
        print("❌ REST API session compatibility issue")
        print("🔧 Need to fix session handling between GraphQL and REST API")
    else:
        print("💥 FRONTEND LOGIN FLOW: FAILED")
        print("❌ Something is broken in the login flow")
    
    print(f"\nSession Compatibility: {'✅ WORKING' if session_compat else '❌ BROKEN'}")
    
    if not session_compat:
        print("\n🔧 SOLUTION NEEDED:")
        print("The GraphQL login and REST API need to use compatible session handling")
        print("This explains why frontend gets 404/403 errors after GraphQL login succeeds")