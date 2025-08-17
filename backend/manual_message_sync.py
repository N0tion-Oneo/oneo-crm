#!/usr/bin/env python3
"""
Manual message sync script to test UniPile integration
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
    print("🔄 MANUAL MESSAGE SYNC TEST")
    print("=" * 50)
    
    # Check if oneotalent tenant exists
    try:
        oneotalent_tenant = Tenant.objects.get(schema_name='oneotalent')
        print(f"✅ Oneotalent tenant found: {oneotalent_tenant.name}")
    except Tenant.DoesNotExist:
        print("❌ Oneotalent tenant not found")
        # Show available tenants
        available_tenants = Tenant.objects.all()
        print(f"Available tenants: {[t.schema_name for t in available_tenants]}")
        return
    
    # Switch to oneotalent tenant schema
    with schema_context('oneotalent'):
        print(f"\n📊 CHECKING ACTIVE CONNECTIONS")
        print("-" * 40)
        
        # Check active connections
        active_connections = UserChannelConnection.objects.filter(
            account_status='active',
            is_active=True
        )
        
        print(f"Active connections: {active_connections.count()}")
        
        if not active_connections.exists():
            print("❌ No active connections found")
            
            # Show all connections for debugging
            all_connections = UserChannelConnection.objects.all()
            print(f"\nAll connections: {all_connections.count()}")
            for conn in all_connections:
                print(f"  - {conn.account_name} ({conn.channel_type}): {conn.account_status}")
            return
        
        # Show active connections
        for conn in active_connections:
            print(f"  - {conn.account_name} ({conn.channel_type})")
            print(f"    UniPile ID: {conn.unipile_account_id}")
            print(f"    Status: {conn.account_status}")
            print(f"    User: {conn.user.username}")
        
        print(f"\n🌐 TESTING UNIPILE API ACCESS")
        print("-" * 40)
        
        try:
            unipile_settings = settings.UNIPILE_SETTINGS
            
            if not unipile_settings.is_configured():
                print("❌ UniPile not configured properly")
                print(f"DSN: {unipile_settings.dsn}")
                print(f"API Key: {'***' if unipile_settings.api_key else 'Not set'}")
                return
            
            print("✅ UniPile configuration found")
            print(f"DSN: {unipile_settings.dsn}")
            
            # Initialize client
            unipile_client = UnipileClient(
                dsn=unipile_settings.dsn,
                access_token=unipile_settings.api_key
            )
            print("✅ UniPile client initialized")
            
            # Test API connection by checking accounts
            print("\n📱 TESTING API CONNECTION")
            print("-" * 40)
            
            try:
                # Use the SDK's get accounts method
                accounts_response = unipile_client.account.get_accounts()
                print(f"✅ API connection successful")
                print(f"Accounts found: {len(accounts_response)}")
                
                # Show account details
                for account in accounts_response[:5]:  # Show first 5
                    print(f"  - {account.get('provider', 'Unknown')}: {account.get('name', 'No name')}")
                    print(f"    ID: {account.get('id', 'No ID')}")
                    print(f"    Status: {account.get('status', 'Unknown')}")
                    
                    # Check if this account matches any local connection
                    local_connections = UserChannelConnection.objects.filter(
                        unipile_account_id=account.get('id', '')
                    )
                    if local_connections.exists():
                        local_conn = local_connections.first()
                        print(f"    ✅ Linked to local user: {local_conn.user.username}")
                    else:
                        print(f"    ⚠️  No local connection found")
                
                print(f"\n📨 TESTING MESSAGE RETRIEVAL")
                print("-" * 40)
                
                # Test message retrieval for each active connection
                for conn in active_connections:
                    print(f"\nTesting messages for: {conn.account_name}")
                    
                    if not conn.unipile_account_id:
                        print("  ❌ No UniPile account ID")
                        continue
                    
                    try:
                        # Try to get messages for this account
                        messages = unipile_client.messaging.get_messages(
                            account_id=conn.unipile_account_id,
                            limit=5
                        )
                        print(f"  ✅ Messages retrieved: {len(messages)}")
                        
                        # Show message details
                        for msg in messages[:3]:  # Show first 3
                            print(f"    - {msg.get('id', 'No ID')}: {msg.get('body', 'No body')[:50]}...")
                            print(f"      From: {msg.get('from', 'Unknown')}")
                            print(f"      Date: {msg.get('date', 'Unknown')}")
                        
                        # Now try to sync these messages to local database
                        print(f"  🔄 Syncing to local database...")
                        
                        # Import and use the message sync service
                        from communications.message_sync import MessageSyncService
                        sync_service = MessageSyncService()
                        
                        # Create or get channel for this connection
                        channel, created = Channel.objects.get_or_create(
                            name=f"{conn.account_name} Channel",
                            channel_type=conn.channel_type,
                            unipile_account_id=conn.unipile_account_id,
                            defaults={
                                'auth_status': 'authenticated',
                                'created_by': conn.user,
                                'is_active': True
                            }
                        )
                        
                        if created:
                            print(f"  ✅ Created channel: {channel.name}")
                        else:
                            print(f"  ✅ Using existing channel: {channel.name}")
                        
                        # Sync messages for this connection
                        for msg in messages[:3]:  # Sync first 3 messages
                            try:
                                # Create conversation if needed
                                conversation, conv_created = Conversation.objects.get_or_create(
                                    channel=channel,
                                    external_thread_id=msg.get('thread_id', msg.get('id', '')),
                                    defaults={
                                        'subject': msg.get('subject', 'No subject')[:500],
                                        'status': 'active'
                                    }
                                )
                                
                                # Create message if it doesn't exist
                                message_obj, msg_created = Message.objects.get_or_create(
                                    external_message_id=msg.get('id', ''),
                                    channel=channel,
                                    defaults={
                                        'conversation': conversation,
                                        'direction': 'inbound',  # Assume incoming for now
                                        'content': msg.get('body', 'No content'),
                                        'subject': msg.get('subject', '')[:500],
                                        'contact_email': msg.get('from', ''),
                                        'status': 'delivered',
                                        'received_at': msg.get('date'),
                                        'metadata': msg
                                    }
                                )
                                
                                if msg_created:
                                    print(f"    ✅ Created message: {message_obj.id}")
                                else:
                                    print(f"    ℹ️  Message already exists: {message_obj.id}")
                            
                            except Exception as sync_error:
                                print(f"    ❌ Failed to sync message: {sync_error}")
                    
                    except Exception as msg_error:
                        print(f"  ❌ Failed to get messages: {msg_error}")
                        import traceback
                        traceback.print_exc()
            
            except Exception as api_error:
                print(f"❌ API connection failed: {api_error}")
                import traceback
                traceback.print_exc()
        
        except Exception as e:
            print(f"❌ Error testing UniPile: {e}")
            import traceback
            traceback.print_exc()
        
        # Final status check
        print(f"\n📋 FINAL STATUS")
        print("-" * 40)
        print(f"Users: {User.objects.count()}")
        print(f"Channel Connections: {UserChannelConnection.objects.count()}")
        print(f"Channels: {Channel.objects.count()}")
        print(f"Conversations: {Conversation.objects.count()}")
        print(f"Messages: {Message.objects.count()}")

if __name__ == '__main__':
    main()