#!/usr/bin/env python
"""
Clear all communication data from the oneotalent schema
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.db import transaction
from communications.models import (
    Message, Conversation, Participant, ConversationParticipant, Channel
)
from communications.record_communications.models import (
    RecordCommunicationLink, RecordSyncJob, RecordCommunicationProfile,
    RecordAttendeeMapping
)

def clear_all_communication_data():
    """Clear all communication data from oneotalent schema"""
    with schema_context('oneotalent'):
        with transaction.atomic():
            # Clear in order to respect foreign key constraints
            print("Clearing communication data...")
            
            # Clear sync-related data
            deleted = RecordSyncJob.objects.all().delete()
            print(f"  - Deleted RecordSyncJob: {deleted[0]} records")
            
            deleted = RecordCommunicationProfile.objects.all().delete()
            print(f"  - Deleted RecordCommunicationProfile: {deleted[0]} records")
            
            deleted = RecordAttendeeMapping.objects.all().delete()
            print(f"  - Deleted RecordAttendeeMapping: {deleted[0]} records")
            
            # Clear message and conversation data
            deleted = Message.objects.all().delete()
            print(f"  - Deleted Messages: {deleted[0]} records")
            
            deleted = ConversationParticipant.objects.all().delete()
            print(f"  - Deleted ConversationParticipants: {deleted[0]} records")
            
            deleted = Conversation.objects.all().delete()
            print(f"  - Deleted Conversations: {deleted[0]} records")
            
            deleted = RecordCommunicationLink.objects.all().delete()
            print(f"  - Deleted RecordCommunicationLinks: {deleted[0]} records")
            
            # Clear participants completely to test name fetching
            deleted = Participant.objects.all().delete()
            print(f"  - Deleted {deleted[0]} Participants")
            
            print("\nCommunication data cleared successfully!")
            print("Channels remain configured and active.")
            print("Ready for fresh sync from API.")

if __name__ == "__main__":
    clear_all_communication_data()
