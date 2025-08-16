#!/usr/bin/env python3
"""
Complete UniPile Integration Test
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


async def test_complete_integration():
    """Complete end-to-end UniPile integration test"""
    
    print("🚀 Complete UniPile Integration Test")
    print("=" * 50)
    
    results = {
        'configuration': False,
        'connection': False,
        'webhooks': False,
        'hosted_auth': False
    }
    
    try:
        client = unipile_service.get_client()
        
        # 1. Test Configuration
        print("1. ✅ Configuration Test")
        print(f"   DSN: {unipile_settings.dsn}")
        print(f"   API Key: {'*' * (len(unipile_settings.api_key) - 4) + unipile_settings.api_key[-4:]}")
        print(f"   Base URL: {unipile_settings.base_url}")
        print(f"   Webhook URL: {unipile_settings.get_webhook_url()}")
        print(f"   Configured: {unipile_settings.is_configured()}")
        results['configuration'] = unipile_settings.is_configured()
        
        # 2. Test API Connection
        print("\n2. ✅ API Connection Test")
        try:
            accounts = await client.account.get_accounts()
            print(f"   Successfully connected to UniPile API")
            print(f"   Found {len(accounts)} existing accounts")
            results['connection'] = True
        except Exception as e:
            print(f"   ❌ API connection failed: {e}")
        
        # 3. Test Webhook Registration
        print("\n3. ✅ Webhook Registration Test")
        try:
            webhooks = await client.webhooks.list_webhooks()
            print(f"   Found {len(webhooks)} existing webhooks")
            
            # Test webhook creation
            webhook_url = unipile_settings.get_webhook_url()
            messaging_webhook = await client.webhooks.create_messaging_webhook(
                url=webhook_url,
                name="OneoCRM Integration Test Webhook"
            )
            webhook_id = messaging_webhook.get('webhook_id')
            print(f"   ✅ Successfully created test webhook: {webhook_id}")
            results['webhooks'] = True
            
        except Exception as e:
            print(f"   ❌ Webhook test failed: {e}")
        
        # 4. Test Hosted Authentication
        print("\n4. ✅ Hosted Authentication Test")
        try:
            # Test LinkedIn hosted auth
            linkedin_auth = await client.account.request_hosted_link(
                providers='linkedin',
                success_redirect_url='https://app.oneocrm.com/auth/success',
                failure_redirect_url='https://app.oneocrm.com/auth/error',
                name='OneoCRM Integration Test',
                notify_url=unipile_settings.get_webhook_url()
            )
            
            print(f"   ✅ LinkedIn hosted auth URL generated")
            print(f"   URL: {linkedin_auth.get('url', 'N/A')[:80]}...")
            
            # Test Gmail hosted auth
            gmail_auth = await client.account.request_hosted_link(
                providers='gmail',
                success_redirect_url='https://app.oneocrm.com/auth/success',
                failure_redirect_url='https://app.oneocrm.com/auth/error',
                name='OneoCRM Integration Test',
                notify_url=unipile_settings.get_webhook_url()
            )
            
            print(f"   ✅ Gmail hosted auth URL generated")
            print(f"   URL: {gmail_auth.get('url', 'N/A')[:80]}...")
            
            results['hosted_auth'] = True
            
        except Exception as e:
            print(f"   ❌ Hosted auth test failed: {e}")
        
        # Summary
        print("\n" + "=" * 50)
        print("🎯 Integration Test Results")
        print("=" * 50)
        
        for test, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {test.title().replace('_', ' '):<25} {status}")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests)*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED - UniPile Integration Ready!")
            print("\n📋 Next Steps:")
            print("   1. Deploy webhooks to production")
            print("   2. Implement user account connection APIs")
            print("   3. Test real account connections")
            print("   4. Add health monitoring")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} tests failed - Review configuration")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(test_complete_integration())
