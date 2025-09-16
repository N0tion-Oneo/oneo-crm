#!/usr/bin/env python
import requests
import json

# Test workflow API
base_url = "http://oneotalent.localhost:8000"

# Login first
login_data = {
    "email": "josh@oneodigital.com",
    "password": "Admin123!"
}

print("1. Logging in...")
login_response = requests.post(f"{base_url}/auth/login/", json=login_data)

if login_response.status_code == 200:
    tokens = login_response.json()
    access_token = tokens.get('access')
    print(f"✓ Login successful. Access token: {access_token[:20]}...")
    
    # Fetch workflows
    print("\n2. Fetching workflows...")
    headers = {"Authorization": f"Bearer {access_token}"}
    workflows_response = requests.get(f"{base_url}/api/v1/workflows/", headers=headers)
    
    if workflows_response.status_code == 200:
        workflows = workflows_response.json()
        print(f"✓ Found {len(workflows.get('results', workflows))} workflows:")
        for wf in workflows.get('results', workflows):
            print(f"   - {wf['name']} (ID: {wf['id']}, Status: {wf['status']})")
    else:
        print(f"✗ Failed to fetch workflows: {workflows_response.status_code}")
        print(f"  Response: {workflows_response.text}")
else:
    print(f"✗ Login failed: {login_response.status_code}")
    print(f"  Response: {login_response.text}")