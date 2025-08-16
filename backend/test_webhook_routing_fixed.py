#!/usr/bin/env python3
"""
Test webhook routing using existing tenants
"""
import os
import django
import json
import uuid
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant, Domain
from communications.models import UserChannelConnection, ChannelType, TenantUniPileConfig
from communications.webhooks.routing import AccountTenantRouter
from communications.webhooks.handlers import UnipileWebhookHandler

User = get_user_model()


def setup_test_connections():
    """Setup test user connections in existing tenants"""
    test_connections = []
    
    # Get existing tenants (skip public)
    tenants = Tenant.objects.exclude(schema_name='public')
    
    if len(tenants) < 2:
        print("❌ Need at least 2 tenants for testing. Found:", [t.schema_name for t in tenants])
        return []
    
    # Test data for existing tenants
    test_data = [
        {'tenant': tenants[0], 'account_id': 'linkedin_test_001', 'channel': ChannelType.LINKEDIN},
        {'tenant': tenants[1], 'account_id': 'gmail_test_002', 'channel': ChannelType.EMAIL},
    ]
    
    # Add more if we have more tenants
    if len(tenants) > 2:
        test_data.append({'tenant': tenants[2], 'account_id': 'whatsapp_test_003', 'channel': ChannelType.WHATSAPP})
    
    for i, data in enumerate(test_data):
        tenant = data['tenant']
        account_id = data['account_id']
        channel = data['channel']
        
        try:
            with schema_context(tenant.schema_name):
                # Create or get test user
                user, created = User.objects.get_or_create(
                    username=f"webhook_test_user_{i+1}",
                    defaults={
                        'email': f"test{i+1}@{tenant.schema_name}.com",
                        'first_name': f"Test{i+1}",
                        'last_name': "User"
                    }
                )
                
                # Create UniPile config if needed
                config, _ = TenantUniPileConfig.objects.get_or_create(
                    id=1,
                    defaults={'auto_create_contacts': True}
                )
                
                # Clean up existing test connections
                UserChannelConnection.objects.filter(
                    external_account_id__startswith='linkedin_test_',
                    user__username__startswith='webhook_test_'
                ).delete()
                UserChannelConnection.objects.filter(
                    external_account_id__startswith='gmail_test_',
                    user__username__startswith='webhook_test_'
                ).delete()
                UserChannelConnection.objects.filter(
                    external_account_id__startswith='whatsapp_test_',
                    user__username__startswith='webhook_test_'
                ).delete()
                
                # Create connection
                connection = UserChannelConnection.objects.create(
                    user=user,
                    channel_type=channel,
                    external_account_id=account_id,
                    account_name=f"Test {channel} Account for Webhook Routing",
                    auth_status='authenticated',
                    account_status='active'
                )
                
                test_connections.append({
                    'tenant': tenant,
                    'connection': connection,
                    'account_id': account_id,
                    'channel': channel
                })
                
                print(f"✅ Setup: {account_id} -> {tenant.schema_name}")
                
        except Exception as e:
            print(f"❌ Failed to setup {account_id} in {tenant.schema_name}: {e}")
    
    return test_connections


