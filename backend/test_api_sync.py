#!/usr/bin/env python3
"""
Test sync via API call
"""
import requests
import json

def test_api_sync():
    """Test the sync API endpoint"""
    
    # Read the JWT token for the correct user
    with open('/tmp/josh_jwt_token.txt', 'r') as f:
        token = f.read().strip()
    
    url = "http://oneotalent.localhost:8000/api/v1/communications/whatsapp/sync/"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    print("🔄 Calling comprehensive sync API...")
    
    try:
        response = requests.post(url, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Sync successful!")
            print(json.dumps(result, indent=2))
        else:
            print(f"❌ Sync failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error calling sync API: {e}")

if __name__ == "__main__":
    test_api_sync()