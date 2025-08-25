#!/usr/bin/env python
"""
Check messages and their conversation links
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Channel, Message, Conversation

def check_messages():
    """Check messages and conversation links"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Checking Messages and Conversation Links")
        print("=" * 60)
        
        # Get the WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        
        # Check messages
        total_messages = Message.objects.filter(channel=channel).count()
        messages_with_conversation = Message.objects.filter(
            channel=channel,
            conversation__isnull=False
        ).count()
        messages_without_conversation = Message.objects.filter(
            channel=channel,
            conversation__isnull=True
        ).count()
        
        print(f"📊 Message Statistics:")
        print(f"   Total messages: {total_messages}")
        print(f"   Messages WITH conversation: {messages_with_conversation}")
        print(f"   Messages WITHOUT conversation: {messages_without_conversation}")
        
        # Check conversations
        total_conversations = Conversation.objects.filter(channel=channel).count()
        conversations_with_messages = Conversation.objects.filter(
            channel=channel,
            messages__isnull=False
        ).distinct().count()
        
        print(f"\n💬 Conversation Statistics:")
        print(f"   Total conversations: {total_conversations}")
        print(f"   Conversations WITH messages: {conversations_with_messages}")
        print(f"   Conversations WITHOUT messages: {total_conversations - conversations_with_messages}")
        
        # Sample some orphaned messages
        orphaned_messages = Message.objects.filter(
            channel=channel,
            conversation__isnull=True
        ).order_by('-created_at')[:10]
        
        print(f"\n🔍 Sample orphaned messages (no conversation):")
        for msg in orphaned_messages:
            print(f"   - External ID: {msg.external_message_id}")
            print(f"     Chat ID: {msg.external_thread_id}")
            print(f"     Content: {msg.content[:50] if msg.content else 'No content'}")
            print(f"     Direction: {msg.direction}")
            print(f"     Created: {msg.created_at}")
            
            # Check if a conversation exists for this chat
            conv = Conversation.objects.filter(
                external_thread_id=msg.external_thread_id
            ).first()
            
            if conv:
                print(f"     ⚠️ ISSUE: Conversation EXISTS (ID: {conv.id}) but message not linked!")
            else:
                print(f"     ❌ No conversation found for chat ID: {msg.external_thread_id}")
        
        # Check a specific conversation we know should have messages
        test_chat_id = "sp8yWrO2XiqS33wjw9lqWQ"  # Josh Cowan chat
        test_conv = Conversation.objects.filter(external_thread_id=test_chat_id).first()
        
        if test_conv:
            print(f"\n🔍 Checking specific conversation: {test_conv.subject}")
            print(f"   External ID: {test_conv.external_thread_id}")
            print(f"   Messages linked: {test_conv.messages.count()}")
            
            # Check if there are orphaned messages for this chat
            orphaned_for_chat = Message.objects.filter(
                channel=channel,
                external_thread_id=test_chat_id,
                conversation__isnull=True
            ).count()
            
            if orphaned_for_chat > 0:
                print(f"   ⚠️ Found {orphaned_for_chat} orphaned messages for this chat!")
                
                # Show sample
                sample = Message.objects.filter(
                    channel=channel,
                    external_thread_id=test_chat_id,
                    conversation__isnull=True
                ).first()
                
                if sample:
                    print(f"   Sample orphaned message:")
                    print(f"     External msg ID: {sample.external_message_id}")
                    print(f"     Content: {sample.content[:50] if sample.content else 'No content'}")

if __name__ == "__main__":
    check_messages()