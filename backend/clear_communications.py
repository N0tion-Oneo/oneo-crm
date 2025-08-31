#!/usr/bin/env python
"""
Script to clear all communication data for a fresh start
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import (
    Message, Conversation, Channel, UserChannelConnection,
    Participant, ConversationParticipant
)
from communications.record_communications.models import (
    RecordCommunicationLink, RecordCommunicationProfile,
    RecordSyncJob, RecordAttendeeMapping
)

def clear_communication_data():
    """Clear all communication-related data"""
    
    print("🗑️  Clearing communication data for oneotalent tenant...")
    
    # Get the oneotalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    # Use schema context for proper tenant isolation
    with schema_context(tenant.schema_name):
        # Clear messages first (foreign key constraints)
        count = Message.objects.all().delete()[0]
        print(f"   ✓ Deleted {count} messages")
        
        # Clear conversation participants
        count = ConversationParticipant.objects.all().delete()[0]
        print(f"   ✓ Deleted {count} conversation participants")
        
        # Clear conversations
        count = Conversation.objects.all().delete()[0]
        print(f"   ✓ Deleted {count} conversations")
        
        # Clear participants
        count = Participant.objects.all().delete()[0]
        print(f"   ✓ Deleted {count} participants")
        
        # Clear record communication links
        count = RecordCommunicationLink.objects.all().delete()[0]
        print(f"   ✓ Deleted {count} record communication links")
        
        # Clear record communication profiles
        count = RecordCommunicationProfile.objects.all().delete()[0]
        print(f"   ✓ Deleted {count} record communication profiles")
        
        # Clear sync jobs
        count = RecordSyncJob.objects.all().delete()[0]
        print(f"   ✓ Deleted {count} sync jobs")
        
        # Clear attendee mappings
        count = RecordAttendeeMapping.objects.all().delete()[0]
        print(f"   ✓ Deleted {count} attendee mappings")
        
        # Keep channels and connections (they're needed for syncing)
        print(f"\n📌 Keeping {Channel.objects.count()} channels")
        print(f"📌 Keeping {UserChannelConnection.objects.count()} channel connections")
    
    print("\n✅ Communication data cleared successfully!")
    print("   You can now run a fresh sync to get properly formatted HTML emails.")

if __name__ == "__main__":
    clear_communication_data()