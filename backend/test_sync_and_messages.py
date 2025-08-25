#!/usr/bin/env python
"""
Test WhatsApp sync and message retrieval to debug frontend issue
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model
from communications.models import Channel, UserChannelConnection, ChatAttendee, Message, Conversation

User = get_user_model()

def test_sync_and_messages():
    """Test sync and message retrieval to see what's happening"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Testing WhatsApp Sync and Message Retrieval")
        print("=" * 60)
        
        # Get the WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        
        print(f"✅ Channel: {channel.name}")
        print(f"   ID: {channel.id}")
        print(f"   Account ID: {channel.unipile_account_id}")
        
        # Get sample conversations
        conversations = Conversation.objects.filter(
            channel=channel
        ).order_by('-updated_at')[:5]
        
        print(f"\n📊 Found {Conversation.objects.filter(channel=channel).count()} total conversations")
        print("\n💬 Recent conversations and their messages:")
        
        for conv in conversations:
            msg_count = conv.messages.count()
            
            # Get messages with sender info
            messages_with_senders = conv.messages.filter(sender__isnull=False).count()
            messages_without_senders = conv.messages.filter(sender__isnull=True).count()
            
            print(f"\n📱 Conversation: {conv.subject}")
            print(f"   External ID: {conv.external_thread_id}")
            print(f"   Total messages: {msg_count}")
            print(f"   Messages WITH sender: {messages_with_senders}")
            print(f"   Messages WITHOUT sender: {messages_without_senders}")
            print(f"   Attendees: {conv.conversation_attendees.count()}")
            
            # Show sample messages
            if msg_count > 0:
                print("   Sample messages:")
                for msg in conv.messages.order_by('-created_at')[:3]:
                    sender_info = "No sender"
                    if msg.sender:
                        sender_info = f"{msg.sender.name} ({msg.sender.external_attendee_id})"
                    elif msg.metadata:
                        sender_name = msg.metadata.get('attendee_name', 'Unknown')
                        sender_id = msg.metadata.get('attendee_id', 'Unknown')
                        sender_info = f"{sender_name} ({sender_id}) [metadata]"
                    
                    content_preview = msg.content[:50] if msg.content else "No content"
                    print(f"      - [{msg.direction}] {sender_info}: {content_preview}")
                    print(f"        External ID: {msg.external_message_id}")
                    
            # Test what the API would return
            messages_for_api = []
            for msg in conv.messages.order_by('-created_at')[:10]:
                sender_id = None
                sender_name = 'Unknown'
                
                if msg.sender:
                    sender_id = msg.sender.external_attendee_id
                    sender_name = msg.sender.name
                elif msg.metadata:
                    sender_id = msg.metadata.get('sender_id', msg.metadata.get('attendee_id'))
                    sender_name = msg.metadata.get('sender_name', msg.metadata.get('attendee_name', 'Unknown'))
                
                messages_for_api.append({
                    'id': msg.external_message_id,
                    'content': msg.content,
                    'sender': {
                        'id': sender_id,
                        'name': sender_name,
                        'is_self': msg.sender.is_self if msg.sender else False
                    },
                    'direction': msg.direction
                })
            
            if messages_for_api:
                print(f"   API would return {len(messages_for_api)} messages")
                # Check for issues
                no_sender_count = sum(1 for m in messages_for_api if m['sender']['id'] is None)
                if no_sender_count > 0:
                    print(f"   ⚠️ WARNING: {no_sender_count} messages have no sender ID!")
        
        # Check for orphaned messages (messages without senders)
        orphaned_messages = Message.objects.filter(
            channel=channel,
            sender__isnull=True
        ).count()
        
        print(f"\n⚠️ Orphaned messages (no sender): {orphaned_messages}")
        
        # Check attendees
        attendees = ChatAttendee.objects.filter(channel=channel).count()
        print(f"\n👥 Total attendees in channel: {attendees}")
        
        print("\n" + "=" * 60)
        print("✅ Analysis complete!")
        print("=" * 60)

if __name__ == "__main__":
    test_sync_and_messages()