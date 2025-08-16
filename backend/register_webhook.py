#!/usr/bin/env python3
"""
Register webhook with UniPile
"""
import os
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.unipile_sdk import unipile_service
from oneo_crm.settings import unipile_settings


async def register_webhook():
    """Register our webhook URL with UniPile"""
    
    print("🔗 Registering Webhook with UniPile...")
    print("=" * 50)
    
    try:
        # Get UniPile client
        client = unipile_service.get_client()
        webhook_url = unipile_settings.get_webhook_url()
        
        print(f"Webhook URL: {webhook_url}")
        
        # Check existing webhooks first
        print("\n📋 Checking existing webhooks...")
        existing_webhooks = await client.webhooks.list_webhooks()
        
        webhook_exists = False
        for webhook in existing_webhooks:
            if webhook.get('url') == webhook_url:
                webhook_exists = True
                print(f"✅ Webhook already registered:")
                print(f"   ID: {webhook.get('id')}")
                print(f"   URL: {webhook.get('url')}")
                print(f"   Events: {webhook.get('events', 'All')}")
                break
        
        if not webhook_exists:
            print(f"\n🔄 Registering webhooks for different sources...")
            
            # Register multiple webhooks for different sources
            webhooks_created = []
            
            # 1. Messaging webhook
            try:
                print("   📨 Creating messaging webhook...")
                messaging_result = await client.webhooks.create_messaging_webhook(
                    url=webhook_url,
                    name="OneoCRM Messaging Webhook"
                )
                webhooks_created.append(('Messaging', messaging_result))
                webhook_id = messaging_result.get('webhook_id') or messaging_result.get('id')
                print(f"   ✅ Messaging webhook created: {webhook_id}")
            except Exception as e:
                print(f"   ❌ Messaging webhook failed: {e}")
            
            # 2. Email webhook
            try:
                print("   📧 Creating email webhook...")
                email_result = await client.webhooks.create_email_webhook(
                    url=webhook_url,
                    name="OneoCRM Email Webhook"
                )
                webhooks_created.append(('Email', email_result))
                webhook_id = email_result.get('webhook_id') or email_result.get('id')
                print(f"   ✅ Email webhook created: {webhook_id}")
            except Exception as e:
                print(f"   ❌ Email webhook failed: {e}")
            
            # 3. Account status webhook
            try:
                print("   👤 Creating account status webhook...")
                account_result = await client.webhooks.create_account_status_webhook(
                    url=webhook_url,
                    name="OneoCRM Account Status Webhook"
                )
                webhooks_created.append(('Account Status', account_result))
                webhook_id = account_result.get('webhook_id') or account_result.get('id')
                print(f"   ✅ Account status webhook created: {webhook_id}")
            except Exception as e:
                print(f"   ❌ Account status webhook failed: {e}")
            
            if webhooks_created:
                print(f"\n✅ {len(webhooks_created)} webhooks registered successfully!")
                for webhook_type, result in webhooks_created:
                    webhook_id = result.get('webhook_id') or result.get('id')
                    print(f"   {webhook_type}:")
                    print(f"     ID: {webhook_id}")
                    print(f"     Object: {result.get('object')}")
                    print(f"     Raw Response: {result}")
            else:
                print("   ❌ No webhooks were created successfully")
        
        # Get updated webhook count
        try:
            updated_webhooks = await client.webhooks.list_webhooks()
            print(f"\n📊 Total webhooks registered: {len(updated_webhooks)}")
        except Exception as e:
            print(f"\n📊 Could not get updated webhook count: {e}")
        
        # Test webhook endpoint
        print(f"\n🧪 Testing webhook endpoint accessibility...")
        import requests
        
        try:
            # Simple GET request to webhook (should return method not allowed but confirms it's accessible)
            response = requests.get(webhook_url, timeout=10)
            if response.status_code in [200, 405]:  # 405 = Method Not Allowed is expected for GET
                print(f"✅ Webhook endpoint is accessible")
            else:
                print(f"⚠️  Webhook endpoint returned status {response.status_code}")
        except Exception as e:
            print(f"❌ Webhook endpoint not accessible: {e}")
            print("   Make sure your Cloudflare tunnel is running!")
        
        print("\n" + "=" * 50)
        print("🎉 Webhook Registration Complete!")
        
    except Exception as e:
        print(f"❌ Failed to register webhook: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(register_webhook())