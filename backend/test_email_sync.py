#!/usr/bin/env python
"""
Test email sync with participant linking
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record
from communications.models import (
    Participant, Conversation, ConversationParticipant, 
    UserChannelConnection
)
from communications.record_communications.models import RecordCommunicationProfile
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from communications.unipile.core.client import UnipileClient
from communications.record_communications.storage.participant_link_manager import ParticipantLinkManager


def test_sync():
    """Test email sync for a record"""
    
    tenant_schema = 'oneotalent'
    record_id = 93  # Robbie Cowan
    
    with schema_context(tenant_schema):
        print(f"\n🔄 Testing Email Sync for Record {record_id}")
        print("=" * 60)
        
        # Get the record
        try:
            record = Record.objects.get(id=record_id)
            print(f"✅ Found record: {record.data.get('first_name')} {record.data.get('last_name')}")
            print(f"   Email: {record.data.get('personal_email')}")
        except Record.DoesNotExist:
            print(f"❌ Record {record_id} not found")
            return
        
        # Check for active channel connections
        connections = UserChannelConnection.objects.filter(
            is_active=True,
            account_status='active',
            channel_type__in=['gmail', 'email']
        )
        
        if not connections.exists():
            print("\n⚠️ No active email connections found")
            print("   Please connect an email account via UniPile")
            return
        
        print(f"\n📧 Found {connections.count()} email connection(s)")
        for conn in connections:
            print(f"   • {conn.channel_type}: {conn.account_name}")
        
        # Initialize UniPile client
        unipile_client = UnipileClient()
        
        # Initialize sync orchestrator
        orchestrator = RecordSyncOrchestrator(unipile_client)
        
        print("\n🚀 Starting sync...")
        
        # Run sync
        result = orchestrator.sync_record(
            record_id=record_id,
            trigger_reason='Test participant linking'
        )
        
        print("\n📊 Sync Results:")
        print(f"   Conversations synced: {result.get('total_conversations', 0)}")
        print(f"   Messages synced: {result.get('total_messages', 0)}")
        
        # Check participant linking
        print("\n🔗 Checking Participant Links:")
        
        participants = Participant.objects.filter(
            contact_record=record
        )
        
        if participants.exists():
            print(f"✅ {participants.count()} participants linked to this record:")
            for p in participants:
                print(f"   • {p.get_display_name()}")
                print(f"     Email: {p.email}")
                print(f"     Confidence: {p.resolution_confidence}")
                print(f"     Method: {p.resolution_method}")
        else:
            print("⚠️ No participants linked to this record yet")
            
            # Check if there are any participants with matching email
            email = record.data.get('personal_email')
            if email:
                matching_participants = Participant.objects.filter(email__iexact=email)
                if matching_participants.exists():
                    print(f"\n🔍 Found {matching_participants.count()} participant(s) with matching email:")
                    
                    # Try to link them
                    link_manager = ParticipantLinkManager()
                    for p in matching_participants:
                        if not p.contact_record:
                            was_linked = link_manager.link_participant_to_record(
                                participant=p,
                                record=record,
                                confidence=0.95,
                                method='email_sync_test'
                            )
                            if was_linked:
                                print(f"   ✅ Linked participant {p.id} to record")
                        else:
                            print(f"   ℹ️ Participant {p.id} already linked to record {p.contact_record_id}")
        
        # Check conversations accessible through participants
        print("\n💬 Checking Conversation Access:")
        
        link_manager = ParticipantLinkManager()
        conversations = link_manager.get_record_conversations(record)
        
        if conversations:
            print(f"✅ {len(conversations)} conversations accessible via participants:")
            for conv in conversations[:5]:
                print(f"   • {conv.subject or f'Conversation {conv.id}'}")
                print(f"     Channel: {conv.channel.channel_type}")
                print(f"     Messages: {conv.message_count}")
        else:
            print("⚠️ No conversations found via participants")
        
        print("\n✅ Test complete!")


if __name__ == '__main__':
    test_sync()
