#!/usr/bin/env python
"""
Script to delete all communication data for testing fresh sync
WARNING: This will delete ALL communication data!
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import transaction
from django_tenants.utils import schema_context
from communications.models import (
    Message, Conversation, ConversationParticipant, 
    Participant, Channel, UserChannelConnection,
    CommunicationAnalytics
)
from communications.record_communications.models import (
    RecordCommunicationProfile, RecordCommunicationLink,
    RecordAttendeeMapping, RecordSyncJob
)


def delete_all_communication_data(schema_name='demo'):
    """Delete all communication data from the specified schema"""
    
    print(f"\n{'='*60}")
    print(f"DELETING ALL COMMUNICATION DATA FROM SCHEMA: {schema_name}")
    print(f"{'='*60}\n")
    
    with schema_context(schema_name):
        with transaction.atomic():
            # Delete in correct order to respect foreign keys
            
            # First, delete any sync sessions and batches that might exist
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    # Delete sync-related tables first
                    cursor.execute("DELETE FROM communications_syncsession")
                    cursor.execute("DELETE FROM communications_syncbatch")
                    print(f"✓ Deleted sync sessions and batches")
            except Exception as e:
                print(f"Note: Could not delete sync tables: {e}")
            
            # 1. Delete Message-related data
            count = Message.objects.all().delete()[0]
            print(f"✓ Deleted {count} Messages")
            
            # 2. Delete ConversationParticipant relationships
            count = ConversationParticipant.objects.all().delete()[0]
            print(f"✓ Deleted {count} ConversationParticipants")
            
            # 3. Delete Conversations
            count = Conversation.objects.all().delete()[0]
            print(f"✓ Deleted {count} Conversations")
            
            # 4. Delete Participants
            count = Participant.objects.all().delete()[0]
            print(f"✓ Deleted {count} Participants")
            
            # 5. Delete Channels
            count = Channel.objects.all().delete()[0]
            print(f"✓ Deleted {count} Channels")
            
            # 6. Delete Analytics
            count = CommunicationAnalytics.objects.all().delete()[0]
            print(f"✓ Deleted {count} CommunicationAnalytics")
            
            # 7. Delete Record-centric models
            count = RecordCommunicationLink.objects.all().delete()[0]
            print(f"✓ Deleted {count} RecordCommunicationLinks")
            
            count = RecordAttendeeMapping.objects.all().delete()[0]
            print(f"✓ Deleted {count} RecordAttendeeMappings")
            
            count = RecordSyncJob.objects.all().delete()[0]
            print(f"✓ Deleted {count} RecordSyncJobs")
            
            count = RecordCommunicationProfile.objects.all().delete()[0]
            print(f"✓ Deleted {count} RecordCommunicationProfiles")
            
            print(f"\n✅ All communication data deleted from schema: {schema_name}")
    
    # Also check public schema for any shared data
    print(f"\nChecking public schema for UserChannelConnections...")
    
    # UserChannelConnection might be in public schema
    count = UserChannelConnection.objects.all().count()
    if count > 0:
        print(f"Found {count} UserChannelConnections in public schema")
        response = input("Delete UserChannelConnections? (y/n): ")
        if response.lower() == 'y':
            deleted = UserChannelConnection.objects.all().delete()[0]
            print(f"✓ Deleted {deleted} UserChannelConnections")
    else:
        print("✓ No UserChannelConnections found in public schema")


def verify_deletion(schema_name='demo'):
    """Verify all data has been deleted"""
    
    print(f"\n{'='*60}")
    print(f"VERIFYING DELETION IN SCHEMA: {schema_name}")
    print(f"{'='*60}\n")
    
    with schema_context(schema_name):
        models_to_check = [
            (Message, "Messages"),
            (Conversation, "Conversations"),
            (ConversationParticipant, "ConversationParticipants"),
            (Participant, "Participants"),
            (Channel, "Channels"),
            (CommunicationAnalytics, "CommunicationAnalytics"),
            (RecordCommunicationProfile, "RecordCommunicationProfiles"),
            (RecordCommunicationLink, "RecordCommunicationLinks"),
            (RecordAttendeeMapping, "RecordAttendeeMappings"),
            (RecordSyncJob, "RecordSyncJobs"),
        ]
        
        all_clear = True
        for model, name in models_to_check:
            count = model.objects.all().count()
            if count > 0:
                print(f"❌ {name}: {count} records still exist")
                all_clear = False
            else:
                print(f"✅ {name}: 0 records")
        
        if all_clear:
            print(f"\n✅ All communication data successfully deleted!")
        else:
            print(f"\n⚠️  Some data still remains!")
    
    # Check public schema
    count = UserChannelConnection.objects.all().count()
    if count > 0:
        print(f"⚠️  UserChannelConnections: {count} records still exist in public schema")
    else:
        print(f"✅ UserChannelConnections: 0 records in public schema")
    
    return all_clear


def main():
    """Main function"""
    
    print("\n" + "="*60)
    print("WARNING: This will DELETE ALL communication data!")
    print("="*60)
    
    # Get schema name
    schema_name = input("\nEnter schema name (default: demo): ").strip() or 'demo'
    
    # Confirm deletion
    confirm = input(f"\nAre you sure you want to delete ALL communication data from '{schema_name}'? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("Deletion cancelled.")
        return
    
    # Double confirm
    confirm2 = input("\nType 'DELETE' to confirm: ")
    
    if confirm2 != 'DELETE':
        print("Deletion cancelled.")
        return
    
    try:
        # Delete all data
        delete_all_communication_data(schema_name)
        
        # Verify deletion
        verify_deletion(schema_name)
        
        print("\n" + "="*60)
        print("Data deletion complete!")
        print("You can now run a fresh sync.")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error during deletion: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()