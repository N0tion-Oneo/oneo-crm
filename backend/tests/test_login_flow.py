#!/usr/bin/env python3

import os
import sys
import django
import requests
import json
from urllib.parse import urlparse

# Add the backend directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_complete_login_flow():
    """Test complete login flow including tenant info retrieval"""
    
    print("🧪 Testing Complete Login Flow")
    print("=" * 50)
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Step 1: Test GraphQL login
    print("\n1. Testing GraphQL Login...")
    graphql_url = 'http://demo.localhost:8000/graphql/'
    headers = {
        'Content-Type': 'application/json',
        'X-Tenant': 'demo'
    }

    mutation = """
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
    """

    variables = {
        'input': {
            'username': 'admin@demo.com',
            'password': 'admin123',
            'rememberMe': False
        }
    }

    payload = {
        'query': mutation,
        'variables': variables
    }

    login_response = session.post(graphql_url, json=payload, headers=headers)
    print(f"Status Code: {login_response.status_code}")
    
    if login_response.status_code == 200:
        login_data = login_response.json()
        if login_data.get('data', {}).get('login', {}).get('success'):
            print("✅ GraphQL Login: SUCCESS")
            user_data = login_data['data']['login']['user']
            print(f"   User: {user_data['firstName']} {user_data['lastName']} ({user_data['email']})")
        else:
            print("❌ GraphQL Login: FAILED")
            print(f"   Errors: {login_data.get('data', {}).get('login', {}).get('errors', [])}")
            return False
    else:
        print("❌ GraphQL Login: HTTP ERROR")
        print(f"   Response: {login_response.text}")
        return False
    
    # Step 2: Test tenant info retrieval
    print("\n2. Testing Tenant Info Retrieval...")
    tenant_url = 'http://demo.localhost:8000/api/v1/auth/tenant_info/'
    tenant_headers = {
        'X-Tenant': 'demo'
    }
    
    tenant_response = session.get(tenant_url, headers=tenant_headers)
    print(f"Status Code: {tenant_response.status_code}")
    
    if tenant_response.status_code == 200:
        tenant_data = tenant_response.json()
        print("✅ Tenant Info: SUCCESS")
        print(f"   Tenant: {tenant_data.get('name', 'N/A')} ({tenant_data.get('schema_name', 'N/A')})")
        
        # Step 3: Test current user via GraphQL
        print("\n3. Testing Current User Query...")
        current_user_query = """
        query CurrentUser {
          currentUser {
            id
            email
            firstName
            lastName
            isActive
            createdAt
          }
        }
        """
        
        current_user_payload = {
            'query': current_user_query
        }
        
        current_user_response = session.post(graphql_url, json=current_user_payload, headers=headers)
        print(f"Status Code: {current_user_response.status_code}")
        
        if current_user_response.status_code == 200:
            current_user_data = current_user_response.json()
            print(f"   Current User Response: {json.dumps(current_user_data, indent=2)}")
            if current_user_data.get('data', {}).get('currentUser'):
                print("✅ Current User Query: SUCCESS")
                user = current_user_data['data']['currentUser']
                print(f"   User: {user['firstName']} {user['lastName']} ({user['email']})")
                print(f"   Active: {user['isActive']}")
                
                # Step 4: Test logout
                print("\n4. Testing Logout...")
                logout_mutation = """
                mutation Logout {
                  logout {
                    success
                    message
                  }
                }
                """
                
                logout_payload = {
                    'query': logout_mutation
                }
                
                logout_response = session.post(graphql_url, json=logout_payload, headers=headers)
                print(f"Status Code: {logout_response.status_code}")
                
                if logout_response.status_code == 200:
                    logout_data = logout_response.json()
                    if logout_data.get('data', {}).get('logout', {}).get('success'):
                        print("✅ Logout: SUCCESS")
                        print(f"   Message: {logout_data['data']['logout']['message']}")
                        
                        # Step 5: Verify session is terminated
                        print("\n5. Verifying Session Termination...")
                        verify_response = session.post(graphql_url, json=current_user_payload, headers=headers)
                        if verify_response.status_code == 200:
                            verify_data = verify_response.json()
                            if not verify_data.get('data', {}).get('currentUser'):
                                print("✅ Session Termination: SUCCESS")
                                print("   User is no longer authenticated")
                                return True
                            else:
                                print("❌ Session Termination: FAILED")
                                print("   User is still authenticated")
                                return False
                    else:
                        print("❌ Logout: FAILED")
                        return False
                else:
                    print("❌ Logout: HTTP ERROR")
                    return False
            else:
                print("❌ Current User Query: FAILED")
                return False
        else:
            print("❌ Current User Query: HTTP ERROR")
            return False
    else:
        print("❌ Tenant Info: FAILED")
        print(f"   Response: {tenant_response.text}")
        return False

