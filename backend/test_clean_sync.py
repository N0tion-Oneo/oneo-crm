#!/usr/bin/env python
"""
Clean sync test - Clear all communication data and run fresh sync
"""

import os
import sys
import django
import logging
from datetime import datetime
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from django_tenants.utils import schema_context
from django.db import connection
from communications.models import (
    Message, Conversation, Participant, ConversationParticipant,
    Channel, UserChannelConnection
)
from communications.record_communications.models import (
    RecordCommunicationLink, RecordCommunicationProfile, 
    RecordSyncJob, RecordAttendeeMapping
)
from pipelines.models import Record

logger = logging.getLogger(__name__)

def clear_all_communication_data():
    """Clear all communication-related data"""
    print("\n🧹 CLEARING ALL COMMUNICATION DATA...")
    print("="*70)
    
    # Clear record communication data
    count = RecordAttendeeMapping.objects.all().delete()[0]
    print(f"  ✓ Deleted {count} RecordAttendeeMapping records")
    
    count = RecordSyncJob.objects.all().delete()[0]
    print(f"  ✓ Deleted {count} RecordSyncJob records")
    
    count = RecordCommunicationLink.objects.all().delete()[0]
    print(f"  ✓ Deleted {count} RecordCommunicationLink records")
    
    count = RecordCommunicationProfile.objects.all().delete()[0]
    print(f"  ✓ Deleted {count} RecordCommunicationProfile records")
    
    # Clear conversation participants
    count = ConversationParticipant.objects.all().delete()[0]
    print(f"  ✓ Deleted {count} ConversationParticipant records")
    
    # Clear participants
    count = Participant.objects.all().delete()[0]
    print(f"  ✓ Deleted {count} Participant records")
    
    # Clear messages
    count = Message.objects.all().delete()[0]
    print(f"  ✓ Deleted {count} Message records")
    
    # Clear conversations
    count = Conversation.objects.all().delete()[0]
    print(f"  ✓ Deleted {count} Conversation records")
    
    print("\n✅ All communication data cleared!")

def run_fresh_sync(record_id: int = 66):
    """Run a fresh sync for a record"""
    from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
    from communications.unipile.core.client import UnipileClient
    from django.conf import settings
    
    print(f"\n🔄 RUNNING FRESH SYNC FOR RECORD {record_id}...")
    print("="*70)
    
    # Configure sync settings
    settings.RECORD_SYNC_CONFIG = {
        'historical_days': 30,  # Last 30 days
        'max_messages_per_record': 500,  # Limit to 500 messages total
        'batch_size': 100,
        'channels': {
            'email': {'enabled': True, 'historical_days': 30, 'max_messages': 200, 'batch_size': 50},
            'gmail': {'enabled': True, 'historical_days': 30, 'max_messages': 200, 'batch_size': 50},
            'whatsapp': {'enabled': True, 'historical_days': 30, 'max_messages': 100, 'batch_size': 50},
            'linkedin': {'enabled': True, 'historical_days': 30, 'max_messages': 100, 'batch_size': 50}
        }
    }
    
    # Reset global config
    from communications.record_communications import utils
    utils._sync_config = None
    
    # Initialize UniPile client
    unipile_client = UnipileClient(
        dsn=settings.UNIPILE_DSN,
        access_token=settings.UNIPILE_API_KEY
    )
    
    # Create orchestrator and run sync
    orchestrator = RecordSyncOrchestrator(unipile_client)
    
    start_time = time.time()
    result = orchestrator.sync_record(
        record_id=record_id,
        trigger_reason='Fresh sync test after clearing all data'
    )
    elapsed_time = time.time() - start_time
    
    return result, elapsed_time

