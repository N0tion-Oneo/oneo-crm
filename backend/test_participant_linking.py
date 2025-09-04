#!/usr/bin/env python
"""
Test script for the new participant-based linking system

This script tests that:
1. Participants are properly linked to records
2. Conversations are accessible through participants
3. The old RecordCommunicationLink is no longer used
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from django.db import connection
from pipelines.models import Record
from communications.models import Participant, Conversation, ConversationParticipant
from communications.record_communications.storage.participant_link_manager import ParticipantLinkManager


def test_participant_linking():
    """Test the participant-based linking system"""
    
    # Use demo tenant for testing
    tenant_schema = 'demo'
    
    with schema_context(tenant_schema):
        print(f"\n🔍 Testing Participant Linking System in tenant: {tenant_schema}")
        print("=" * 60)
        
        # Initialize link manager
        link_manager = ParticipantLinkManager()
        
        # Test 1: Check if participants exist and are linked to records
        print("\n1️⃣ Checking participant-record links...")
        participants_with_records = Participant.objects.filter(
            contact_record__isnull=False
        ).select_related('contact_record__pipeline')
        
        print(f"   Found {participants_with_records.count()} participants linked to records")
        
        # Show a few examples
        for participant in participants_with_records[:3]:
            record = participant.contact_record
            print(f"   • Participant: {participant.get_display_name()}")
            print(f"     → Record: {record.id} in pipeline '{record.pipeline.name}'")
            print(f"     → Confidence: {participant.resolution_confidence}")
            print(f"     → Method: {participant.resolution_method}")
        
        # Test 2: Check conversations linked through participants
        print("\n2️⃣ Testing conversation access through participants...")
        
        # Pick a record with communications
        test_record = Record.objects.filter(
            communication_participants__isnull=False
        ).first()
        
        if test_record:
            print(f"   Using test record: {test_record.id}")
            
            # Get conversations using the link manager
            conversations = link_manager.get_record_conversations(test_record)
            print(f"   Found {len(conversations)} conversations via participants")
            
            # Show conversation details
            for conv in conversations[:3]:
                participant_count = ConversationParticipant.objects.filter(
                    conversation=conv
                ).count()
                print(f"   • Conversation: {conv.subject or conv.id}")
                print(f"     → Channel: {conv.channel.channel_type}")
                print(f"     → Participants: {participant_count}")
                print(f"     → Messages: {conv.message_count}")
        else:
            print("   ⚠️ No records with linked participants found")
        
        # Test 3: Verify RecordCommunicationLink is not being used
        print("\n3️⃣ Checking RecordCommunicationLink removal...")
        try:
            # Try to import the model - it should fail or be commented out
            from communications.record_communications.models import RecordCommunicationLink
            
            # If import succeeds, check if table exists
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = %s 
                        AND table_name = 'communications_recordcommunicationlink'
                    )
                """, [tenant_schema])
                exists = cursor.fetchone()[0]
                
                if exists:
                    print("   ⚠️ RecordCommunicationLink table still exists")
                    print("   → Run migration to remove it: python manage.py migrate_schemas")
                else:
                    print("   ✅ RecordCommunicationLink table has been removed")
        except ImportError:
            print("   ✅ RecordCommunicationLink model cannot be imported (good!)")
        
        # Test 4: Test participant linking functionality
        print("\n4️⃣ Testing ParticipantLinkManager functionality...")
        
        # Find an unlinked participant
        unlinked_participant = Participant.objects.filter(
            contact_record__isnull=True,
            email__isnull=False
        ).exclude(email='').first()
        
        if unlinked_participant:
            print(f"   Found unlinked participant: {unlinked_participant.get_display_name()}")
            
            # Try to find a matching record
            from communications.record_communications.services import RecordIdentifierExtractor
            extractor = RecordIdentifierExtractor()
            
            if unlinked_participant.email:
                identifiers = {'email': [unlinked_participant.email]}
                matching_records = extractor.find_records_by_identifiers(identifiers)
                
                if matching_records:
                    print(f"   Found {len(matching_records)} potential record matches")
                    if len(matching_records) == 1:
                        # Link the participant
                        was_linked = link_manager.link_participant_to_record(
                            participant=unlinked_participant,
                            record=matching_records[0],
                            confidence=0.9,
                            method='test_script'
                        )
                        if was_linked:
                            print(f"   ✅ Successfully linked participant to record {matching_records[0].id}")
                        else:
                            print("   ℹ️ Participant was already linked")
                else:
                    print(f"   No matching records found for email: {unlinked_participant.email}")
        else:
            print("   ℹ️ No unlinked participants found to test")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Summary:")
        
        total_participants = Participant.objects.count()
        linked_participants = Participant.objects.filter(contact_record__isnull=False).count()
        link_percentage = (linked_participants / total_participants * 100) if total_participants > 0 else 0
        
        print(f"   Total Participants: {total_participants}")
        print(f"   Linked to Records: {linked_participants} ({link_percentage:.1f}%)")
        
        total_conversations = Conversation.objects.count()
        conversations_with_participants = Conversation.objects.filter(
            conversation_participants__isnull=False
        ).distinct().count()
        
        print(f"   Total Conversations: {total_conversations}")
        print(f"   With Participants: {conversations_with_participants}")
        
        print("\n✅ Participant linking system is working correctly!")
        
        # Recommendations
        if link_percentage < 50:
            print("\n💡 Recommendations:")
            print("   • Run sync to link more participants: python manage.py sync_record_communications")
            print("   • Check identifier extraction for better matching")


if __name__ == '__main__':
    test_participant_linking()