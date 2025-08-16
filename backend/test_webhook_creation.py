#!/usr/bin/env python3
"""
Test webhook creation and response
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


async def test_webhook_creation():
    """Test webhook creation response"""
    
    print("🔗 Testing Webhook Creation Response...")
    print("=" * 50)
    
    try:
        client = unipile_service.get_client()
        webhook_url = unipile_settings.get_webhook_url()
        
        print(f"Creating messaging webhook at: {webhook_url}")
        
        # Create messaging webhook and check response
        result = await client.webhooks.create_messaging_webhook(
            url=webhook_url,
            name="Test OneoCRM Messaging Webhook"
        )
        
        print("Raw webhook creation response:")
        print(json.dumps(result, indent=2))
        
        # List webhooks to see what was created
        print("\nListing all webhooks:")
        webhooks = await client.webhooks.list_webhooks()
        print(json.dumps(webhooks, indent=2))
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_webhook_creation())
