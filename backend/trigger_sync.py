#!/usr/bin/env python
"""
Trigger message sync for testing purposes
"""
import os
import sys
import django
from django.conf import settings

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def trigger_sync():
    """Trigger message sync for the demo tenant connection"""
    from django_tenants.utils import get_tenant_model
    from django.db import connection
    from communications.models import UserChannelConnection
    from communications.message_sync import message_sync_service
    import asyncio
    
    try:
        # Switch to demo tenant
        tenant_model = get_tenant_model()
        demo_tenant = tenant_model.objects.filter(name__icontains='demo').first()
        
        if demo_tenant:
            connection.set_tenant(demo_tenant)
            print(f"🔗 Using tenant: {demo_tenant.name}")
        else:
            print("❌ No demo tenant found")
            return
        
        # Get the connection
        connections = UserChannelConnection.objects.all()
        print(f"📊 Found {connections.count()} connections")
        
        if not connections.exists():
            print("❌ No connections found")
            return
        
        conn = connections.first()
        print(f"🔄 Triggering sync for: {conn.account_name} ({conn.channel_type})")
        print(f"   UniPile ID: {conn.unipile_account_id}")
        print(f"   Status: {conn.account_status}")
        
        # Use the Celery task instead which handles async/sync properly
        from communications.tasks import sync_account_messages_task
        from asgiref.sync import async_to_sync
        
        try:
            # Use the task directly (not via Celery queue for testing)
            result = sync_account_messages_task(
                str(conn.id),
                initial_sync=True,
                days_back=30
            )
        except Exception as e:
            print(f"❌ Sync error: {e}")
            import traceback
            traceback.print_exc()
            result = {'success': False, 'error': str(e)}
        
        print(f"\n📋 Sync Result:")
        print(f"   Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"   Messages Synced: {result.get('messages_synced', 0)}")
            print(f"   Conversations Synced: {result.get('conversations_synced', 0)}")
            print(f"   Channels Created: {result.get('channels_created', 0)}")
            print(f"   Contacts Created: {result.get('contacts_created', 0)}")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Check what we have now
        from communications.models import Channel, Conversation, Message
        print(f"\n📊 After Sync:")
        print(f"   Channels: {Channel.objects.count()}")
        print(f"   Conversations: {Conversation.objects.count()}")
        print(f"   Messages: {Message.objects.count()}")
        
        return result
        
    except Exception as e:
        print(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = trigger_sync()
    sys.exit(0 if success else 1)