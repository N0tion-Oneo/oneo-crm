#!/usr/bin/env python3
"""
Test webhook routing to tenants and users
"""
import os
import django
import asyncio
import json
import uuid
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, tenant_context
from django_tenants.test.cases import TenantTestCase
from tenants.models import Tenant, Domain
from communications.models import UserChannelConnection, ChannelType, TenantUniPileConfig
from communications.webhooks.routing import AccountTenantRouter
from communications.webhooks.handlers import UnipileWebhookHandler

User = get_user_model()


def create_test_tenant(schema_name, domain_name):
    """Helper to create test tenant"""
    try:
        # Create tenant
        tenant = Tenant.objects.create(
            name=f"Test Tenant {schema_name}",
            schema_name=schema_name,
            description=f"Test tenant for webhook routing: {schema_name}"
        )
        
        # Create domain
        domain = Domain.objects.create(
            domain=domain_name,
            tenant=tenant,
            is_primary=True
        )
        
        print(f"✅ Created tenant: {schema_name} -> {domain_name}")
        return tenant, domain
        
    except Exception as e:
        print(f"❌ Failed to create tenant {schema_name}: {e}")
        return None, None


def create_test_user_connection(tenant, user_id, account_id, channel_type):
    """Helper to create test user connection within tenant"""
    try:
        with schema_context(tenant.schema_name):
            # Create user
            user, created = User.objects.get_or_create(
                username=f"testuser_{user_id}",
                defaults={
                    'email': f"testuser{user_id}@{tenant.schema_name}.com",
                    'first_name': f"Test{user_id}",
                    'last_name': "User"
                }
            )
            
            # Create UniPile config for tenant
            config, _ = TenantUniPileConfig.objects.get_or_create(
                id=1,
                defaults={
                    'auto_create_contacts': True,
                    'sync_historical_days': 30
                }
            )
            
            # Create channel connection
            connection = UserChannelConnection.objects.create(
                user=user,
                channel_type=channel_type,
                external_account_id=account_id,
                account_name=f"Test {channel_type} Account",
                auth_status='authenticated',
                account_status='active'
            )
            
            print(f"✅ Created connection: {account_id} -> {tenant.schema_name} ({user.username})")
            return user, connection
            
    except Exception as e:
        print(f"❌ Failed to create connection for {account_id}: {e}")
        return None, None


def test_webhook_routing():
    """Test webhook routing to correct tenants"""
    
    print("🔄 Testing Webhook Routing System...")
    print("=" * 60)
    
    # Test data
    test_accounts = [
        {'tenant': 'demo', 'domain': 'demo.test.local', 'account_id': 'linkedin_demo_001', 'channel': ChannelType.LINKEDIN},
        {'tenant': 'testorg', 'domain': 'testorg.test.local', 'account_id': 'gmail_testorg_001', 'channel': ChannelType.EMAIL},
        {'tenant': 'company', 'domain': 'company.test.local', 'account_id': 'whatsapp_company_001', 'channel': ChannelType.WHATSAPP},
    ]
    
    results = {
        'setup': False,
        'routing': False,
        'event_handling': False,
        'tenant_isolation': False
    }
    
    try:
        # 1. Setup test tenants and connections
        print("1. 🏗️  Setting up test tenants and connections...")
        
        created_tenants = []
        created_connections = []
        
        for i, account_data in enumerate(test_accounts):
            # Create tenant
            tenant, domain = create_test_tenant(
                account_data['tenant'], 
                account_data['domain']
            )
            
            if tenant:
                created_tenants.append(tenant)
                
                # Create user connection
                user, connection = create_test_user_connection(
                    tenant,
                    i + 1,
                    account_data['account_id'],
                    account_data['channel']
                )
                
                if connection:
                    created_connections.append((tenant, connection))
        
        print(f"   Created {len(created_tenants)} tenants and {len(created_connections)} connections")
        
        if len(created_connections) == len(test_accounts):
            results['setup'] = True
        
        # 2. Test account routing
        print("\n2. 🎯 Testing account-to-tenant routing...")
        
        router = AccountTenantRouter()
        routing_success = 0
        
        for account_data in test_accounts:
            account_id = account_data['account_id']
            expected_tenant = account_data['tenant']
            
            # Test routing
            found_tenant = router.get_tenant_for_account(account_id)
            
            if found_tenant == expected_tenant:
                print(f"   ✅ {account_id} -> {found_tenant}")
                routing_success += 1
            else:
                print(f"   ❌ {account_id} -> {found_tenant} (expected {expected_tenant})")
        
        if routing_success == len(test_accounts):
            results['routing'] = True
        
        # 3. Test webhook event handling
        print("\n3. 📨 Testing webhook event handlers...")
        
        handler = UnipileWebhookHandler()
        handling_success = 0
        
        # Test different event types
        test_events = [
            {
                'type': 'account.connected',
                'account_id': 'linkedin_demo_001',
                'status': 'connected'
            },
            {
                'type': 'message.received', 
                'account_id': 'gmail_testorg_001',
                'message': {
                    'id': 'msg_12345',
                    'text': 'Test message from webhook routing',
                    'from': {'email': 'sender@example.com', 'name': 'Test Sender'},
                    'timestamp': datetime.now().isoformat()
                }
            },
            {
                'type': 'account.error',
                'account_id': 'whatsapp_company_001', 
                'error': 'Connection timeout during routing test'
            }
        ]
        
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
        
        # Test that connections are isolated per tenant
        for tenant, connection in created_connections:
            with schema_context(tenant.schema_name):
                # Check connection exists in this tenant
                local_connection = UserChannelConnection.objects.filter(
                    external_account_id=connection.external_account_id
                ).first()
                
                if local_connection:
                    print(f"   ✅ {connection.external_account_id} found in {tenant.schema_name}")
                    isolation_success += 1
                else:
                    print(f"   ❌ {connection.external_account_id} not found in {tenant.schema_name}")
                
                # Check other accounts are NOT visible
                other_accounts = [acc['account_id'] for acc in test_accounts 
                                if acc['account_id'] != connection.external_account_id]
                
                for other_account in other_accounts:
                    other_connection = UserChannelConnection.objects.filter(
                        external_account_id=other_account
                    ).first()
                    
                    if not other_connection:
                        isolation_success += 0.5  # Partial point for proper isolation
                    else:
                        print(f"   ❌ Found {other_account} in wrong tenant {tenant.schema_name}")
        
        # Require high isolation score
        if isolation_success >= len(created_connections) * 1.5:  # Account for isolation checks
            results['tenant_isolation'] = True
        
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
        else:
            print(f"\n⚠️  {total_tests - passed_tests} tests failed")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        for tenant in created_tenants:
            try:
                tenant.delete()
                print(f"   Deleted tenant: {tenant.schema_name}")
            except Exception as e:
                print(f"   Failed to delete tenant {tenant.schema_name}: {e}")
        
    except Exception as e:
        print(f"❌ Webhook routing test failed: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    test_webhook_routing()
