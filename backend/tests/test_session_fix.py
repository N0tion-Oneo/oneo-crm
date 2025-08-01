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

def test_session_constraint_fix():
    """Test that session constraint violation is fixed"""
    
    print("🔧 Testing Session Constraint Fix")
    print("=" * 50)
    
    # Create a session to simulate browser behavior
    session = requests.Session()
    
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
    
    print("🔑 Test 1: First login attempt")
    print(f"   URL: {graphql_url}")
    print(f"   Credentials: admin@demo.com / admin123")
    
    # First login attempt
    response1 = session.post(graphql_url, json=payload, headers=headers)
    print(f"   Status: {response1.status_code}")
    
    if response1.status_code == 200:
        data1 = response1.json()
        if 'errors' in data1 and data1['errors']:
            print(f"   ❌ GraphQL Errors: {data1['errors']}")
            return False
        
        login_result1 = data1.get('data', {}).get('login', {})
        if login_result1.get('success'):
            print("   ✅ First login: SUCCESS")
            user1 = login_result1.get('user', {})
            print(f"   User: {user1.get('firstName')} {user1.get('lastName')}")
        else:
            print(f"   ❌ First login failed: {login_result1.get('errors', [])}")
            return False
    else:
        print(f"   ❌ HTTP Error: {response1.status_code}")
        return False
    
    print("\n🔑 Test 2: Second login attempt (should not cause constraint violation)")
    
    # Second login attempt with same session - this used to cause the constraint violation
    response2 = session.post(graphql_url, json=payload, headers=headers)
    print(f"   Status: {response2.status_code}")
    
    if response2.status_code == 200:
        data2 = response2.json()
        if 'errors' in data2 and data2['errors']:
            print(f"   ❌ GraphQL Errors: {data2['errors']}")
            return False
        
        login_result2 = data2.get('data', {}).get('login', {})
        if login_result2.get('success'):
            print("   ✅ Second login: SUCCESS")
            user2 = login_result2.get('user', {})
            print(f"   User: {user2.get('firstName')} {user2.get('lastName')}")
        else:
            print(f"   ❌ Second login failed: {login_result2.get('errors', [])}")
            return False
    else:
        print(f"   ❌ HTTP Error: {response2.status_code}")
        return False
    
    print("\n🔍 Test 3: Multiple rapid login attempts")
    
    # Test multiple rapid login attempts to stress test the fix
    for i in range(3):
        print(f"   Attempt {i+1}/3...")
        response = session.post(graphql_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data and data['errors']:
                print(f"   ❌ Attempt {i+1} failed: {data['errors']}")
                return False
            
            login_result = data.get('data', {}).get('login', {})
            if not login_result.get('success'):
                print(f"   ❌ Attempt {i+1} login failed: {login_result.get('errors', [])}")
                return False
        else:
            print(f"   ❌ Attempt {i+1} HTTP error: {response.status_code}")
            return False
    
    print("   ✅ All rapid login attempts successful")
    
    print("\n🎯 Test 4: Current user query after login")
    
    # Test that session is working properly
    current_user_query = """
    query CurrentUser {
      currentUser {
        id
        email
        firstName
        lastName
      }
    }
    """
    
    current_user_payload = {'query': current_user_query}
    user_response = session.post(graphql_url, json=current_user_payload, headers=headers)
    
    if user_response.status_code == 200:
        user_data = user_response.json()
        current_user = user_data.get('data', {}).get('currentUser')
        
        if current_user:
            print("   ✅ Session working: Current user loaded")
            print(f"   User: {current_user.get('firstName')} {current_user.get('lastName')}")
            print(f"   Email: {current_user.get('email')}")
        else:
            print("   ❌ Session broken: No current user")
            return False
    else:
        print(f"   ❌ Current user query failed: {user_response.status_code}")
        return False
    
    return True

def test_different_browsers():
    """Test login from different 'browsers' (different sessions)"""
    
    print(f"\n\n🌐 Testing Multiple Browser Sessions")
    print("=" * 50)
    
    graphql_url = 'http://demo.localhost:8000/graphql/'
    headers = {
        'Content-Type': 'application/json',
        'X-Tenant': 'demo'
    }
    
    login_mutation = """
    mutation Login($input: LoginInput!) {
      login(input: $input) {
        success
        user { id email firstName lastName }
      }
    }
    """
    
    payload = {
        'query': login_mutation,
        'variables': {
            'input': {
                'username': 'admin@demo.com',
                'password': 'admin123',
                'rememberMe': False
            }
        }
    }
    
    success_count = 0
    
    # Simulate 3 different browsers/sessions
    for i in range(3):
        print(f"\n   Browser {i+1}: Creating new session...")
        browser_session = requests.Session()
        
        response = browser_session.post(graphql_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if not 'errors' in data or not data['errors']:
                login_result = data.get('data', {}).get('login', {})
                if login_result.get('success'):
                    print(f"   ✅ Browser {i+1}: Login successful")
                    success_count += 1
                else:
                    print(f"   ❌ Browser {i+1}: Login failed")
            else:
                print(f"   ❌ Browser {i+1}: GraphQL errors: {data['errors']}")
        else:
            print(f"   ❌ Browser {i+1}: HTTP error: {response.status_code}")
    
    if success_count == 3:
        print(f"\n✅ All {success_count} browser sessions logged in successfully")
        return True
    else:
        print(f"\n❌ Only {success_count}/3 browser sessions succeeded")
        return False

if __name__ == '__main__':
    print("🧪 Session Constraint Violation Fix Test")
    print("Testing that duplicate session key errors are resolved...")
    print("=" * 60)
    
    # Test the session constraint fix
    constraint_fix_success = test_session_constraint_fix()
    
    # Test multiple browser sessions
    multi_browser_success = test_different_browsers()
    
    print("\n" + "=" * 60)
    print("📊 Session Fix Test Results")
    print("=" * 60)
    
    if constraint_fix_success and multi_browser_success:
        print("🎉 ALL SESSION TESTS PASSED!")
        print("✅ Session constraint violation fixed")
        print("✅ Multiple login attempts working")
        print("✅ Rapid login attempts working")
        print("✅ Multi-browser sessions working")
        print("✅ Session persistence working")
        print("\n🔧 SESSION FIX STATUS: RESOLVED")
        print("The duplicate key constraint error should now be fixed!")
    else:
        print("💥 SOME SESSION TESTS FAILED!")
        print(f"Constraint Fix: {'✅ PASSED' if constraint_fix_success else '❌ FAILED'}")
        print(f"Multi-Browser: {'✅ PASSED' if multi_browser_success else '❌ FAILED'}")
        print("Further investigation needed.")