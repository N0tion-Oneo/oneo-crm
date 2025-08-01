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

def test_complete_end_to_end_flow():
    """Test complete end-to-end flow: registration -> login -> tenant access"""
    
    print("🚀 Complete End-to-End Authentication Flow Test")
    print("=" * 60)
    
    # Generate unique test data
    pid = os.getpid()
    
    registration_data = {
        "first_name": "Jane",
        "last_name": "Doe", 
        "email": f"jane{pid}@newcompany.com",
        "password": "securepass123",
        "organization_name": f"New Company E2E {pid}",
        "subdomain": f"newe2e{pid}"
    }
    
    print("\n🔧 Step 1: Tenant Registration")
    print("=" * 40)
    print(f"Registration Data: {json.dumps(registration_data, indent=2)}")
    
    # Step 1: Register new tenant
    url = 'http://localhost:8000/api/v1/tenants/register/'
    headers = {'Content-Type': 'application/json'}
    
    response = requests.post(url, json=registration_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 201:
        print("❌ Registration Failed")
        print(f"Response: {response.text}")
        return False
    
    response_data = response.json()
    print("✅ Tenant Registration: SUCCESS")
    print(f"   Tenant: {response_data['tenant']['name']} ({response_data['tenant']['schema_name']})")
    print(f"   User: {response_data['user']['first_name']} {response_data['user']['last_name']} ({response_data['user']['email']})")
    
    # Debug: print full response to see structure
    print(f"   Full Response: {json.dumps(response_data, indent=2)}")
    
    # Extract info for next steps
    schema_name = response_data['tenant']['schema_name']
    tenant_domain = f"{schema_name}.localhost"  # construct domain from schema name
    user_email = response_data['user']['email']
    password = registration_data['password']
    
    print(f"\n🔑 Step 2: Login to New Tenant")
    print("=" * 40)
    
    # Step 2: Login to the newly created tenant
    login_url = f'http://{tenant_domain}:8000/graphql/'
    login_headers = {
        'Content-Type': 'application/json',
        'X-Tenant': schema_name
    }
    
    login_mutation = """
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
    
    login_variables = {
        'input': {
            'username': user_email,
            'password': password,
            'rememberMe': False
        }
    }
    
    login_payload = {
        'query': login_mutation,
        'variables': login_variables
    }
    
    print(f"Login URL: {login_url}")
    print(f"Login Headers: {login_headers}")
    
    login_session = requests.Session()
    login_response = login_session.post(login_url, json=login_payload, headers=login_headers)
    print(f"Status Code: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print("❌ Login Failed - HTTP Error")
        print(f"Response: {login_response.text}")
        return False
    
    login_data = login_response.json()
    if not login_data.get('data', {}).get('login', {}).get('success'):
        print("❌ Login Failed - GraphQL Error")
        print(f"Errors: {login_data.get('data', {}).get('login', {}).get('errors', [])}")
        return False
    
    print("✅ Login: SUCCESS")
    user_data = login_data['data']['login']['user']
    permissions = login_data['data']['login']['permissions']
    print(f"   User: {user_data['firstName']} {user_data['lastName']} ({user_data['email']})")
    print(f"   Active: {user_data['isActive']}")
    print(f"   Permissions: {len(permissions)} permission categories")
    
    print(f"\n📊 Step 3: Verify Session and Access")
    print("=" * 40)
    
    # Step 3: Test current user query to verify session
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
    
    current_user_payload = {'query': current_user_query}
    current_user_response = login_session.post(login_url, json=current_user_payload, headers=login_headers)
    print(f"Current User Query Status: {current_user_response.status_code}")
    
    if current_user_response.status_code == 200:
        current_user_data = current_user_response.json()
        if current_user_data.get('data', {}).get('currentUser'):
            print("✅ Session Verification: SUCCESS")
            user = current_user_data['data']['currentUser']
            print(f"   Current User: {user['firstName']} {user['lastName']} ({user['email']})")
        else:
            print("❌ Session Verification: FAILED")
            print(f"   Response: {current_user_data}")
            return False
    else:
        print("❌ Session Verification: HTTP ERROR")
        return False
    
    # Step 4: Test tenant info access
    tenant_info_url = f'http://{tenant_domain}:8000/api/v1/auth/tenant_info/'
    tenant_info_headers = {'X-Tenant': schema_name}
    
    tenant_info_response = login_session.get(tenant_info_url, headers=tenant_info_headers)
    print(f"Tenant Info Status: {tenant_info_response.status_code}")
    
    if tenant_info_response.status_code == 200:
        tenant_info = tenant_info_response.json()
        print("✅ Tenant Info Access: SUCCESS")
        print(f"   Tenant Name: {tenant_info.get('name', 'N/A')}")
        print(f"   Schema: {tenant_info.get('schema_name', 'N/A')}")
        print(f"   Domain: {tenant_info.get('domain', 'N/A')}")
    else:
        print("❌ Tenant Info Access: FAILED")
        print(f"   Response: {tenant_info_response.text}")
        return False
    
    print(f"\n🔒 Step 4: Test Multi-Tenant Isolation")
    print("=" * 40)
    
    # Step 5: Test cross-tenant access prevention
    # Try to access demo tenant with this session
    demo_headers = {'Content-Type': 'application/json', 'X-Tenant': 'demo'}
    demo_response = login_session.post('http://demo.localhost:8000/graphql/', 
                                      json=current_user_payload, headers=demo_headers)
    
    if demo_response.status_code == 200:
        demo_data = demo_response.json()
        if not demo_data.get('data', {}).get('currentUser'):
            print("✅ Tenant Isolation: SUCCESS")
            print("   New tenant session cannot access demo tenant")
        else:
            print("❌ Tenant Isolation: FAILED")
            print("   Cross-tenant access detected!")
            return False
    else:
        print("✅ Tenant Isolation: SUCCESS (HTTP Level)")
    
    print("\n🎯 Step 5: Logout Test")
    print("=" * 40)
    
    # Step 6: Test logout
    logout_mutation = """
    mutation Logout {
      logout {
        success
        message
      }
    }
    """
    
    logout_payload = {'query': logout_mutation}
    logout_response = login_session.post(login_url, json=logout_payload, headers=login_headers)
    
    if logout_response.status_code == 200:
        logout_data = logout_response.json()
        if logout_data.get('data', {}).get('logout', {}).get('success'):
            print("✅ Logout: SUCCESS")
            print(f"   Message: {logout_data['data']['logout']['message']}")
            
            # Verify session is terminated
            verify_response = login_session.post(login_url, json=current_user_payload, headers=login_headers)
            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                if not verify_data.get('data', {}).get('currentUser'):
                    print("✅ Session Termination: SUCCESS")
                    return True
                else:
                    print("❌ Session Termination: FAILED")
                    return False
        else:
            print("❌ Logout: FAILED")
            return False
    else:
        print("❌ Logout: HTTP ERROR")
        return False

if __name__ == '__main__':
    print("🧪 Starting Complete End-to-End Flow Test")
    print("=" * 50)
    
    success = test_complete_end_to_end_flow()
    
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS")
    print("=" * 60)
    
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Tenant registration working")
        print("✅ User login working")
        print("✅ Session management working")
        print("✅ Tenant isolation working")
        print("✅ Logout working")
        print("✅ Multi-tenant authentication system is fully operational!")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED!")
        print("❌ End-to-end flow needs attention")
        sys.exit(1)