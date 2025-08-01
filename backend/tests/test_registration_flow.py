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

def test_tenant_registration():
    """Test tenant registration endpoint"""
    
    print("🚀 Testing Tenant Registration Flow")
    print("=" * 50)
    
    # Test data for registration
    registration_data = {
        "first_name": "John",
        "last_name": "Smith", 
        "email": "john@testcorp.com",
        "password": "testpass123",
        "organization_name": "Test Corp Registration",
        "subdomain": "testcorp"
    }
    
    print("\n1. Testing Tenant Registration...")
    print(f"Registration Data: {json.dumps(registration_data, indent=2)}")
    
    # Registration endpoint (uses public schema)
    url = 'http://localhost:8000/api/v1/tenants/register/'
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, json=registration_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 201:
        response_data = response.json()
        print("✅ Tenant Registration: SUCCESS")
        print(f"   Tenant: {response_data['tenant']['name']} ({response_data['tenant']['schema_name']})")
        print(f"   User: {response_data['user']['first_name']} {response_data['user']['last_name']} ({response_data['user']['email']})")
        print(f"   Domain: {response_data['domain']['domain']}")
        
        # Test 2: Login to the new tenant
        print("\n2. Testing Login to New Tenant...")
        tenant_domain = response_data['domain']['domain']
        tenant_schema = response_data['tenant']['schema_name']
        user_email = response_data['user']['email']
        
        login_url = f'http://{tenant_domain}:8000/graphql/'
        login_headers = {
            'Content-Type': 'application/json',
            'X-Tenant': tenant_schema
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
            }
            permissions
          }
        }
        """
        
        login_variables = {
            'input': {
                'username': user_email,
                'password': registration_data['password'],
                'rememberMe': False
            }
        }
        
        login_payload = {
            'query': login_mutation,
            'variables': login_variables
        }
        
        login_response = requests.post(login_url, json=login_payload, headers=login_headers)
        print(f"Status Code: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            if login_data.get('data', {}).get('login', {}).get('success'):
                print("✅ New Tenant Login: SUCCESS")
                user_data = login_data['data']['login']['user']
                print(f"   User: {user_data['firstName']} {user_data['lastName']} ({user_data['email']})")
                print(f"   Permissions: {len(login_data['data']['login']['permissions'])} permission categories")
                return True
            else:
                print("❌ New Tenant Login: FAILED")
                print(f"   Errors: {login_data.get('data', {}).get('login', {}).get('errors', [])}")
                return False
        else:
            print("❌ New Tenant Login: HTTP ERROR")
            print(f"   Response: {login_response.text}")
            return False
            
    elif response.status_code == 400:
        response_data = response.json()
        print("❌ Tenant Registration: VALIDATION ERROR")
        print(f"   Errors: {response_data}")
        
        # Check if it's a duplicate error (expected for testing)
        details = response_data.get('details', {})
        if 'organization_name' in str(response_data) or 'subdomain' in str(response_data) or details.get('subdomain'):
            print("   This appears to be a duplicate organization/subdomain - trying with unique data...")
            
            # Try with unique data
            unique_data = registration_data.copy()
            unique_data['organization_name'] = f"Test Corp Unique {os.getpid()}"
            unique_data['subdomain'] = f"testunique{os.getpid()}"
            unique_data['email'] = f"john{os.getpid()}@testcorp.com"
            
            print(f"\nRetrying with unique data: {json.dumps(unique_data, indent=2)}")
            
            retry_response = requests.post(url, json=unique_data, headers=headers)
            print(f"Retry Status Code: {retry_response.status_code}")
            
            if retry_response.status_code == 201:
                print("✅ Tenant Registration with Unique Data: SUCCESS")
                return True
            else:
                print("❌ Tenant Registration with Unique Data: FAILED")
                print(f"   Response: {retry_response.text}")
                return False
        else:
            return False
    else:
        print("❌ Tenant Registration: HTTP ERROR")
        print(f"   Response: {response.text}")
        return False

if __name__ == '__main__':
    print("🧪 Starting Tenant Registration Test")
    print("=" * 40)
    
    success = test_tenant_registration()
    
    print("\n📊 Test Results Summary")
    print("=" * 30)
    print(f"Registration Flow: {'✅ PASSED' if success else '❌ FAILED'}")
    
    if success:
        print("\n🎉 REGISTRATION FLOW WORKING CORRECTLY!")
        sys.exit(0)
    else:
        print("\n💥 REGISTRATION FLOW NEEDS ATTENTION!")
        sys.exit(1)