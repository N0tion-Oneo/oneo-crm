#!/usr/bin/env python
"""Clear all communication data for a tenant"""
import os
import sys
import django
import argparse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import (
    Conversation, Message, Participant, ConversationParticipant
)
from communications.record_communications.models import (
    RecordCommunicationProfile,
    RecordSyncJob, RecordAttendeeMapping
)

def clear_communication_data(tenant_schema):
    """Clear all communication data for a tenant"""
    with schema_context(tenant_schema):
        # Delete in correct order to respect foreign keys
        print(f"Clearing communication data for tenant: {tenant_schema}")
        
        # Clear record-specific models
        count = RecordAttendeeMapping.objects.all().delete()[0]
        print(f"  - Deleted {count} RecordAttendeeMappings")
        
        count = RecordSyncJob.objects.all().delete()[0]
        print(f"  - Deleted {count} RecordSyncJobs")
        
        count = RecordCommunicationProfile.objects.all().delete()[0]
        print(f"  - Deleted {count} RecordCommunicationProfiles")
        
        # Clear messages
        count = Message.objects.all().delete()[0]
        print(f"  - Deleted {count} Messages")
        
        # Clear conversation participants
        count = ConversationParticipant.objects.all().delete()[0]
        print(f"  - Deleted {count} ConversationParticipants")
        
        # Clear conversations
        count = Conversation.objects.all().delete()[0]
        print(f"  - Deleted {count} Conversations")
        
        # Clear participant record links first
        count = Participant.objects.filter(contact_record__isnull=False).update(contact_record=None)
        print(f"  - Cleared {count} Participant record links")
        
        # Clear participants
        count = Participant.objects.all().delete()[0]
        print(f"  - Deleted {count} Participants")
        
        print("✅ All communication data cleared")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Clear communication data for a tenant')
    parser.add_argument('--tenant', required=True, help='Tenant schema name')
    args = parser.parse_args()
    
    clear_communication_data(args.tenant)