#!/usr/bin/env python
"""
Clear communication data for oneotalent tenant
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from communications.models import (
    Conversation, Message, Participant, 
    ConversationParticipant, Channel
)
from communications.record_communications.models import (
    RecordCommunicationProfile,
    RecordSyncJob,
    RecordAttendeeMapping
)

def clear_communication_data():
    """Clear all communication data for oneotalent tenant"""
    
    tenant_schema = 'oneotalent'
    
    with schema_context(tenant_schema):
        print(f"🗑️ Clearing communication data for tenant: {tenant_schema}")
        print("=" * 60)
        
        # Get counts before deletion
        conversations_count = Conversation.objects.count()
        messages_count = Message.objects.count()
        participants_count = Participant.objects.count()
        linked_participants = Participant.objects.filter(contact_record__isnull=False).count()
        
        print(f"📊 Before clearing:")
        print(f"   Conversations: {conversations_count}")
        print(f"   Messages: {messages_count}")
        print(f"   Participants: {participants_count}")
        print(f"   Linked Participants: {linked_participants}")
        
        # Clear data
        print("\n🔄 Clearing data...")
        
        # Clear participant links
        updated = Participant.objects.filter(contact_record__isnull=False).update(
            contact_record=None,
            resolution_confidence=0,
            resolution_method='',
            resolved_at=None
        )
        print(f"✓ Cleared {updated} participant-record links")
        
        # Delete messages
        deleted = Message.objects.all().delete()
        print(f"✓ Deleted {deleted[0]} messages")
        
        # Delete conversation participants
        deleted = ConversationParticipant.objects.all().delete()
        print(f"✓ Deleted {deleted[0]} conversation participants")
        
        # Delete conversations
        deleted = Conversation.objects.all().delete()
        print(f"✓ Deleted {deleted[0]} conversations")
        
        # Delete participants
        deleted = Participant.objects.all().delete()
        print(f"✓ Deleted {deleted[0]} participants")
        
        # Delete channels
        deleted = Channel.objects.all().delete()
        print(f"✓ Deleted {deleted[0]} channels")
        
        # Clear sync jobs
        deleted = RecordSyncJob.objects.all().delete()
        print(f"✓ Deleted {deleted[0]} sync jobs")
        
        # Clear attendee mappings
        deleted = RecordAttendeeMapping.objects.all().delete()
        print(f"✓ Deleted {deleted[0]} attendee mappings")
        
        # Keep profiles but reset their stats
        profiles = RecordCommunicationProfile.objects.all()
        profiles.update(
            sync_status='not_started',
            sync_in_progress=False,
            total_conversations=0,
            total_messages=0,
            total_unread=0,
            last_message_at=None,
            last_full_sync=None
        )
        print(f"✓ Reset {profiles.count()} communication profiles")
        
        print("\n✅ Communication data cleared successfully!")


if __name__ == '__main__':
    clear_communication_data()