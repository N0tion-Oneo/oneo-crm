#!/usr/bin/env python3
"""
Message sync script for OneOTalent tenant - Fixed version
"""

import os
import django
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
import requests

User = get_user_model()

def main():
    print("🔄 MESSAGE SYNC FOR ONEOTALENT TENANT")
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
        
        for conn in active_connections:
            print(f"  - {conn.account_name} ({conn.channel_type}) - UniPile ID: {conn.unipile_account_id}")
        
        # Test direct UniPile API call with requests
        unipile_settings = settings.UNIPILE_SETTINGS
        print(f"Using UniPile DSN: {unipile_settings.dsn}")
        
        try:
            print("\n📱 TESTING DIRECT API CONNECTION")
            print("-" * 40)
            
            # Test accounts endpoint directly
            accounts_url = f"{unipile_settings.dsn}/api/v1/accounts"
            headers = {
                'X-API-KEY': unipile_settings.api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            accounts_response = requests.get(accounts_url, headers=headers, timeout=30)
            
            if accounts_response.status_code == 200:
                response = accounts_response.json()
                
                # Extract accounts from the response.items array
                if isinstance(response, dict) and 'items' in response:
                    accounts = response['items']
                    print(f"✅ Found {len(accounts)} UniPile accounts")
                    
                    # Map accounts by ID
                    account_map = {acc.get('id'): acc for acc in accounts}
                    
                    # Show accounts
                    for acc in accounts:
                        provider = acc.get('type', 'Unknown').lower().replace('_oauth', '').replace('google', 'gmail')
                        status = 'OK' if any(s.get('status') == 'OK' for s in acc.get('sources', [])) else 'NOT_OK'
                        print(f"  - {provider}: {acc.get('name', 'No name')} (ID: {acc.get('id')}) - Status: {status}")
                else:
                    print(f"❌ Unexpected response format: {response}")
                    return
                
                print(f"\n📨 SYNCING MESSAGES")
                print("-" * 40)
                
                total_new_messages = 0
                
                # Sync for each connection
                for conn in active_connections:
                    print(f"\n🔄 {conn.account_name}")
                    
                    if not conn.unipile_account_id:
                        print("  ❌ No UniPile account ID")
                        continue
                    
                    if conn.unipile_account_id not in account_map:
                        print(f"  ❌ Account {conn.unipile_account_id} not found")
                        continue
                    
                    try:
                        # Get messages for this account
                        messages_url = f"{unipile_settings.dsn}/api/v1/messages"
                        params = {
                            'account_id': conn.unipile_account_id,
                            'limit': 20  # Get more messages now that parsing is fixed
                        }
                        
                        messages_response = requests.get(messages_url, headers=headers, params=params, timeout=30)
                        
                        if messages_response.status_code == 200:
                            messages_response_data = messages_response.json()
                            
                            # Handle messages response format (likely similar to accounts)
                            if isinstance(messages_response_data, dict) and 'items' in messages_response_data:
                                messages = messages_response_data['items']
                            else:
                                messages = messages_response_data
                                
                            print(f"  ✅ Retrieved {len(messages)} messages")
                            
                            if not messages:
                                print("  ℹ️  No messages found")
                                continue
                            
                            # Show first message structure
                            first_msg = messages[0] if messages else {}
                            print(f"  📋 Sample message keys: {list(first_msg.keys())}")
                            print(f"  📋 Sample message data: {first_msg}")
                            
                            # Create or get channel
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
                                print(f"  ✅ Using channel: {channel.name}")
                            
                            # Sync messages
                            new_messages = 0
                            for msg in messages:
                                try:
                                    msg_id = msg.get('id', '')
                                    if not msg_id:
                                        continue
                                    
                                    # Skip if exists
                                    if Message.objects.filter(external_message_id=msg_id).exists():
                                        continue
                                    
                                    # Extract content
                                    content = (
                                        msg.get('text', '') or 
                                        msg.get('body', '') or 
                                        msg.get('content', '') or 
                                        'No content'
                                    )
                                    
                                    # Extract sender - use sender_id for WhatsApp
                                    sender_id = msg.get('sender_id', '') or msg.get('from', {})
                                    if isinstance(sender_id, dict):
                                        sender_email = sender_id.get('email', '') or sender_id.get('id', '')
                                    else:
                                        sender_email = str(sender_id)
                                    
                                    # Create conversation
                                    chat_id = msg.get('chat_id', '') or msg.get('thread_id', '') or msg_id
                                    conversation, conv_created = Conversation.objects.get_or_create(
                                        channel=channel,
                                        external_thread_id=chat_id,
                                        defaults={
                                            'subject': content[:100],
                                            'status': 'active'
                                        }
                                    )
                                    
                                    # Create message (handle None values)
                                    subject = msg.get('subject') or ''
                                    timestamp = msg.get('timestamp') or msg.get('date') or timezone.now()
                                    
                                    Message.objects.create(
                                        external_message_id=msg_id,
                                        channel=channel,
                                        conversation=conversation,
                                        direction='inbound',  # Default to inbound
                                        content=content,
                                        subject=subject[:500] if subject else '',
                                        contact_email=sender_email,
                                        status='delivered',
                                        received_at=timestamp,
                                        metadata=msg
                                    )
                                    
                                    new_messages += 1
                                    
                                except Exception as msg_error:
                                    print(f"    ❌ Message sync error: {msg_error}")
                            
                            print(f"  📊 Synced {new_messages} new messages")
                            total_new_messages += new_messages
                            
                            # Update connection
                            conn.last_sync_at = timezone.now()
                            conn.save(update_fields=['last_sync_at'])
                        
                        else:
                            print(f"  ❌ Messages API failed: {messages_response.status_code}")
                            print(f"      Response: {messages_response.text[:200]}")
                    
                    except Exception as sync_error:
                        print(f"  ❌ Sync failed: {sync_error}")
                        import traceback
                        traceback.print_exc()
                
                print(f"\n📊 FINAL STATUS")
                print("-" * 40)
                print(f"Channels: {Channel.objects.count()}")
                print(f"Conversations: {Conversation.objects.count()}")
                print(f"Messages: {Message.objects.count()}")
                print(f"Total synced: {total_new_messages}")
                
                if Message.objects.count() > 0:
                    print(f"\n✅ SUCCESS: Messages synced! Check your inbox at:")
                    print(f"💡 http://oneotalent.localhost:3000/communications")
                else:
                    print(f"\n⚠️  No messages were synced")
            
            else:
                print(f"❌ Accounts API failed: {accounts_response.status_code}")
                print(f"Response: {accounts_response.text}")
        
        except Exception as api_error:
            print(f"❌ API error: {api_error}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()