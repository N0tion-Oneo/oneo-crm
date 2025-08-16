#!/usr/bin/env python3
"""
Test hosted authentication with debugging
"""
import os
import django
import asyncio
import json
import aiohttp

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.unipile_sdk import unipile_service
from oneo_crm.settings import unipile_settings


async def test_hosted_auth_debug():
    """Test hosted authentication with detailed error debugging"""
    
    print("🔗 Testing Hosted Authentication with Debug...")
    print("=" * 50)
    
    try:
        # Test raw API call to hosted/accounts/link
        print("Testing raw API call to hosted/accounts/link...")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'X-API-KEY': unipile_settings.api_key,
                'Content-Type': 'application/json',
            }
            
            data = {
                'provider': 'linkedin',
                'redirect_url': 'https://app.oneocrm.com/auth/callback'
            }
            
            url = f"{unipile_settings.base_url}/hosted/accounts/link"
            print(f"URL: {url}")
            print(f"Data: {json.dumps(data, indent=2)}")
            
            async with session.post(url, json=data, headers=headers) as response:
                response_text = await response.text()
                print(f"Status: {response.status}")
                print(f"Response: {response_text}")
                
                # Try to parse as JSON
                try:
                    response_json = json.loads(response_text)
                    print(f"JSON Response:")
                    print(json.dumps(response_json, indent=2))
                except:
                    print("Response is not valid JSON")
        
        print("\n" + "=" * 50)
        print("🎉 Debug Test Complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_hosted_auth_debug())
