#!/usr/bin/env python3
"""
Test UniPile connection and API
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


async def test_unipile_connection():
    """Test UniPile API connection"""
    
    print("🔗 Testing UniPile Connection...")
    print("=" * 50)
    
    try:
        # Check configuration
        print(f"DSN: {unipile_settings.dsn}")
        print(f"API Key: {'*' * (len(unipile_settings.api_key) - 4) + unipile_settings.api_key[-4:] if unipile_settings.api_key else 'Not set'}")
        print(f"Base URL: {unipile_settings.base_url}")
        print(f"Configured: {unipile_settings.is_configured()}")
        print(f"Webhook URL: {unipile_settings.get_webhook_url()}")
        
        if not unipile_settings.is_configured():
            print("❌ UniPile not configured properly")
            return
        
        # Get UniPile client
        client = unipile_service.get_client()
        
        print("\n📋 Testing API endpoints...")
        
        # Test 1: List accounts
        print("1. Testing GET /accounts...")
        try:
            accounts = await client.account.get_accounts()
            print(f"✅ Accounts endpoint working. Found {len(accounts)} accounts")
            for account in accounts[:3]:  # Show first 3
                print(f"   - Account ID: {account.get('id', 'N/A')}")
                print(f"     Provider: {account.get('provider', 'N/A')}")
                print(f"     Status: {account.get('status', 'N/A')}")
        except Exception as e:
            print(f"❌ Accounts endpoint failed: {e}")
        
        # Test 2: List webhooks
        print("\n2. Testing GET /webhooks...")
        try:
            webhooks = await client.webhooks.list_webhooks()
            print(f"✅ Webhooks endpoint working. Found {len(webhooks)} webhooks")
            for webhook in webhooks:
                print(f"   - Webhook ID: {webhook.get('id', 'N/A')}")
                print(f"     URL: {webhook.get('url', 'N/A')}")
                print(f"     Events: {webhook.get('events', 'N/A')}")
        except Exception as e:
            print(f"❌ Webhooks endpoint failed: {e}")
        
        # Test 3: Test webhook creation with simpler data
        print("\n3. Testing POST /webhooks (simplified)...")
        webhook_url = unipile_settings.get_webhook_url()
        
        try:
            # Try with minimal data first
            result = await client.webhooks.create_webhook(webhook_url)
            print(f"✅ Webhook creation successful!")
            print(f"   ID: {result.get('id')}")
            print(f"   URL: {result.get('url')}")
        except Exception as e:
            print(f"❌ Webhook creation failed: {e}")
            
            # Try to get more detailed error info
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    headers = {
                        'X-API-KEY': unipile_settings.api_key,
                        'Content-Type': 'application/json',
                    }
                    data = {'url': webhook_url}
                    
                    async with session.post(
                        f"{unipile_settings.base_url}/webhooks",
                        json=data,
                        headers=headers
                    ) as response:
                        response_text = await response.text()
                        print(f"   Raw response ({response.status}): {response_text}")
            except Exception as raw_e:
                print(f"   Could not get raw response: {raw_e}")
        
        print("\n" + "=" * 50)
        print("🎉 UniPile Connection Test Complete!")
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_unipile_connection())
