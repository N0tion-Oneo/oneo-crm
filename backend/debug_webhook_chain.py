#!/usr/bin/env python3
"""
Debug the entire webhook chain to identify where real incoming messages are getting lost
"""
import requests
import json
import time
from datetime import datetime
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def check_webhook_endpoints():
    """Check if webhook endpoints are accessible"""
    print("🔍 CHECKING WEBHOOK ENDPOINTS")
    print("=" * 50)
    
    endpoints_to_check = [
        "http://localhost:8000/webhooks/health/",
        "http://localhost:8000/webhooks/unipile/",
        "http://localhost:8000/webhooks/whatsapp/",
        "http://oneotalent.localhost:8000/webhooks/unipile/",
    ]
    
    for endpoint in endpoints_to_check:
        try:
            if "health" in endpoint:
                response = requests.get(endpoint, timeout=5)
                status = "✅ ACCESSIBLE" if response.status_code == 200 else f"⚠️  Status {response.status_code}"
            else:
                # Test POST with minimal payload
                response = requests.post(endpoint, json={"test": "ping"}, timeout=5)
                status = "✅ ACCESSIBLE" if response.status_code in [200, 400] else f"⚠️  Status {response.status_code}"
                
            print(f"  {endpoint}: {status}")
            if response.status_code != 200 and "health" in endpoint:
                print(f"    Response: {response.text[:100]}")
                
        except requests.RequestException as e:
            print(f"  {endpoint}: ❌ ERROR - {e}")

def check_unipile_account_connections():
    """Check if there are active UniPile account connections"""
    print("\n📱 CHECKING UNIPILE ACCOUNT CONNECTIONS")
    print("=" * 50)
    
    from django_tenants.utils import tenant_context
    from tenants.models import Tenant
    from communications.models import UserChannelConnection
    
    tenant = Tenant.objects.get(schema_name='oneotalent')
    with tenant_context(tenant):
        connections = UserChannelConnection.objects.filter(is_active=True)
        print(f"✅ Active connections found: {connections.count()}")
        
        whatsapp_connections = connections.filter(channel_type='whatsapp')
        print(f"📱 WhatsApp connections: {whatsapp_connections.count()}")
        
        for conn in whatsapp_connections[:3]:  # Show first 3
            print(f"  • Account: {conn.account_name}")
            print(f"    UniPile Account ID: {conn.unipile_account_id}")
            print(f"    Status: {conn.account_status}")
            print(f"    Auth Status: {conn.auth_status}")
            print(f"    Last Sync: {conn.last_sync_at}")
            print()

def test_webhook_dispatcher():
    """Test the webhook dispatcher directly"""
    print("🔧 TESTING WEBHOOK DISPATCHER")  
    print("=" * 50)
    
    from communications.webhooks.dispatcher import webhook_dispatcher
    
    # Test health check
    health = webhook_dispatcher.health_check()
    print("✅ Dispatcher Health:", json.dumps(health, indent=2))
    
    # Test supported events
    supported = webhook_dispatcher.get_supported_events()
    print("\n📋 Supported Events:")
    for provider, events in supported.items():
        print(f"  {provider}: {events}")

def test_account_routing():
    """Test the account routing system"""  
    print("\n🎯 TESTING ACCOUNT ROUTING")
    print("=" * 50)
    
    from communications.webhooks.routing import account_router
    from django_tenants.utils import tenant_context
    from tenants.models import Tenant
    from communications.models import UserChannelConnection
    
    # Get a real WhatsApp account ID from the database
    tenant = Tenant.objects.get(schema_name='oneotalent')
    with tenant_context(tenant):
        whatsapp_conn = UserChannelConnection.objects.filter(
            channel_type='whatsapp',
            is_active=True
        ).first()
        
        if whatsapp_conn:
            account_id = whatsapp_conn.unipile_account_id
            print(f"🔍 Testing with real account ID: {account_id}")
            
            # Test user connection lookup
            connection = account_router.get_user_connection(account_id)
            if connection:
                print(f"✅ Found connection: {connection.account_name}")
                print(f"  User: {connection.user.email}")
                print(f"  Channel Type: {connection.channel_type}")
                print(f"  Status: {connection.account_status}")
            else:
                print("❌ No connection found for account ID")
        else:
            print("⚠️  No active WhatsApp connections found")

