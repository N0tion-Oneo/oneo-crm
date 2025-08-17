#!/usr/bin/env python3
"""
Simple message sync script for OneOTalent tenant
Using actual UniPile API endpoints from documentation
"""

import os
import django
import asyncio
import json
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

User = get_user_model()

async def main():
    print("🔄 SIMPLE MESSAGE SYNC FOR ONEOTALENT")
    print("=" * 60)
    
    # Switch to oneotalent tenant
    with schema_context('oneotalent'):
        print("✅ Connected to OneOTalent tenant")
        
        # Get active connections
        active_connections = UserChannelConnection.objects.filter(
            account_status='active',
            is_active=True
        )
        
        print(f"Active connections: {active_connections.count()}")
        
        if not active_connections.exists():
            print("❌ No active connections found")
            return
        
        # Initialize UniPile client
        unipile_settings = settings.UNIPILE_SETTINGS
        client = UnipileClient(
            dsn=unipile_settings.dsn,
            access_token=unipile_settings.api_key
        )
        
        print("✅ UniPile client initialized")
        
        # Test API connection with accounts endpoint
        try:
            print("\n📱 TESTING API CONNECTION")
            print("-" * 40)
            
            accounts = await client.account.get_accounts()
            print(f"✅ API connection successful! Found {len(accounts)} accounts")
            
            # Map UniPile accounts to local connections
            account_map = {}
            for account in accounts:
                account_id = account.get('id')
                account_map[account_id] = account
                print(f"  - {account.get('provider', 'Unknown')}: {account.get('name', 'No name')} (ID: {account_id})")
            
            print(f"\n📨 SYNCING MESSAGES")
            print("-" * 40)
            
            # For each active connection, sync messages
            for conn in active_connections:
                print(f"\nSyncing: {conn.account_name} ({conn.channel_type})")
                
                if not conn.unipile_account_id:
                    print("  ❌ No UniPile account ID")
                    continue
                
                if conn.unipile_account_id not in account_map:
                    print(f"  ❌ Account {conn.unipile_account_id} not found in UniPile")
                    continue
                
                try:
                    # Get messages using the correct endpoint: GET /api/v1/messages
                    messages = await client.messaging.get_messages(
                        account_id=conn.unipile_account_id,
                        limit=10  # Start with just 10 messages
                    )
                    
                    print(f"  ✅ Retrieved {len(messages)} messages from UniPile")
                    
                    # Create or get channel for this connection
                    channel, created = Channel.objects.get_or_create(
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
                        print(f"  ✅ Created channel: {channel.name}")
                    else:
                        print(f"  ✅ Using existing channel: {channel.name}")
                    
                    # Sync messages to database
                    new_messages = 0
                    for msg in messages:
                        try:
                            # Extract message data
                            msg_id = msg.get('id', '')
                            if not msg_id:
                                continue
                            
                            # Check if message already exists
                            if Message.objects.filter(external_message_id=msg_id).exists():
                                continue
                            
                            # Determine message direction and sender info
                            sender = msg.get('from', {})
                            if isinstance(sender, dict):
                                sender_name = sender.get('name', '')
                                sender_email = sender.get('email', '')
                            else:
                                sender_name = str(sender)
                                sender_email = ''
                            
                            # Create conversation if needed
                            chat_id = msg.get('chat_id', msg_id)
                            conversation, conv_created = Conversation.objects.get_or_create(
                                channel=channel,
                                external_thread_id=chat_id,
                                defaults={
                                    'subject': msg.get('text', 'No subject')[:100],
                                    'status': 'active'
                                }
                            )
                            
                            # Create message
                            message_obj = Message.objects.create(
                                external_message_id=msg_id,
                                channel=channel,
                                conversation=conversation,
                                direction='inbound',  # Assume incoming for simplicity
                                content=msg.get('text', '') or msg.get('body', '') or 'No content',
                                subject=msg.get('subject', '')[:500],
                                contact_email=sender_email,
                                status='delivered',
                                received_at=msg.get('date') or timezone.now(),
                                metadata=msg
                            )
                            
                            new_messages += 1
                            print(f"    ✅ Created message: {msg_id[:20]}...")
                        
                        except Exception as msg_error:
                            print(f"    ❌ Failed to sync message {msg.get('id', 'unknown')}: {msg_error}")
                    
                    print(f"  📊 Synced {new_messages} new messages")
                    
                    # Update connection sync status
                    conn.last_sync_at = timezone.now()
                    conn.save(update_fields=['last_sync_at'])
                
                except Exception as sync_error:
                    print(f"  ❌ Failed to sync messages: {sync_error}")
                    import traceback
                    traceback.print_exc()
        
        except Exception as api_error:
            print(f"❌ API connection failed: {api_error}")
            import traceback
            traceback.print_exc()
        
        # Final status
        print(f"\n📊 FINAL STATUS")
        print("-" * 40)
        print(f"Channels: {Channel.objects.count()}")
        print(f"Conversations: {Conversation.objects.count()}")
        print(f"Messages: {Message.objects.count()}")

if __name__ == '__main__':
    asyncio.run(main())