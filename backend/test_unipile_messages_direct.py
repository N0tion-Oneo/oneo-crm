#!/usr/bin/env python
"""
Test UniPile API directly to check message limits
"""
import os
import sys
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection as db_connection
from tenants.models import Tenant
from communications.models import UserChannelConnection, Conversation
from communications.channels.whatsapp.client import WhatsAppClient
from communications.unipile import UnipileClient
from asgiref.sync import sync_to_async

def test_message_limits_sync():
    """Test message retrieval limits directly"""
    print("=" * 60)
    print("Testing UniPile Message Limits")
    print("=" * 60)
    
    # Set tenant context
    tenant = Tenant.objects.get(schema_name='oneotalent')
    db_connection.set_tenant(tenant)
    print(f"\n✅ Set tenant context: {tenant.name}")
    
    # Get connection
    connection = (
        UserChannelConnection.objects.filter(
            channel_type='whatsapp',
            is_active=True
        ).first
    )()
    
    if not connection:
        print("❌ No WhatsApp connection found")
        return
        
    print(f"✅ Found connection: {connection.account_name}")
    print(f"   Account ID: {connection.unipile_account_id}")
    
    # Initialize WhatsApp client
    client = WhatsAppClient()
    
    # Get a conversation with many messages
    conversations = await sync_to_async(list)(
        Conversation.objects.filter(
            channel__channel_type='whatsapp'
        ).order_by('-updated_at')[:5]
    )
    
    print(f"\n📱 Testing message retrieval for {len(conversations)} conversations:")
    
    for conv in conversations:
        print(f"\n🔍 Conversation: {conv.name or conv.external_thread_id[:30]}")
        print(f"   External ID: {conv.external_thread_id}")
        
        # Test different limits
        for limit in [50, 100, 150, 200]:
            result = await client.get_messages(
                account_id=connection.unipile_account_id,
                conversation_id=conv.external_thread_id,
                limit=limit
            )
            
            if result.get('success'):
                msg_count = len(result.get('messages', []))
                has_more = result.get('has_more', False)
                print(f"   Limit {limit}: Got {msg_count} messages (has_more: {has_more})")
                
                # If we got less than the limit, that's all there is
                if msg_count < limit:
                    print(f"      → Conversation only has {msg_count} messages total")
                    break
            else:
                print(f"   Limit {limit}: ❌ Error: {result.get('error')}")
                break

if __name__ == "__main__":
    asyncio.run(test_message_limits())