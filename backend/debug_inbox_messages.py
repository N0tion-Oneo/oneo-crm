#!/usr/bin/env python3
"""
Debug script to check why messages aren't appearing in the unified inbox
"""

import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import connection, schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Channel, Conversation, Message
from communications.unipile_sdk import UnipileClient
from django.contrib.auth import get_user_model

User = get_user_model()

def main():
    print("🔍 DEBUGGING UNIFIED INBOX MESSAGE VISIBILITY")
    print("=" * 60)
    
    # Check if demo tenant exists
    try:
        demo_tenant = Tenant.objects.get(schema_name='demo')
        print(f"✅ Demo tenant found: {demo_tenant.name}")
    except Tenant.DoesNotExist:
        print("❌ Demo tenant not found")
        return
    
    # Switch to demo tenant schema
    with schema_context('demo'):
        print(f"\n📊 TENANT: {demo_tenant.name}")
        print("-" * 40)
        
        # Check user accounts
        users = User.objects.all()
        print(f"👥 Total users: {users.count()}")
        for user in users:
            print(f"  - {user.username} ({user.email})")
        
        if not users.exists():
            print("❌ No users found - this might be the issue")
            return
        
        # Use first user for testing
        test_user = users.first()
        print(f"\n🧪 Testing with user: {test_user.username}")
        
        # Check user channel connections
        connections = UserChannelConnection.objects.filter(user=test_user)
        print(f"\n🔗 User Channel Connections: {connections.count()}")
        for conn in connections:
            print(f"  - {conn.channel_type}: {conn.account_name} (Status: {conn.account_status})")
            print(f"    UniPile ID: {conn.unipile_account_id}")
            print(f"    Active: {conn.is_active}")
            print(f"    Can send: {conn.can_send_messages()}")
        
        # Check channels
        channels = Channel.objects.all()
        print(f"\n📺 Channels: {channels.count()}")
        for channel in channels:
            print(f"  - {channel.name} ({channel.channel_type}): {channel.auth_status}")
        
        # Check conversations
        conversations = Conversation.objects.all()
        print(f"\n💬 Conversations: {conversations.count()}")
        for conv in conversations:
            print(f"  - {conv.subject or 'No subject'} (Messages: {conv.message_count})")
        
        # Check messages
        messages = Message.objects.all()
        print(f"\n📨 Messages: {messages.count()}")
        for msg in messages[:5]:  # Show first 5
            print(f"  - {msg.direction}: {msg.content[:50]}... (Status: {msg.status})")
        
        # Check if accounts are actually active in UniPile
        print(f"\n🌐 UNIPILE API CHECK")
        print("-" * 40)
        
        try:
            from django.conf import settings
            unipile_settings = settings.UNIPILE_SETTINGS
            
            if unipile_settings.is_configured():
                unipile_client = UnipileClient(
                    dsn=unipile_settings.dsn,
                    access_token=unipile_settings.api_key
                )
                
                # Check UniPile accounts
                accounts = unipile_client.get_accounts()
                print(f"UniPile accounts found: {len(accounts)}")
                
                for account in accounts[:5]:  # Show first 5
                    print(f"  - {account.get('provider', 'Unknown')}: {account.get('name', 'No name')} (ID: {account.get('id', 'No ID')})")
                    print(f"    Status: {account.get('status', 'Unknown')}")
                    
                    # Try to get messages for this account
                    try:
                        account_messages = unipile_client.get_messages(account_id=account.get('id'), limit=5)
                        print(f"    Messages available: {len(account_messages)}")
                    except Exception as e:
                        print(f"    ❌ Error getting messages: {e}")
            else:
                print("❌ UniPile not configured properly")
        
        except Exception as e:
            print(f"❌ Error connecting to UniPile: {e}")
            import traceback
            traceback.print_exc()
        
        # Check message sync service
        print(f"\n🔄 MESSAGE SYNC STATUS")
        print("-" * 40)
        
        # Check if message sync has been run
        from communications.message_sync import MessageSyncService
        
        active_connections = UserChannelConnection.objects.filter(
            account_status='active',
            is_active=True
        )
        
        print(f"Active connections ready for sync: {active_connections.count()}")
        
        if active_connections.exists():
            print("\n🚀 ATTEMPTING MESSAGE SYNC TEST")
            try:
                sync_service = MessageSyncService()
                
                # Test sync for first active connection
                test_connection = active_connections.first()
                print(f"Testing sync for: {test_connection.account_name}")
                
                # Run a small sync test
                result = sync_service.sync_messages_for_connection(test_connection, limit=5)
                print(f"Sync result: {result}")
                
                # Check if messages were created
                new_message_count = Message.objects.count()
                print(f"Messages after sync: {new_message_count}")
                
            except Exception as e:
                print(f"❌ Sync test failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Final summary
        print(f"\n📋 SUMMARY")
        print("-" * 40)
        print(f"Users: {User.objects.count()}")
        print(f"Channel Connections: {UserChannelConnection.objects.count()}")
        print(f"Active Connections: {UserChannelConnection.objects.filter(account_status='active', is_active=True).count()}")
        print(f"Channels: {Channel.objects.count()}")
        print(f"Conversations: {Conversation.objects.count()}")
        print(f"Messages: {Message.objects.count()}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        print("-" * 40)
        
        if not UserChannelConnection.objects.filter(account_status='active').exists():
            print("❌ No active connections - accounts need to be connected properly")
        
        if Message.objects.count() == 0:
            print("❌ No messages in database - need to run message sync")
            print("  Try: python manage.py sync_unipile_messages")
        
        if Conversation.objects.count() == 0:
            print("❌ No conversations - messages need to be grouped into conversations")

if __name__ == '__main__':
    main()