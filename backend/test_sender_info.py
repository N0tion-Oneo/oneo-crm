#!/usr/bin/env python
"""
Check sender information in messages
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Message, Conversation, ChatAttendee

def check_sender_info():
    """Check sender information in messages"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Checking Sender Information in Messages")
        print("=" * 60)
        
        # Get the specific conversation
        conv = Conversation.objects.filter(
            external_thread_id='sp8yWrO2XiqS33wjw9lqWQ'
        ).first()
        
        if not conv:
            print("❌ Conversation not found")
            return
            
        print(f"✅ Conversation: {conv.subject}")
        print(f"   External ID: {conv.external_thread_id}")
        print(f"   Messages: {conv.messages.count()}")
        print(f"   Attendees: {conv.conversation_attendees.count()}")
        
        # Check attendees
        print("\n👥 Attendees in conversation:")
        for ca in conv.conversation_attendees.all():
            attendee = ca.attendee
            print(f"   - {attendee.name}")
            print(f"     External ID: {attendee.external_attendee_id}")
            print(f"     Provider ID: {attendee.provider_id}")
            print(f"     Is self: {attendee.is_self}")
            print(f"     Metadata: {attendee.metadata}")
        
        # Check messages
        print("\n📨 Messages in conversation:")
        for msg in conv.messages.order_by('-created_at')[:10]:
            print(f"\n   Message ID: {msg.external_message_id}")
            print(f"   Direction: {msg.direction}")
            print(f"   Content: {msg.content[:50] if msg.content else 'No content'}")
            
            if msg.sender:
                print(f"   ✅ Has sender: {msg.sender.name} ({msg.sender.external_attendee_id})")
                print(f"      Is self: {msg.sender.is_self}")
            else:
                print(f"   ❌ No sender linked")
            
            if msg.metadata:
                print(f"   Metadata:")
                if 'attendee_id' in msg.metadata:
                    print(f"     attendee_id: {msg.metadata['attendee_id']}")
                if 'attendee_name' in msg.metadata:
                    print(f"     attendee_name: {msg.metadata['attendee_name']}")
                if 'sender_id' in msg.metadata:
                    print(f"     sender_id: {msg.metadata['sender_id']}")
                if 'sender_attendee_id' in msg.metadata:
                    print(f"     sender_attendee_id: {msg.metadata['sender_attendee_id']}")
        
        # Check for orphaned attendees
        print("\n🔍 All attendees in channel:")
        channel = conv.channel
        all_attendees = ChatAttendee.objects.filter(channel=channel).order_by('name')[:10]
        for att in all_attendees:
            msg_count = Message.objects.filter(sender=att).count()
            print(f"   - {att.name}: {msg_count} messages as sender")

if __name__ == "__main__":
    check_sender_info()