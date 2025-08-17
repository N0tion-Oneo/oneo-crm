#!/usr/bin/env python
"""
Diagnose inbox message state - check what data we have
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

def diagnose_inbox():
    """Check the current state of inbox data"""
    print("🔍 Diagnosing Inbox Message State")
    print("=" * 50)
    
    try:
        # Switch to demo tenant
        from django_tenants.utils import get_tenant_model
        from django.db import connection
        
        tenant_model = get_tenant_model()
        demo_tenant = tenant_model.objects.filter(name__icontains='demo').first()
        
        if demo_tenant:
            connection.set_tenant(demo_tenant)
            print(f"🔗 Using tenant: {demo_tenant.name}")
        else:
            print("❌ No demo tenant found")
            return
        
        # Import models after setting tenant
        from communications.models import UserChannelConnection, Channel, Conversation, Message
        
        # Check user connections
        connections = UserChannelConnection.objects.all()
        print(f"\n📊 UserChannelConnection Records: {connections.count()}")
        
        for conn in connections:
            print(f"   - {conn.account_name} ({conn.channel_type})")
            print(f"     UniPile ID: {conn.unipile_account_id}")
            print(f"     Status: {conn.account_status}")
            print(f"     Last Sync: {conn.last_sync_at}")
            print(f"     Active: {conn.is_active}")
        
        # Check channels
        channels = Channel.objects.all()
        print(f"\n📊 Channel Records: {channels.count()}")
        
        for channel in channels:
            print(f"   - {channel.name} ({channel.channel_type})")
            print(f"     UniPile ID: {channel.unipile_account_id}")
            print(f"     Active: {channel.is_active}")
            print(f"     Message Count: {channel.message_count}")
        
        # Check conversations
        conversations = Conversation.objects.all()
        print(f"\n📊 Conversation Records: {conversations.count()}")
        
        for conv in conversations[:5]:  # Show first 5
            print(f"   - {conv.subject or 'No Subject'}")
            print(f"     Channel: {conv.channel.name}")
            print(f"     Messages: {conv.message_count}")
            print(f"     Last Message: {conv.last_message_at}")
        
        # Check messages
        messages = Message.objects.all()
        print(f"\n📊 Message Records: {messages.count()}")
        
        if messages.exists():
            print("\n📝 Recent Messages:")
            for msg in messages.order_by('-created_at')[:5]:
                print(f"   - {msg.direction}: {msg.content[:50]}...")
                print(f"     Channel: {msg.channel.name}")
                print(f"     Created: {msg.created_at}")
                print(f"     Contact: {msg.contact_email}")
        else:
            print("   ❌ No messages found in database")
        
        # Summary and recommendations
        print(f"\n📋 Summary:")
        print(f"   Active Connections: {connections.filter(is_active=True, account_status='active').count()}")
        print(f"   Synced Channels: {channels.count()}")
        print(f"   Total Conversations: {conversations.count()}")
        print(f"   Total Messages: {messages.count()}")
        
        if messages.count() == 0:
            print(f"\n🔧 Recommendations:")
            print(f"   1. Trigger initial message sync:")
            print(f"      POST /api/v1/communications/sync/messages/")
            print(f"   2. Check connection status:")
            print(f"      GET /api/v1/communications/sync/status/")
            print(f"   3. Verify UniPile credentials are configured")
            
            if connections.exists():
                conn = connections.first()
                print(f"   4. Try syncing specific connection:")
                print(f"      POST /api/v1/communications/sync/messages/{conn.id}/")
        else:
            print(f"\n✅ Messages found! Use local inbox endpoint:")
            print(f"   GET /api/v1/communications/local-inbox/")
        
        return True
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = diagnose_inbox()
    sys.exit(0 if success else 1)