def simulate_real_unipile_webhook():
    """Simulate what a real UniPile webhook might look like"""
    print("\n📡 SIMULATING REAL UNIPILE WEBHOOK")
    print("=" * 50)
    
    from django_tenants.utils import tenant_context
    from tenants.models import Tenant
    from communications.models import UserChannelConnection
    
    # Get a real account ID
    tenant = Tenant.objects.get(schema_name='oneotalent')
    with tenant_context(tenant):
        whatsapp_conn = UserChannelConnection.objects.filter(
            channel_type='whatsapp',
            is_active=True
        ).first()
        
        if not whatsapp_conn:
            print("⚠️  No WhatsApp connection found, using test account ID")
            real_account_id = "mp9Gis3IRtuh9V5oSxZdSA"
        else:
            real_account_id = whatsapp_conn.unipile_account_id
    
    # Create realistic webhook payloads based on UniPile documentation
    webhook_payloads = [
        {
            "name": "Standard WhatsApp message received",
            "payload": {
                "type": "message",
                "event": "message.received",
                "account_id": real_account_id,
                "message": {
                    "id": f"debug_msg_{int(time.time())}",
                    "chat_id": f"debug_chat_{int(time.time())}",
                    "from": "sender123",
                    "text": "Hello! This is a real webhook test message 📱",
                    "timestamp": int(time.time()),
                    "type": "text"
                },
                "timestamp": int(time.time())
            }
        },
        {
            "name": "WhatsApp message with nested data",
            "payload": {
                "event": "message_received",
                "account_id": real_account_id,
                "data": {
                    "message": {
                        "id": f"debug_nested_{int(time.time())}",
                        "chat_id": f"debug_chat_nested_{int(time.time())}",
                        "from": "sender456",
                        "text": "Nested webhook format test message 🔧",
                        "timestamp": int(time.time())
                    }
                },
                "timestamp": int(time.time())
            }
        }
    ]
    
    for test_case in webhook_payloads:
        print(f"\n🧪 Testing: {test_case['name']}")
        
        webhook_url = "http://localhost:8000/webhooks/unipile/"
        
        try:
            response = requests.post(
                webhook_url,
                json=test_case['payload'],
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Success: {result.get('success', False)}")
                if result.get('result'):
                    webhook_result = result['result']
                    print(f"  📝 Message ID: {webhook_result.get('message_id', 'N/A')}")
                    print(f"  💬 Conversation: {webhook_result.get('conversation_name', 'N/A')}")
                    print(f"  🔄 Approach: {webhook_result.get('approach', 'N/A')}")
            else:
                print(f"  ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"  💥 Exception: {e}")
        
        time.sleep(1)  # Brief pause between tests

def check_django_logs():
    """Check if Django logging is properly configured"""
    print("\n📝 CHECKING DJANGO LOGGING CONFIGURATION")
    print("=" * 50)
    
    import logging
    
    # Test different loggers that webhooks use
    loggers_to_test = [
        'communications.webhooks.views',
        'communications.webhooks.dispatcher', 
        'communications.webhooks.handlers.whatsapp',
        'django.request'
    ]
    
    for logger_name in loggers_to_test:
        logger = logging.getLogger(logger_name)
        print(f"  Logger '{logger_name}':")
        print(f"    Level: {logging.getLevelName(logger.level)}")
        print(f"    Handlers: {len(logger.handlers)}")
        print(f"    Effective Level: {logging.getLevelName(logger.getEffectiveLevel())}")
        
        # Test log message
        logger.info(f"Test log message from debug script")
        print()

def check_unipile_webhook_url():
    """Check what webhook URL should be configured in UniPile"""
    print("🌐 WEBHOOK URL CONFIGURATION")
    print("=" * 50)
    
    possible_webhook_urls = [
        "http://localhost:8000/webhooks/unipile/",
        "https://localhost:8000/webhooks/unipile/",  
        "http://oneotalent.localhost:8000/webhooks/unipile/",
        "https://yourdomain.com/webhooks/unipile/",  # Production
        "http://yourserver.ngrok.io/webhooks/unipile/",  # Ngrok tunnel
    ]
    
    print("📋 Possible webhook URLs to configure in UniPile:")
    for url in possible_webhook_urls:
        print(f"  • {url}")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("  • UniPile can only send webhooks to publicly accessible URLs")
    print("  • localhost URLs will NOT work unless you're testing locally") 
    print("  • You need either:")
    print("    - A public domain pointing to your server")
    print("    - A tunneling service like ngrok")
    print("    - Port forwarding if testing locally")

def main():
    """Run complete webhook chain debugging"""
    print("🚀 WEBHOOK CHAIN DEBUGGING")
    print("=" * 70)
    print(f"Timestamp: {datetime.now()}")
    print("=" * 70)
    
    try:
        # 1. Check endpoints
        check_webhook_endpoints()
        
        # 2. Check UniPile connections  
        check_unipile_account_connections()
        
        # 3. Test dispatcher
        test_webhook_dispatcher()
        
        # 4. Test routing
        test_account_routing()
        
        # 5. Check logging
        check_django_logs()
        
        # 6. Simulate webhooks
        simulate_real_unipile_webhook()
        
        # 7. Show webhook URL info
        check_unipile_webhook_url()
        
    except Exception as e:
        print(f"\n💥 DEBUGGING ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("🔍 DEBUGGING COMPLETE")
    print("=" * 70)
    print("📊 SUMMARY:")
    print("✅ If webhook endpoints are accessible")
    print("✅ If UniPile connections exist") 
    print("✅ If dispatcher is working")
    print("✅ If routing finds connections")
    print("✅ If simulated webhooks work")
    print()
    print("🎯 NEXT STEPS:")
    print("1. Configure proper webhook URL in UniPile dashboard")
    print("2. Ensure webhooks can reach your server (public URL/ngrok)")
    print("3. Check UniPile account has webhook notifications enabled") 
    print("4. Test with real WhatsApp message to verify end-to-end flow")

if __name__ == "__main__":
    main()