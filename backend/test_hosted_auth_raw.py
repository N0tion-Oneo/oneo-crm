#!/usr/bin/env python3
"""
Test hosted authentication with raw API debugging
"""
import os
import django
import asyncio
import json
import aiohttp
from datetime import datetime, timedelta, timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from oneo_crm.settings import unipile_settings


async def test_hosted_auth_raw():
    """Test hosted authentication with raw API call"""
    
    print("🔗 Testing Hosted Authentication (Raw API)...")
    print("=" * 50)
    
    try:
        # Set expiration to 24 hours from now  
        expires_on = (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'
        
        # Test data based on UniPile API spec
        data = {
            'type': 'create',
            'api_url': unipile_settings.dsn,
            'expiresOn': expires_on,
            'providers': ['LINKEDIN']
        }
        
        print(f"API URL: {unipile_settings.base_url}/hosted/accounts/link")
        print(f"DSN: {unipile_settings.dsn}")
        print(f"API Key: {'*' * (len(unipile_settings.api_key) - 4) + unipile_settings.api_key[-4:]}")
        print(f"Request Data:")
        print(json.dumps(data, indent=2))
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'X-API-KEY': unipile_settings.api_key,
                'Content-Type': 'application/json',
            }
            
            url = f"{unipile_settings.base_url}/hosted/accounts/link"
            
            async with session.post(url, json=data, headers=headers) as response:
                response_text = await response.text()
                print(f"\nResponse Status: {response.status}")
                print(f"Response Text: {response_text}")
                
                # Try to parse as JSON
                try:
                    response_json = json.loads(response_text)
                    print(f"JSON Response:")
                    print(json.dumps(response_json, indent=2))
                except:
                    print("Response is not valid JSON")
        
        print("\n" + "=" * 50)
        print("🎉 Raw API Test Complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_hosted_auth_raw())
