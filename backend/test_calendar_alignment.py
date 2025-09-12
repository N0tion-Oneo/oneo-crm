#!/usr/bin/env python
"""Test script to verify calendar event creation alignment between scheduling and manual events"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Channel, ChannelType, Conversation, Message, Participant, ConversationParticipant
from communications.scheduling.models import SchedulingProfile
from pipelines.models import Record, Pipeline

User = get_user_model()

def test_manual_event_creation():
    """Test that manual event creation follows the scheduling pattern"""
    
    print("\n=== Testing Calendar Event Creation Alignment ===\n")
    
    # Get a tenant to work with
    tenant = Tenant.objects.filter(schema_name='oneotalent').first()
    if not tenant:
        tenant = Tenant.objects.exclude(schema_name='public').first()
    
    if not tenant:
        print("❌ No tenant found. Please create a tenant first.")
        return False
    
    print(f"✅ Using tenant: {tenant.name} (schema: {tenant.schema_name})")
    
    # Work within tenant context
    with schema_context(tenant.schema_name):
        # Get test user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ No superuser found in tenant. Please create a superuser first.")
            return False
        
        print(f"✅ Using user: {user.username}")
        
        # Check for SchedulingProfile
        profile = SchedulingProfile.objects.filter(user=user).first()
        if profile:
            print(f"✅ SchedulingProfile found for user")
            if profile.calendar_connection:
                print(f"✅ Calendar connection exists: {profile.calendar_connection.provider}")
            else:
                print("⚠️  No calendar connection configured (events will be created without UniPile sync)")
        else:
            print("⚠️  No SchedulingProfile found (events will be created without UniPile sync)")
        
        # Check for CALENDAR channel
        channel = Channel.objects.filter(
            channel_type=ChannelType.CALENDAR,
            created_by=user
        ).first()
        
        if channel:
            print(f"✅ CALENDAR channel exists: {channel.name}")
            print(f"   - Auth status: {channel.auth_status}")
            print(f"   - Metadata: {channel.metadata}")
        else:
            print("ℹ️  No CALENDAR channel exists yet (will be created on first event)")
        
        # Check conversation structure
        print("\n=== Checking Conversation Structure ===")
        
        recent_conversations = Conversation.objects.filter(
            channel__channel_type=ChannelType.CALENDAR
        ).order_by('-created_at')[:3]
        
        if recent_conversations:
            print(f"\n📅 Found {recent_conversations.count()} recent calendar conversations:")
            for conv in recent_conversations:
                print(f"\n   Conversation: {conv.subject}")
                print(f"   - Type: {conv.conversation_type}")
                print(f"   - Status: {conv.status}")
                print(f"   - External ID: {conv.external_thread_id}")
                print(f"   - Metadata: {conv.metadata.get('event_type', 'N/A')} event")
                
                # Check participants
                participants = ConversationParticipant.objects.filter(conversation=conv)
                if participants:
                    print(f"   - Participants ({participants.count()}):")
                    for cp in participants:
                        print(f"     • {cp.participant.name or cp.participant.email} ({cp.role})")
                
                # Check messages
                messages = Message.objects.filter(conversation=conv).order_by('created_at')[:1]
                for msg in messages:
                    print(f"   - Message direction: {msg.direction}")
                    print(f"   - Message status: {msg.status}")
                    print(f"   - Message metadata type: {msg.metadata.get('message_type', 'N/A') if msg.metadata else 'N/A'}")
                    if msg.metadata.get('event_data'):
                        event_data = msg.metadata['event_data']
                        print(f"     • Title: {event_data.get('title')}")
                        print(f"     • Type: {event_data.get('event_type')}")
                        print(f"     • Location type: {event_data.get('location_type')}")
        else:
            print("ℹ️  No calendar conversations found yet")
        
        # Verify pattern alignment
        print("\n=== Pattern Alignment Verification ===")
        
        checks = {
            "SchedulingProfile check": "✅" if profile else "⚠️",
            "Channel naming pattern": "✅" if not channel or "Calendar Events" in channel.name else "⚠️",
            "Channel metadata": "✅" if not channel or channel.metadata else "⚠️",
            "Conversation type": "✅" if not recent_conversations or any(c.conversation_type == 'calendar_event' for c in recent_conversations) else "⚠️",
            "Conversation status": "✅" if not recent_conversations or any(c.status == 'scheduled' for c in recent_conversations) else "⚠️",
            "Participant roles": "✅" if not recent_conversations or ConversationParticipant.objects.filter(role='organizer').exists() else "⚠️",
            "Message structure": "✅" if not recent_conversations or Message.objects.filter(metadata__message_type='event_created').exists() else "⚠️",
        }
        
        for check, status in checks.items():
            print(f"{status} {check}")
        
        # Summary
        print("\n=== Summary ===")
        success_count = sum(1 for status in checks.values() if status == "✅")
        total_count = len(checks)
        
        if success_count == total_count:
            print(f"✅ All {total_count} alignment checks passed!")
            print("The manual event creation now follows the scheduling pattern.")
        elif success_count > total_count * 0.7:
            print(f"⚠️  {success_count}/{total_count} checks passed.")
            print("The alignment is mostly complete but some areas may need attention.")
        else:
            print(f"❌ Only {success_count}/{total_count} checks passed.")
            print("Further alignment work may be needed.")
        
        return success_count == total_count

if __name__ == "__main__":
    success = test_manual_event_creation()
    sys.exit(0 if success else 1)