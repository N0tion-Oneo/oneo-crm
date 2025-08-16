#!/usr/bin/env python3
"""
Test hosted authentication flow
"""
import os
import django
import asyncio
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.unipile_sdk import unipile_service
from oneo_crm.settings import unipile_settings


async def test_hosted_auth():
    """Test hosted authentication flow"""
    
    print("🔗 Testing Hosted Authentication Flow...")
    print("=" * 50)
    
    try:
        client = unipile_service.get_client()
        
        # Test hosted authentication request for LinkedIn
        print("1. Testing LinkedIn hosted auth link request...")
        redirect_url = "https://app.oneocrm.com/auth/callback"
        
        try:
            linkedin_result = await client.account.request_hosted_link(
                provider='linkedin',
                redirect_url=redirect_url
            )
            print(f"✅ LinkedIn hosted auth link:")
            print(json.dumps(linkedin_result, indent=2))
        except Exception as e:
            print(f"❌ LinkedIn hosted auth failed: {e}")
        
        # Test hosted authentication request for Gmail
        print("\n2. Testing Gmail hosted auth link request...")
        try:
            gmail_result = await client.account.request_hosted_link(
                provider='gmail', 
                redirect_url=redirect_url
            )
            print(f"✅ Gmail hosted auth link:")
            print(json.dumps(gmail_result, indent=2))
        except Exception as e:
            print(f"❌ Gmail hosted auth failed: {e}")
        
        # Test hosted authentication request for WhatsApp
        print("\n3. Testing WhatsApp hosted auth link request...")
        try:
            whatsapp_result = await client.account.request_hosted_link(
                provider='whatsapp',
                redirect_url=redirect_url
            )
            print(f"✅ WhatsApp hosted auth link:")
            print(json.dumps(whatsapp_result, indent=2))
        except Exception as e:
            print(f"❌ WhatsApp hosted auth failed: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 Hosted Authentication Test Complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_hosted_auth())