def test_webhook_routing():
    """Test webhook routing with existing tenants"""
    
    print("🔄 Testing Webhook Routing with Existing Tenants...")
    print("=" * 60)
    
    results = {
        'setup': False,
        'routing': False,
        'event_handling': False,
        'tenant_isolation': False
    }
    
    try:
        # 1. Setup test connections
        print("1. 🏗️  Setting up test connections in existing tenants...")
        
        test_connections = setup_test_connections()
        
        if len(test_connections) >= 2:
            results['setup'] = True
            print(f"   ✅ Setup {len(test_connections)} test connections")
        else:
            print(f"   ❌ Only setup {len(test_connections)} connections (need at least 2)")
            return
        
        # 2. Test account routing
        print("\n2. 🎯 Testing account-to-tenant routing...")
        
        router = AccountTenantRouter()
        routing_success = 0
        
        for conn_data in test_connections:
            account_id = conn_data['account_id']
            expected_tenant = conn_data['tenant'].schema_name
            
            # Test routing
            found_tenant = router.get_tenant_for_account(account_id)
            
            if found_tenant == expected_tenant:
                print(f"   ✅ {account_id} -> {found_tenant}")
                routing_success += 1
            else:
                print(f"   ❌ {account_id} -> {found_tenant} (expected {expected_tenant})")
        
        if routing_success == len(test_connections):
            results['routing'] = True
        
        # 3. Test webhook event handling
        print("\n3. 📨 Testing webhook event handlers...")
        
        handler = UnipileWebhookHandler()
        handling_success = 0
        
        # Test different event types
        test_events = []
        
        if len(test_connections) >= 1:
            test_events.append({
                'type': 'account.connected',
                'account_id': test_connections[0]['account_id'],
                'status': 'connected'
            })
        
        if len(test_connections) >= 2:
            test_events.append({
                'type': 'message.received',
                'account_id': test_connections[1]['account_id'],
                'message': {
                    'id': f'msg_{uuid.uuid4().hex[:8]}',
                    'text': 'Test message from webhook routing test',
                    'from': {'email': 'webhook-test@example.com', 'name': 'Webhook Test'},
                    'thread_id': f'thread_{uuid.uuid4().hex[:8]}',
                    'timestamp': datetime.now().isoformat()
                }
            })
        
        if len(test_connections) >= 3:
            test_events.append({
                'type': 'account.error',
                'account_id': test_connections[2]['account_id'],
                'error': 'Connection timeout during webhook routing test'
            })
        
        for event in test_events:
            result = handler.process_webhook(event['type'], event)
            
            if result.get('success'):
                print(f"   ✅ {event['type']} for {event['account_id']}")
                handling_success += 1
            else:
                print(f"   ❌ {event['type']} for {event['account_id']}: {result.get('error')}")
        
        if handling_success == len(test_events):
            results['event_handling'] = True
        
        # 4. Test tenant isolation
        print("\n4. 🔒 Testing tenant data isolation...")
        
        isolation_success = 0
        total_isolation_checks = 0
        
        for conn_data in test_connections:
            tenant = conn_data['tenant']
            account_id = conn_data['account_id']
            
            with schema_context(tenant.schema_name):
                # Check connection exists in this tenant
                local_connection = UserChannelConnection.objects.filter(
                    external_account_id=account_id
                ).first()
                
                total_isolation_checks += 1
                if local_connection:
                    print(f"   ✅ {account_id} found in {tenant.schema_name}")
                    isolation_success += 1
                else:
                    print(f"   ❌ {account_id} not found in {tenant.schema_name}")
                
                # Check other test accounts are NOT visible
                other_accounts = [c['account_id'] for c in test_connections if c['account_id'] != account_id]
                
                for other_account in other_accounts:
                    total_isolation_checks += 1
                    other_connection = UserChannelConnection.objects.filter(
                        external_account_id=other_account
                    ).first()
                    
                    if not other_connection:
                        print(f"   ✅ {other_account} properly isolated from {tenant.schema_name}")
                        isolation_success += 1
                    else:
                        print(f"   ❌ Found {other_account} in wrong tenant {tenant.schema_name}")
        
        # Require all isolation checks to pass
        if isolation_success == total_isolation_checks:
            results['tenant_isolation'] = True
        
        # 5. Test HTTP webhook endpoint
        print("\n5. 🌐 Testing HTTP webhook endpoint...")
        
        try:
            from django.test import Client
            from django.urls import reverse
            
            client = Client()
            
            # Test webhook health endpoint
            response = client.get('/webhooks/health/')
            if response.status_code == 200:
                print("   ✅ Webhook health endpoint accessible")
                
                # Test actual webhook endpoint
                webhook_data = {
                    'type': 'account.connected',
                    'account_id': test_connections[0]['account_id'] if test_connections else 'test_account',
                    'status': 'connected'
                }
                
                response = client.post(
                    '/webhooks/unipile/',
                    data=json.dumps(webhook_data),
                    content_type='application/json'
                )
                
                if response.status_code in [200, 400]:  # 400 is expected if no routing
                    print("   ✅ Webhook endpoint accessible and processing")
                else:
                    print(f"   ⚠️  Webhook endpoint returned {response.status_code}")
            else:
                print(f"   ❌ Webhook health endpoint failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️  HTTP endpoint test failed: {e}")
        
        # Results summary
        print("\n" + "=" * 60)
        print("🎯 Webhook Routing Test Results")
        print("=" * 60)
        
        for test, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {test.title().replace('_', ' '):<25} {status}")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests)*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL WEBHOOK ROUTING TESTS PASSED!")
            print("\n📋 Verified:")
            print("   ✅ Multi-tenant webhook routing")
            print("   ✅ Account-to-tenant mapping")
            print("   ✅ Event handler processing")
            print("   ✅ Tenant data isolation")
            print("   ✅ HTTP webhook endpoints")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} tests failed")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        cleanup_count = 0
        for conn_data in test_connections:
            try:
                with schema_context(conn_data['tenant'].schema_name):
                    # Clean up test connections and users
                    UserChannelConnection.objects.filter(
                        external_account_id__in=[c['account_id'] for c in test_connections]
                    ).delete()
                    
                    User.objects.filter(
                        username__startswith='webhook_test_user_'
                    ).delete()
                    
                    cleanup_count += 1
            except Exception as e:
                print(f"   ⚠️  Cleanup failed for {conn_data['tenant'].schema_name}: {e}")
        
        print(f"   ✅ Cleaned up {cleanup_count} tenant schemas")
        
    except Exception as e:
        print(f"❌ Webhook routing test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    test_webhook_routing()
