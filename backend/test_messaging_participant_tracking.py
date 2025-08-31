#!/usr/bin/env python
"""
Test WhatsApp and LinkedIn participant tracking improvements
"""

import os
import sys
import django
import logging
from datetime import datetime

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
from communications.models import Participant, ConversationParticipant, Message, Conversation
from communications.record_communications.models import RecordCommunicationLink
from pipelines.models import Record

logger = logging.getLogger(__name__)

def clear_participant_data():
    """Clear existing participant data for clean test"""
    print("\n🧹 Clearing existing participant data...")
    
    # Delete ConversationParticipant links
    conv_part_count = ConversationParticipant.objects.all().delete()[0]
    print(f"  ✓ Deleted {conv_part_count} ConversationParticipant links")
    
    # Delete Participants
    part_count = Participant.objects.all().delete()[0]
    print(f"  ✓ Deleted {part_count} Participants")
    
    # Clear sender_participant from messages
    Message.objects.update(sender_participant=None)
    print(f"  ✓ Cleared sender_participant from all messages")

def run_messaging_sync(record_id: int = 66):
    """Run sync for WhatsApp and LinkedIn channels"""
    from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
    from communications.unipile.core.client import UnipileClient
    from django.conf import settings
    
    print(f"\n🔄 Running messaging sync for record {record_id}...")
    
    # Configure for messaging channels only
    settings.RECORD_SYNC_CONFIG = {
        'historical_days': 7,  # Last 7 days for messaging
        'max_messages_per_record': 100,
        'batch_size': 50,
        'channels': {
            'email': {'enabled': False},  # Disable email
            'gmail': {'enabled': False},  # Disable gmail
            'whatsapp': {'enabled': True, 'historical_days': 7, 'max_messages': 100, 'batch_size': 50},
            'linkedin': {'enabled': True, 'historical_days': 7, 'max_messages': 100, 'batch_size': 50}
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
    result = orchestrator.sync_record(
        record_id=record_id,
        trigger_reason='Test WhatsApp/LinkedIn participant tracking'
    )
    
    return result

def analyze_messaging_participants():
    """Analyze participant tracking for messaging channels"""
    print("\n📊 MESSAGING PARTICIPANT TRACKING ANALYSIS")
    print("="*70)
    
    # 1. Total participants
    total_participants = Participant.objects.count()
    print(f"\n✅ TOTAL PARTICIPANTS: {total_participants}")
    
    # 2. Participants by type
    with_phone = Participant.objects.exclude(phone='').count()
    with_linkedin = Participant.objects.exclude(linkedin_member_urn='').count()
    with_names = Participant.objects.exclude(name='').count()
    
    print(f"\n📱 PARTICIPANT BREAKDOWN:")
    print(f"  - With phone (WhatsApp): {with_phone}")
    print(f"  - With LinkedIn URN: {with_linkedin}")
    if total_participants > 0:
        print(f"  - With names: {with_names}/{total_participants} ({with_names/total_participants*100:.1f}%)")
    else:
        print(f"  - With names: 0/0 (No participants)")
    
    # 3. Sample WhatsApp participants
    print(f"\n📱 SAMPLE WHATSAPP PARTICIPANTS:")
    whatsapp_participants = Participant.objects.exclude(phone='')[:5]
    for p in whatsapp_participants:
        provider_id = p.metadata.get('provider_id', '')
        print(f"  - {p.name or 'Unknown'}: {p.phone} (provider: {provider_id[:20]}...)")
    
    # 4. Sample LinkedIn participants
    print(f"\n💼 SAMPLE LINKEDIN PARTICIPANTS:")
    linkedin_participants = Participant.objects.exclude(linkedin_member_urn='')[:5]
    for p in linkedin_participants:
        print(f"  - {p.name or 'Unknown'}: {p.linkedin_member_urn[:30]}...")
    
    # 5. ConversationParticipant links for messaging
    from django.db.models import Count
    
    # Get conversations from messaging channels
    messaging_conversations = Conversation.objects.filter(
        channel__channel_type__in=['whatsapp', 'linkedin']
    )
    
    if messaging_conversations.exists():
        conv_participants = ConversationParticipant.objects.filter(
            conversation__in=messaging_conversations
        )
        conv_part_count = conv_participants.count()
        print(f"\n✅ MESSAGING CONVERSATION-PARTICIPANT LINKS: {conv_part_count}")
        
        # Check role distribution
        role_counts = conv_participants.values('role').annotate(count=Count('id'))
        print(f"\n📊 ROLE DISTRIBUTION IN MESSAGING:")
        for role in role_counts:
            print(f"  - {role['role']}: {role['count']}")
    else:
        print("\n⚠️ No messaging conversations found")
    
    # 6. Messages with sender_participant in messaging channels
    messaging_messages = Message.objects.filter(
        channel__channel_type__in=['whatsapp', 'linkedin']
    )
    
    if messaging_messages.exists():
        messages_with_sender = messaging_messages.exclude(sender_participant__isnull=True).count()
        total_messages = messaging_messages.count()
        if total_messages > 0:
            print(f"\n✅ MESSAGING MESSAGES WITH SENDER: {messages_with_sender}/{total_messages} ({messages_with_sender/total_messages*100:.1f}%)")
        else:
            print(f"\n✅ MESSAGING MESSAGES WITH SENDER: 0/0")
    else:
        print("\n⚠️ No messaging messages found")
    
    # 7. Check specific WhatsApp conversation
    whatsapp_conv = Conversation.objects.filter(
        channel__channel_type='whatsapp'
    ).first()
    
    if whatsapp_conv:
        print(f"\n📱 SAMPLE WHATSAPP CONVERSATION:")
        print(f"Subject: {whatsapp_conv.subject[:50]}...")
        conv_parts = ConversationParticipant.objects.filter(conversation=whatsapp_conv)
        for cp in conv_parts[:5]:
            participant_info = f"{cp.participant.name or 'Unknown'}"
            if cp.participant.phone:
                participant_info += f" ({cp.participant.phone})"
            print(f"  - {participant_info} [{cp.role}]")
    
    # 8. Check specific LinkedIn conversation
    linkedin_conv = Conversation.objects.filter(
        channel__channel_type='linkedin'
    ).first()
    
    if linkedin_conv:
        print(f"\n💼 SAMPLE LINKEDIN CONVERSATION:")
        print(f"Subject: {linkedin_conv.subject[:50]}...")
        conv_parts = ConversationParticipant.objects.filter(conversation=linkedin_conv)
        for cp in conv_parts[:5]:
            participant_info = f"{cp.participant.name or 'Unknown'}"
            if cp.participant.linkedin_member_urn:
                participant_info += f" ({cp.participant.linkedin_member_urn[:20]}...)"
            print(f"  - {participant_info} [{cp.role}]")

def main():
    """Main test function"""
    tenant_schema = 'oneotalent'
    
    print("\n" + "="*70)
    print("WHATSAPP/LINKEDIN PARTICIPANT TRACKING TEST")
    print("="*70)
    print(f"Timestamp: {datetime.now()}")
    print(f"Tenant: {tenant_schema}")
    print("="*70)
    
    with schema_context(tenant_schema):
        try:
            # 1. Clear existing data
            clear_participant_data()
            
            # 2. Check if we have the record
            try:
                record = Record.objects.get(id=66)
                print(f"\n✓ Found record: {record.id} - {record.data.get('first_name', '')} {record.data.get('last_name', '')}")
            except Record.DoesNotExist:
                print(f"\n✗ Record 66 not found. Please specify a valid record ID.")
                return
            
            # 3. Run sync
            result = run_messaging_sync(66)
            
            if result.get('success'):
                print(f"\n✓ Sync successful!")
                print(f"  - Total Conversations: {result.get('total_conversations', 0)}")
                print(f"  - Total Messages: {result.get('total_messages', 0)}")
                
                channel_results = result.get('channel_results', {})
                for channel, stats in channel_results.items():
                    if stats.get('conversations', 0) > 0:
                        print(f"  - {channel}: {stats.get('conversations', 0)} conversations, {stats.get('messages', 0)} messages")
            else:
                print(f"\n✗ Sync failed: {result.get('error')}")
                return
            
            # 4. Analyze results
            analyze_messaging_participants()
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            logger.exception("Test failed")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()