#!/usr/bin/env python3
"""
Test hosted authentication with correct format
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


async def test_hosted_auth_fixed():
    """Test hosted authentication with correct UniPile format"""
    
    print("🔗 Testing Hosted Authentication (Fixed Format)...")
    print("=" * 50)
    
    try:
        client = unipile_service.get_client()
        
        # Test hosted authentication request for LinkedIn
        print("1. Testing LinkedIn hosted auth link request...")
        
        try:
            linkedin_result = await client.account.request_hosted_link(
                providers='linkedin',
                success_redirect_url='https://app.oneocrm.com/auth/success',
                failure_redirect_url='https://app.oneocrm.com/auth/error', 
                name='OneoCRM LinkedIn Connection',
                notify_url='https://webhooks.oneocrm.com/webhooks/unipile/'
            )
            print(f"✅ LinkedIn hosted auth link:")
            print(json.dumps(linkedin_result, indent=2))
        except Exception as e:
            print(f"❌ LinkedIn hosted auth failed: {e}")
        
        # Test hosted authentication request for Gmail
        print("\n2. Testing Gmail hosted auth link request...")
        try:
            gmail_result = await client.account.request_hosted_link(
                providers='gmail',
                success_redirect_url='https://app.oneocrm.com/auth/success',
                failure_redirect_url='https://app.oneocrm.com/auth/error',
                name='OneoCRM Gmail Connection',
                notify_url='https://webhooks.oneocrm.com/webhooks/unipile/'
            )
            print(f"✅ Gmail hosted auth link:")
            print(json.dumps(gmail_result, indent=2))
        except Exception as e:
            print(f"❌ Gmail hosted auth failed: {e}")
        
        # Test multi-provider hosted auth
        print("\n3. Testing multi-provider hosted auth link request...")
        try:
            multi_result = await client.account.request_hosted_link(
                providers=['linkedin', 'gmail', 'whatsapp'],
                success_redirect_url='https://app.oneocrm.com/auth/success',
                failure_redirect_url='https://app.oneocrm.com/auth/error',
                name='OneoCRM Multi-Provider Connection',
                notify_url='https://webhooks.oneocrm.com/webhooks/unipile/'
            )
            print(f"✅ Multi-provider hosted auth link:")
            print(json.dumps(multi_result, indent=2))
        except Exception as e:
            print(f"❌ Multi-provider hosted auth failed: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 Hosted Authentication Test Complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_hosted_auth_fixed())