def analyze_sync_results():
    """Analyze the results of the sync"""
    print("\n📊 SYNC RESULTS ANALYSIS")
    print("="*70)
    
    # 1. Conversations
    total_conversations = Conversation.objects.count()
    print(f"\n📬 CONVERSATIONS: {total_conversations}")
    
    # By channel
    from django.db.models import Count
    channel_counts = Conversation.objects.values('channel__channel_type').annotate(
        count=Count('id')
    ).order_by('channel__channel_type')
    
    for cc in channel_counts:
        channel_type = cc['channel__channel_type'] or 'Unknown'
        print(f"  - {channel_type}: {cc['count']}")
    
    # 2. Messages
    total_messages = Message.objects.count()
    print(f"\n💬 MESSAGES: {total_messages}")
    
    # By channel
    message_counts = Message.objects.values('channel__channel_type').annotate(
        count=Count('id')
    ).order_by('channel__channel_type')
    
    for mc in message_counts:
        channel_type = mc['channel__channel_type'] or 'Unknown'
        print(f"  - {channel_type}: {mc['count']}")
    
    # By direction
    direction_counts = Message.objects.values('direction').annotate(
        count=Count('id')
    )
    print(f"\n📤 MESSAGE DIRECTIONS:")
    for dc in direction_counts:
        print(f"  - {dc['direction']}: {dc['count']}")
    
    # 3. Participants
    total_participants = Participant.objects.count()
    print(f"\n👥 PARTICIPANTS: {total_participants}")
    
    # With identifiers
    with_email = Participant.objects.exclude(email='').count()
    with_phone = Participant.objects.exclude(phone='').count()
    with_linkedin = Participant.objects.exclude(linkedin_member_urn='').count()
    with_names = Participant.objects.exclude(name='').count()
    
    print(f"  - With email: {with_email}")
    print(f"  - With phone: {with_phone}")
    print(f"  - With LinkedIn URN: {with_linkedin}")
    print(f"  - With names: {with_names}")
    
    # Sample participants
    print(f"\n👤 SAMPLE PARTICIPANTS:")
    for p in Participant.objects.all()[:10]:
        identifiers = []
        if p.email:
            identifiers.append(f"email={p.email}")
        if p.phone:
            identifiers.append(f"phone={p.phone}")
        if p.linkedin_member_urn:
            identifiers.append(f"linkedin={p.linkedin_member_urn[:20]}...")
        
        name_display = p.name or "(no name)"
        identifier_str = ", ".join(identifiers) if identifiers else "no identifiers"
        print(f"  - {name_display}: {identifier_str}")
    
    # 4. ConversationParticipant links
    conv_participants = ConversationParticipant.objects.all()
    conv_part_count = conv_participants.count()
    print(f"\n🔗 CONVERSATION-PARTICIPANT LINKS: {conv_part_count}")
    
    # Role distribution
    role_counts = conv_participants.values('role').annotate(count=Count('id'))
    if role_counts:
        print(f"\n📊 ROLE DISTRIBUTION:")
        for role in role_counts:
            print(f"  - {role['role']}: {role['count']}")
    
    # 5. Messages with sender_participant
    messages_with_sender = Message.objects.exclude(sender_participant__isnull=True).count()
    if total_messages > 0:
        percentage = (messages_with_sender / total_messages) * 100
        print(f"\n✉️ MESSAGES WITH SENDER PARTICIPANT: {messages_with_sender}/{total_messages} ({percentage:.1f}%)")
    
    # 6. Record communication links
    record_links = RecordCommunicationLink.objects.all()
    link_count = record_links.count()
    print(f"\n🔗 RECORD-CONVERSATION LINKS: {link_count}")
    
    # Sample links
    for link in record_links[:5]:
        print(f"  - Record {link.record_id} → Conversation: {link.conversation.subject[:50]}...")

def main():
    """Main test function"""
    tenant_schema = 'oneotalent'
    
    print("\n" + "="*70)
    print("CLEAN SYNC TEST")
    print("="*70)
    print(f"Timestamp: {datetime.now()}")
    print(f"Tenant: {tenant_schema}")
    print("="*70)
    
    with schema_context(tenant_schema):
        try:
            # 1. Check if we have the record
            try:
                record = Record.objects.get(id=66)
                print(f"\n✓ Found record: {record.id} - {record.data.get('first_name', '')} {record.data.get('last_name', '')}")
            except Record.DoesNotExist:
                print(f"\n✗ Record 66 not found. Please specify a valid record ID.")
                return
            
            # 2. Clear all existing data
            clear_all_communication_data()
            
            # 3. Run fresh sync
            result, elapsed_time = run_fresh_sync(66)
            
            if result.get('success'):
                print(f"\n✅ SYNC SUCCESSFUL!")
                print(f"  - Time taken: {elapsed_time:.2f} seconds")
                print(f"  - Total Conversations: {result.get('total_conversations', 0)}")
                print(f"  - Total Messages: {result.get('total_messages', 0)}")
                
                # Show channel breakdown
                channel_results = result.get('channel_results', {})
                print(f"\n📊 CHANNEL BREAKDOWN:")
                for channel, stats in channel_results.items():
                    if stats.get('conversations', 0) > 0 or stats.get('messages', 0) > 0:
                        print(f"  - {channel}: {stats.get('conversations', 0)} conversations, {stats.get('messages', 0)} messages")
            else:
                print(f"\n✗ Sync failed: {result.get('error')}")
                return
            
            # 4. Analyze results
            analyze_sync_results()
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            logger.exception("Test failed")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()