#!/usr/bin/env python3
"""
Message sync script for OneOTalent tenant with proper async/sync handling
"""

import os
import django
import asyncio
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import UserChannelConnection, Channel, Conversation, Message
from communications.unipile_sdk import UnipileClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async

User = get_user_model()

# Convert Django ORM operations to async
get_active_connections = sync_to_async(lambda: list(UserChannelConnection.objects.filter(
    account_status='active',
    is_active=True
)))

get_or_create_channel = sync_to_async(Channel.objects.get_or_create)
get_or_create_conversation = sync_to_async(Conversation.objects.get_or_create)
create_message = sync_to_async(Message.objects.create)
check_message_exists = sync_to_async(lambda msg_id: Message.objects.filter(external_message_id=msg_id).exists())
save_connection = sync_to_async(lambda conn: conn.save(update_fields=['last_sync_at']))
count_objects = sync_to_async(lambda model: model.objects.count())

async def main():
    print("🔄 MESSAGE SYNC FOR ONEOTALENT TENANT")
    print("=" * 60)
    
    # Switch to oneotalent tenant
    with schema_context('oneotalent'):
        print("✅ Connected to OneOTalent tenant")
        
        # Get active connections (sync converted to async)
        active_connections = await get_active_connections()
        
        print(f"Active connections: {len(active_connections)}")
        
        if not active_connections:
            print("❌ No active connections found")
            return
        
        for conn in active_connections:
            print(f"  - {conn.account_name} ({conn.channel_type}) - UniPile ID: {conn.unipile_account_id}")
        
        # Initialize UniPile client
        unipile_settings = settings.UNIPILE_SETTINGS
        client = UnipileClient(
            dsn=unipile_settings.dsn,
            access_token=unipile_settings.api_key
        )
        
        print("✅ UniPile client initialized")
        
        try:
            print("\n📱 TESTING API CONNECTION")
            print("-" * 40)
            
            # Test with accounts endpoint
            accounts = await client.account.get_accounts()
            print(f"✅ Found {len(accounts)} UniPile accounts")
            
            # Create account lookup
            account_map = {acc.get('id'): acc for acc in accounts}
            
            print(f"\n📨 SYNCING MESSAGES")
            print("-" * 40)
            
            total_new_messages = 0
            
            # Sync messages for each connection
            for conn in active_connections:
                print(f"\n🔄 Syncing: {conn.account_name}")
                
                if not conn.unipile_account_id:
                    print("  ❌ No UniPile account ID")
                    continue
                
                if conn.unipile_account_id not in account_map:
                    print(f"  ❌ Account {conn.unipile_account_id} not found in UniPile")
                    continue
                
                try:
                    # Get messages for this account
                    messages = await client.messaging.get_messages(
                        account_id=conn.unipile_account_id,
                        limit=20  # Get more messages to test
                    )
                    
                    print(f"  ✅ Retrieved {len(messages)} messages from UniPile")
                    
                    if not messages:
                        print("  ℹ️  No messages found for this account")
                        continue
                    
                    # Show sample message structure
                    sample_msg = messages[0] if messages else {}
                    print(f"  📋 Sample message keys: {list(sample_msg.keys())}")
                    
                    # Create or get channel
                    channel, created = await get_or_create_channel(
                        unipile_account_id=conn.unipile_account_id,
                        defaults={
                            'name': f"{conn.account_name} Channel",
                            'channel_type': conn.channel_type,
                            'auth_status': 'authenticated',
                            'created_by': conn.user,
                            'is_active': True
                        }
                    )
                    
                    if created:
                        print(f"  ✅ Created new channel: {channel.name}")
                    else:
                        print(f"  ✅ Using existing channel: {channel.name}")
                    
                    # Sync messages
                    new_messages = 0
                    for msg in messages:
                        try:
                            msg_id = msg.get('id', '')
                            if not msg_id:
                                print(f"    ⚠️  Skipping message without ID")
                                continue
                            
                            # Check if already exists
                            if await check_message_exists(msg_id):
                                continue
                            
                            # Extract message content
                            content = (
                                msg.get('text', '') or 
                                msg.get('body', '') or 
                                msg.get('content', '') or 
                                'No content'
                            )
                            
                            # Extract sender info
                            sender = msg.get('from', {})
                            if isinstance(sender, dict):
                                sender_email = sender.get('email', '') or sender.get('id', '')
                                sender_name = sender.get('name', '')
                            else:
                                sender_email = str(sender)
                                sender_name = ''
                            
                            # Determine direction (simple heuristic)
                            account_info = account_map.get(conn.unipile_account_id, {})
                            account_name = account_info.get('name', '')
                            is_outbound = sender_name == account_name or sender_email == account_name
                            direction = 'outbound' if is_outbound else 'inbound'
                            
                            # Create conversation
                            chat_id = msg.get('chat_id', '') or msg.get('thread_id', '') or msg_id
                            conversation, conv_created = await get_or_create_conversation(
                                channel=channel,
                                external_thread_id=chat_id,
                                defaults={
                                    'subject': content[:100] if content else 'No subject',
                                    'status': 'active'
                                }
                            )
                            
                            # Create message
                            await create_message(
                                external_message_id=msg_id,
                                channel=channel,
                                conversation=conversation,
                                direction=direction,
                                content=content,
                                subject=msg.get('subject', '')[:500],
                                contact_email=sender_email,
                                status='delivered',
                                received_at=msg.get('date') or timezone.now(),
                                metadata=msg
                            )
                            
                            new_messages += 1
                            
                        except Exception as msg_error:
                            print(f"    ❌ Failed to sync message: {msg_error}")
                    
                    print(f"  📊 Synced {new_messages} new messages")
                    total_new_messages += new_messages
                    
                    # Update connection
                    conn.last_sync_at = timezone.now()
                    await save_connection(conn)
                
                except Exception as sync_error:
                    print(f"  ❌ Sync failed: {sync_error}")
                    import traceback
                    traceback.print_exc()
        
        except Exception as api_error:
            print(f"❌ API connection failed: {api_error}")
            import traceback
            traceback.print_exc()
        
        # Final status
        print(f"\n📊 FINAL STATUS")
        print("-" * 40)
        channel_count = await count_objects(Channel)
        conversation_count = await count_objects(Conversation)
        message_count = await count_objects(Message)
        
        print(f"Channels: {channel_count}")
        print(f"Conversations: {conversation_count}")
        print(f"Messages: {message_count}")
        print(f"Total new messages synced: {total_new_messages}")
        
        if message_count > 0:
            print(f"\n✅ SUCCESS: Messages are now available in the database!")
            print(f"💡 The unified inbox should now show {message_count} messages")
        else:
            print(f"\n❌ No messages were synced to the database")

if __name__ == '__main__':
    asyncio.run(main())