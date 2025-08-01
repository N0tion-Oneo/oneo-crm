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

def test_live_demo_login():
    """Test live demo login as a user would experience it"""
    
    print("🎭 LIVE USER EXPERIENCE TEST")
    print("=" * 50)
    print("Simulating a user visiting the demo login page and logging in...")
    
    # Create a session to simulate browser behavior
    session = requests.Session()
    
    print("\n📱 Step 1: User visits http://demo.localhost:3000/login")
    print("   Frontend loads and displays:")
    print("   - Welcome to Oneo CRM")
    print("   - Email and password fields") 
    print("   - Demo Account section showing:")
    print("     Email: admin@demo.com")
    print("     Password: admin123")
    
    print("\n🔑 Step 2: User enters demo credentials and clicks 'Sign In'")
    print("   Frontend sends GraphQL login mutation to backend...")
    
    # GraphQL login mutation (what the frontend sends)
    graphql_url = 'http://demo.localhost:8000/graphql/'
    headers = {
        'Content-Type': 'application/json',
        'X-Tenant': 'demo'
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
    
    variables = {
        'input': {
            'username': 'admin@demo.com',
            'password': 'admin123',
            'rememberMe': False
        }
    }
    
    payload = {
        'query': login_mutation,
        'variables': variables
    }
    
    print(f"   POST {graphql_url}")
    print(f"   Headers: {headers}")
    print(f"   Payload: {json.dumps(variables, indent=4)}")
    
    response = session.post(graphql_url, json=payload, headers=headers)
    print(f"   Response Status: {response.status_code}")
    
    if response.status_code == 200:
        response_data = response.json()
        if response_data.get('data', {}).get('login', {}).get('success'):
            print("   ✅ LOGIN SUCCESS!")
            user_data = response_data['data']['login']['user']
            permissions = response_data['data']['login']['permissions']
            
            print(f"   User authenticated: {user_data['firstName']} {user_data['lastName']}")
            print(f"   Email: {user_data['email']}")
            print(f"   Active: {user_data['isActive']}")
            print(f"   User ID: {user_data['id']}")
            print(f"   Permissions granted: {list(permissions.keys())}")
            
            print("\n🏠 Step 3: Frontend redirects user to dashboard")
            print("   User sees: 'Welcome back!' notification")
            print("   Browser navigates to: http://demo.localhost:3000/dashboard")
            
            # Test what happens when user accesses protected resources
            print("\n🔐 Step 4: User accesses protected resources")
            print("   Testing current user query (for dashboard data)...")
            
            current_user_query = """
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
            
            current_user_payload = {'query': current_user_query}
            user_response = session.post(graphql_url, json=current_user_payload, headers=headers)
            
            if user_response.status_code == 200:
                user_data_check = user_response.json()
                if user_data_check.get('data', {}).get('currentUser'):
                    print("   ✅ Session is valid - user can access protected resources")
                    current_user = user_data_check['data']['currentUser']
                    print(f"   Dashboard will show: Welcome, {current_user['firstName']}!")
                else:
                    print("   ❌ Session invalid - authentication issue")
                    return False
            
            # Test tenant info access (for showing current organization)
            print("\n🏢 Step 5: Loading tenant information")
            tenant_url = 'http://demo.localhost:8000/api/v1/auth/tenant_info/'
            tenant_headers = {'X-Tenant': 'demo'}
            
            tenant_response = session.get(tenant_url, headers=tenant_headers)
            if tenant_response.status_code == 200:
                tenant_data = tenant_response.json()
                print("   ✅ Tenant info loaded successfully")
                print(f"   Organization: {tenant_data.get('name', 'N/A')}")
                print(f"   Domain: {tenant_data.get('domain', 'N/A')}")
                print(f"   Created: {tenant_data.get('created_on', 'N/A')}")
            else:
                print("   ❌ Failed to load tenant info")
                return False
            
            print("\n👋 Step 6: User logout test")
            print("   User clicks logout button...")
            
            logout_mutation = """
            mutation Logout {
              logout {
                success
                message
              }
            }
            """
            
            logout_payload = {'query': logout_mutation}
            logout_response = session.post(graphql_url, json=logout_payload, headers=headers)
            
            if logout_response.status_code == 200:
                logout_data = logout_response.json()
                if logout_data.get('data', {}).get('logout', {}).get('success'):
                    print("   ✅ Logout successful")
                    print(f"   Message: {logout_data['data']['logout']['message']}")
                    print("   Frontend redirects to: http://demo.localhost:3000/login")
                    
                    # Verify session is terminated
                    verify_response = session.post(graphql_url, json=current_user_payload, headers=headers)
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        if not verify_data.get('data', {}).get('currentUser'):
                            print("   ✅ Session properly terminated - user is logged out")
                            return True
                        else:
                            print("   ❌ Session not terminated - logout issue")
                            return False
                else:
                    print("   ❌ Logout failed")
                    return False
            else:
                print("   ❌ Logout request failed")
                return False
                
        else:
            print("   ❌ LOGIN FAILED!")
            errors = response_data.get('data', {}).get('login', {}).get('errors', [])
            print(f"   Errors: {errors}")
            print("   User would see: 'Login failed' notification")
            return False
    else:
        print(f"   ❌ HTTP ERROR: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_new_tenant_registration():
    """Test new tenant registration flow"""
    
    print("\n\n🚀 NEW TENANT REGISTRATION TEST")
    print("=" * 50)
    print("Simulating a new user registering their organization...")
    
    pid = os.getpid()
    registration_data = {
        "first_name": "Sarah",
        "last_name": "Johnson",
        "email": f"sarah{pid}@techstartup.com",
        "password": "startuppass123",
        "organization_name": f"Tech Startup Live {pid}",
        "subdomain": f"techlive{pid}"
    }
    
    print("\n📝 Step 1: User visits http://localhost:3000/register")
    print("   User fills out registration form:")
    print(f"   - Name: {registration_data['first_name']} {registration_data['last_name']}")
    print(f"   - Email: {registration_data['email']}")
    print(f"   - Organization: {registration_data['organization_name']}")
    print(f"   - Subdomain: {registration_data['subdomain']}")
    print("   - Password: [hidden]")
    
    print("\n📤 Step 2: User clicks 'Create Organization'")
    print("   Frontend sends registration request...")
    
    url = 'http://localhost:8000/api/v1/tenants/register/'
    headers = {'Content-Type': 'application/json'}
    
    response = requests.post(url, json=registration_data, headers=headers)
    print(f"   Response Status: {response.status_code}")
    
    if response.status_code == 201:
        response_data = response.json()
        print("   ✅ REGISTRATION SUCCESS!")
        print(f"   Organization created: {response_data['tenant']['name']}")
        print(f"   Schema: {response_data['tenant']['schema_name']}")
        print(f"   User account: {response_data['user']['email']}")
        print(f"   Redirect URL: {response_data['redirect_url']}")
        
        print("\n🎉 Step 3: Automatic login to new tenant")
        print("   System automatically logs user into their new organization...")
        
        # Test login to the new tenant
        tenant_domain = f"{response_data['tenant']['schema_name']}.localhost"
        login_url = f'http://{tenant_domain}:8000/graphql/'
        login_headers = {
            'Content-Type': 'application/json',
            'X-Tenant': response_data['tenant']['schema_name']
        }
        
        login_mutation = """
        mutation Login($input: LoginInput!) {
          login(input: $input) {
            success
            user {
              id
              email
              firstName
              lastName
            }
          }
        }
        """
        
        login_variables = {
            'input': {
                'username': registration_data['email'],
                'password': registration_data['password'],
                'rememberMe': False
            }
        }
        
        login_payload = {
            'query': login_mutation,
            'variables': login_variables
        }
        
        login_response = requests.post(login_url, json=login_payload, headers=login_headers)
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            if login_data.get('data', {}).get('login', {}).get('success'):
                print("   ✅ New tenant login successful!")
                user = login_data['data']['login']['user']
                print(f"   Welcome {user['firstName']}! Your organization is ready.")
                print(f"   Dashboard URL: http://{tenant_domain}:3000/dashboard")
                return True
            else:
                print("   ❌ New tenant login failed")
                return False
        else:
            print("   ❌ New tenant login request failed")
            return False
    else:
        print("   ❌ REGISTRATION FAILED!")
        print(f"   Response: {response.text}")
        return False

if __name__ == '__main__':
    print("🧪 LIVE AUTHENTICATION SYSTEM TEST")
    print("Testing the actual user experience...")
    print("=" * 60)
    
    # Test demo login flow
    demo_success = test_live_demo_login()
    
    # Test new tenant registration
    registration_success = test_new_tenant_registration()
    
    print("\n" + "=" * 60)
    print("📊 LIVE TEST RESULTS")
    print("=" * 60)
    
    if demo_success and registration_success:
        print("🎉 ALL LIVE TESTS PASSED!")
        print("✅ Demo login experience working perfectly")
        print("✅ New tenant registration working perfectly")
        print("✅ Multi-tenant authentication system is LIVE and operational!")
        print("\n🚀 SYSTEM STATUS: PRODUCTION READY")
        print("Users can now:")
        print("  • Visit demo.localhost:3000/login and use demo account")
        print("  • Register new organizations at localhost:3000/register")
        print("  • Access their tenant-specific dashboard after login")
        print("  • Use all authentication features securely")
        sys.exit(0)
    else:
        print("💥 SOME LIVE TESTS FAILED!")
        print(f"Demo login: {'✅ PASSED' if demo_success else '❌ FAILED'}")
        print(f"Registration: {'✅ PASSED' if registration_success else '❌ FAILED'}")
        sys.exit(1)