#!/usr/bin/env python3
"""
Debug the actual API response to see what conversation IDs are being returned
"""

import os
import django
import json
import requests

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_local_inbox_api():
    """Test the actual local inbox API response"""
    print("🔍 TESTING ACTUAL LOCAL INBOX API RESPONSE")
    print("=" * 80)
    
    try:
        # Test the API endpoint directly
        url = "http://oneotalent.localhost:8000/api/v1/communications/local-inbox/"
        
        # Note: This will fail with 401 because we don't have auth token
        # But we can still see the endpoint structure
        response = requests.get(url, timeout=10)
        
        print(f"📡 API URL: {url}")
        print(f"📊 Response Status: {response.status_code}")
        print(f"📝 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 401:
            print("✅ Expected 401 - endpoint exists but needs authentication")
        elif response.status_code == 200:
            data = response.json()
            print(f"📋 Response Data: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            print(f"📝 Response Text: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def show_expected_vs_actual():
    """Show what we expect vs what might be happening"""
    print(f"\n📊 EXPECTED vs ACTUAL API RESPONSE")
    print("=" * 60)
    
    print("✅ EXPECTED (after our fix):")
    expected = {
        "conversations": [
            {
                "id": "whatsapp_1T1s9uwKX3yXDdHr9p9uWQ",  # NEW FORMAT
                "database_id": "1691322e-db0b-4fa5-908c-e61fc10de3be",  # UUID for reference
                "type": "whatsapp",
                "participants": [
                    {
                        "name": "Vanessa",  # REAL NAME from metadata/known contacts
                        "email": "27849977040@s.whatsapp.net",
                        "platform": "whatsapp"
                    }
                ]
            }
        ]
    }
    print(json.dumps(expected, indent=2))
    
    print("\n❌ ACTUAL (if fix didn't apply):")
    actual = {
        "conversations": [
            {
                "id": "1691322e-db0b-4fa5-908c-e61fc10de3be",  # OLD UUID FORMAT
                "type": "whatsapp", 
                "participants": [
                    {
                        "name": "27849977040",  # PHONE NUMBER ONLY
                        "email": "27849977040@s.whatsapp.net",
                        "platform": "whatsapp"
                    }
                ]
            }
        ]
    }
    print(json.dumps(actual, indent=2))

def debug_frontend_caching():
    """Debug potential frontend caching issues"""
    print(f"\n🔧 FRONTEND CACHING DEBUG")
    print("=" * 40)
    
    print("Potential issues:")
    print("1. ❌ Browser cache - frontend using old API response")
    print("2. ❌ React state cache - old conversation data in memory")
    print("3. ❌ Axios cache - HTTP cache headers")
    print("4. ❌ Backend not reloaded - old code still running")
    
    print("\nFixes to try:")
    print("1. 🔄 Hard refresh browser (Cmd+Shift+R)")
    print("2. 🔄 Restart frontend development server")
    print("3. 🔄 Clear browser dev tools -> Application -> Storage -> Clear Site Data")
    print("4. 🔄 Restart backend server to load new code")

def main():
    """Main function"""
    test_local_inbox_api()
    show_expected_vs_actual()
    debug_frontend_caching()
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Restart both frontend and backend servers")
    print("2. Hard refresh browser to clear any cached API responses")
    print("3. Test send message functionality to see if 400 error is fixed")
    print("4. Check if conversation list now shows proper contact names")

if __name__ == '__main__':
    main()