#!/usr/bin/env python
"""
Test UniPile API directly to check message limits
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection as db_connection
from tenants.models import Tenant
from communications.models import UserChannelConnection, Conversation
from communications.channels.whatsapp.service import WhatsAppService
from asgiref.sync import async_to_sync

def test_message_limits():
    """Test message retrieval limits directly"""
    print("=" * 60)
    print("Testing UniPile Message Limits")
    print("=" * 60)
    
    # Set tenant context FIRST
    tenant = Tenant.objects.get(schema_name='oneotalent')
    db_connection.set_tenant(tenant)
    print(f"\n✅ Set tenant context: {tenant.name}")
    
    # Now get connection - this should work in tenant context
    connection = UserChannelConnection.objects.filter(
        channel_type='whatsapp',
        is_active=True
    ).first()
    
    if not connection:
        print("❌ No WhatsApp connection found")
        return
        
    print(f"✅ Found connection: {connection.account_name}")
    print(f"   Account ID: {connection.unipile_account_id}")
    
    # Get channel
    from communications.models import Channel
    channel = Channel.objects.filter(
        unipile_account_id=connection.unipile_account_id,
        channel_type='whatsapp'
    ).first()
    
    if not channel:
        print("❌ No channel found")
        return
        
    # Initialize WhatsApp service
    service = WhatsAppService(channel=channel)
    
    # Get a few conversations
    conversations = Conversation.objects.filter(
        channel=channel
    ).order_by('-updated_at')[:3]
    
    print(f"\n📱 Testing message retrieval for {conversations.count()} conversations:")
    
    for conv in conversations:
        print(f"\n🔍 Conversation: {conv.external_thread_id[:30]}...")
        print(f"   External ID: {conv.external_thread_id}")
        
        # Test different limits
        for limit in [50, 100, 150]:
            try:
                result = async_to_sync(service.client.get_messages)(
                    account_id=connection.unipile_account_id,
                    conversation_id=conv.external_thread_id,
                    limit=limit
                )
                
                if result.get('success'):
                    msg_count = len(result.get('messages', []))
                    has_more = result.get('has_more', False)
                    total = result.get('total')
                    print(f"   Limit {limit}: Got {msg_count} messages (has_more: {has_more}, total: {total})")
                    
                    # Check message dates
                    if msg_count > 0:
                        messages = result.get('messages', [])
                        first_msg = messages[0]
                        last_msg = messages[-1]
                        print(f"      First message date: {first_msg.get('timestamp', 'unknown')}")
                        print(f"      Last message date: {last_msg.get('timestamp', 'unknown')}")
                    
                    # If we got less than the limit and no more, that's all there is
                    if msg_count < limit and not has_more:
                        print(f"      → Conversation only has {msg_count} messages total")
                        break
                else:
                    print(f"   Limit {limit}: ❌ Error: {result.get('error')}")
                    break
            except Exception as e:
                print(f"   Limit {limit}: ❌ Exception: {e}")
                break

if __name__ == "__main__":
    test_message_limits()