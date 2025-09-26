#!/usr/bin/env python
"""Test script to verify system fields are returned from the API."""

import requests
import json

# Configuration
BASE_URL = "http://oneotalent.localhost:8000"
AUTH_URL = f"{BASE_URL}/auth/login/"

# Test credentials
credentials = {
    "email": "admin@oneotalent.com",
    "password": "Admin123!"
}

def test_system_fields():
    # Login first
    print("1. Logging in...")
    login_response = requests.post(AUTH_URL, json=credentials)
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        print(login_response.text)
        return

    tokens = login_response.json()
    access_token = tokens.get("access")
    print("✓ Login successful")

    # Get pipelines
    print("\n2. Getting pipelines...")
    headers = {"Authorization": f"Bearer {access_token}"}
    pipelines_response = requests.get(f"{BASE_URL}/api/v1/pipelines/", headers=headers)
    pipelines = pipelines_response.json()

    if isinstance(pipelines, dict) and 'results' in pipelines:
        pipelines = pipelines['results']

    if not pipelines:
        print("No pipelines found")
        return

    pipeline_id = pipelines[0]['id']
    print(f"✓ Found pipeline: {pipelines[0]['name']} (ID: {pipeline_id})")

    # Test fields WITHOUT system fields
    print("\n3. Testing fields WITHOUT system fields...")
    fields_url = f"{BASE_URL}/api/v1/pipelines/{pipeline_id}/fields/"
    response = requests.get(fields_url, headers=headers)
    fields_data = response.json()

    if isinstance(fields_data, dict) and 'results' in fields_data:
        fields_data = fields_data['results']

    print(f"   - Total fields: {len(fields_data)}")
    system_count = sum(1 for f in fields_data if f.get('id', '').startswith('system_'))
    print(f"   - System fields: {system_count}")

    # Test fields WITH system fields
    print("\n4. Testing fields WITH system fields...")
    response = requests.get(f"{fields_url}?include_system=true", headers=headers)
    fields_data = response.json()

    if isinstance(fields_data, dict) and 'results' in fields_data:
        fields_data = fields_data['results']

    print(f"   - Total fields: {len(fields_data)}")
    system_count = sum(1 for f in fields_data if f.get('id', '').startswith('system_'))
    print(f"   - System fields: {system_count}")

    if system_count > 0:
        print("\n✅ System fields found:")
        for field in fields_data:
            if field.get('id', '').startswith('system_'):
                print(f"   - {field['display_name']} ({field['name']}) - {field['field_type']}")
    else:
        print("\n❌ No system fields found")

    print("\n5. Raw response preview:")
    print(json.dumps(fields_data[:2], indent=2))

if __name__ == "__main__":
    test_system_fields()