def test_multi_tenant_isolation():
    """Test multi-tenant isolation between demo and test tenants"""
    
    print("\n\n🔒 Testing Multi-Tenant Isolation")
    print("=" * 50)
    
    # Test 1: Login to demo tenant
    print("\n1. Login to Demo Tenant...")
    demo_session = requests.Session()
    demo_headers = {'Content-Type': 'application/json', 'X-Tenant': 'demo'}
    
    login_mutation = """
    mutation Login($input: LoginInput!) {
      login(input: $input) {
        success
        user { id email firstName lastName }
      }
    }
    """
    
    demo_login = {
        'query': login_mutation,
        'variables': {
            'input': {
                'username': 'admin@demo.com',
                'password': 'admin123',
                'rememberMe': False
            }
        }
    }
    
    demo_response = demo_session.post('http://demo.localhost:8000/graphql/', 
                                     json=demo_login, headers=demo_headers)
    
    if demo_response.status_code == 200 and demo_response.json().get('data', {}).get('login', {}).get('success'):
        print("✅ Demo Login: SUCCESS")
        
        # Test 2: Try to access test tenant with demo session
        print("\n2. Testing Cross-Tenant Access Prevention...")
        test_headers = {'Content-Type': 'application/json', 'X-Tenant': 'test'}
        
        current_user_query = """
        query CurrentUser {
          currentUser {
            id
            email
          }
        }
        """
        
        cross_tenant_payload = {'query': current_user_query}
        cross_tenant_response = demo_session.post('http://test.localhost:8000/graphql/',
                                                 json=cross_tenant_payload, headers=test_headers)
        
        if cross_tenant_response.status_code == 200:
            cross_tenant_data = cross_tenant_response.json()
            if not cross_tenant_data.get('data', {}).get('currentUser'):
                print("✅ Cross-Tenant Isolation: SUCCESS")
                print("   Demo session cannot access test tenant")
                return True
            else:
                print("❌ Cross-Tenant Isolation: FAILED")
                print("   Demo session can access test tenant data")
                return False
        else:
            print("✅ Cross-Tenant Isolation: SUCCESS (HTTP Level)")
            return True
    else:
        print("❌ Demo Login: FAILED")
        return False

if __name__ == '__main__':
    print("🚀 Starting Complete Authentication Flow Tests")
    print("=" * 60)
    
    # Test complete login flow
    login_flow_success = test_complete_login_flow()
    
    # Test multi-tenant isolation
    isolation_success = test_multi_tenant_isolation()
    
    print("\n\n📊 Test Results Summary")
    print("=" * 30)
    print(f"Login Flow Test: {'✅ PASSED' if login_flow_success else '❌ FAILED'}")
    print(f"Isolation Test: {'✅ PASSED' if isolation_success else '❌ FAILED'}")
    
    if login_flow_success and isolation_success:
        print("\n🎉 ALL TESTS PASSED - Authentication system is working correctly!")
        sys.exit(0)
    else:
        print("\n💥 SOME TESTS FAILED - Authentication system needs attention!")
        sys.exit(1)