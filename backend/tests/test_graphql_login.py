#!/usr/bin/env python3

import os
import sys
import django

# Add the backend directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import requests
import json

def test_graphql_login():
    """Test GraphQL login with demo account credentials"""
    
    # Test GraphQL login with demo credentials
    url = 'http://demo.localhost:8000/graphql/'
    headers = {
        'Content-Type': 'application/json',
        'X-Tenant': 'demo'
    }

    # GraphQL mutation for login
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

    print("Testing GraphQL login...")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()

    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response

if __name__ == '__main__':
    test_graphql_login()