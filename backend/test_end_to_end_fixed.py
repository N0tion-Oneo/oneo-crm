#!/usr/bin/env python3
"""
Fixed End-to-End Webhook Test (sync version)
"""
import os
import django
import json
import uuid
import asyncio
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from django.test import Client
from tenants.models import Tenant
from communications.models import UserChannelConnection, ChannelType
from communications.unipile_sdk import unipile_service
from oneo_crm.settings import unipile_settings

User = get_user_model()


def test_sync_components():
    """Test synchronous components"""
    
    print("🚀 Fixed End-to-End Test (Sync Components)")
    print("=" * 50)
    
    results = {
        'configuration': False,
        'account_setup': False,
        'webhook_delivery': False,
        'tenant_isolation': False
    }
    
    test_data = {}
    
    try:
        # 1. Configuration
        print("1. 🔧 Configuration...")
        if unipile_settings.is_configured():
            print(f"   ✅ Configured: {unipile_settings.get_webhook_url()}")
            results['configuration'] = True
        
        # 2. Account Setup (sync)
        print("\n2. 🏗️  Account Setup...")
        
        tenant = Tenant.objects.exclude(schema_name='public').first()
        if tenant:
            test_account_id = f"e2e_test_{uuid.uuid4().hex[:8]}"
            
            with schema_context(tenant.schema_name):
                test_user = User.objects.create_user(
                    username=f"e2e_user_{uuid.uuid4().hex[:6]}",
                    email=f"e2e_{uuid.uuid4().hex[:6]}@{tenant.schema_name}.test"
                )
                
                connection = UserChannelConnection.objects.create(
                    user=test_user,
                    channel_type=ChannelType.LINKEDIN,
                    external_account_id=test_account_id,
                    account_name="E2E Test Account",
                    auth_status='authenticated',
                    account_status='active'
                )
                
                test_data.update({
                    'tenant': tenant,
                    'user': test_user,
                    'connection': connection,
                    'account_id': test_account_id
                })
                
                print(f"   ✅ Created: {test_account_id} in {tenant.schema_name}")
                results['account_setup'] = True
        
        # 3. Webhook Delivery
        print("\n3. 📨 Webhook Delivery...")
        
        if 'account_id' in test_data:
            client = Client()
            
            webhook_event = {
                'type': 'account.connected',
                'account_id': test_data['account_id'],
                'status': 'connected'
            }
            
            response = client.post(
                '/webhooks/unipile/',
                data=json.dumps(webhook_event),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success'):
                    print(f"   ✅ Webhook processed successfully")
                    results['webhook_delivery'] = True
                else:
                    print(f"   ❌ Processing failed: {response_data.get('error')}")
            else:
                print(f"   ❌ HTTP {response.status_code}")
        
        # 4. Tenant Isolation
        print("\n4. 🔒 Tenant Isolation...")
        
        if 'tenant' in test_data:
            with schema_context(test_data['tenant'].schema_name):
                exists = UserChannelConnection.objects.filter(
                    external_account_id=test_data['account_id']
                ).exists()
                
                if exists:
                    print(f"   ✅ Account found in correct tenant")
                    results['tenant_isolation'] = True
                else:
                    print(f"   ❌ Account not found in tenant")
        
        # Results
        print(f"\n" + "=" * 50)
        print("🎯 Results")
        print("=" * 50)
        
        for test, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {test.title().replace('_', ' '):<20} {status}")
        
        passed = sum(results.values())
        total = len(results)
        print(f"\nSync Tests: {passed}/{total} passed ({(passed/total)*100:.1f}%)")
        
        if passed >= 3:
            print("\n🎉 Core functionality working!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if 'connection' in test_data:
            try:
                with schema_context(test_data['tenant'].schema_name):
                    test_data['connection'].delete()
                    test_data['user'].delete()
                print("   ✅ Cleaned up test data")
            except Exception as e:
                print(f"   ⚠️  Cleanup failed: {e}")


async def test_async_components():
    """Test async components separately"""
    
    print("\n🔄 Testing Async Components...")
    print("=" * 30)
    
    try:
        # Test UniPile API calls
        client = unipile_service.get_client()
        
        # 1. Test webhook registration
        webhook_result = await client.webhooks.create_messaging_webhook(
            url=unipile_settings.get_webhook_url(),
            name="E2E Test Webhook"
        )
        
        if webhook_result.get('webhook_id'):
            print("   ✅ Webhook registration working")
        
        # 2. Test hosted auth
        hosted_auth = await client.account.request_hosted_link(
            providers='linkedin',
            success_redirect_url='https://app.oneocrm.com/auth/success',
            name='E2E Test Account'
        )
        
        if hosted_auth.get('url'):
            print("   ✅ Hosted auth URL generation working")
            print(f"   URL: {hosted_auth['url'][:50]}...")
        
    except Exception as e:
        print(f"   ❌ Async test failed: {e}")


def main():
    """Run both sync and async tests"""
    test_sync_components()
    asyncio.run(test_async_components())


if __name__ == "__main__":
    main()
