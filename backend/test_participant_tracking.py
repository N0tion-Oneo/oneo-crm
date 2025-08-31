#!/usr/bin/env python
"""
Test participant tracking improvements
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
from communications.models import Participant, ConversationParticipant, Message
from communications.record_communications.models import RecordCommunicationLink

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

def run_test_sync():
    """Run a limited sync to test participant tracking"""
    from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
    from communications.unipile.core.client import UnipileClient
    from django.conf import settings
    
    print("\n🔄 Running test sync...")
    
    # Configure for limited sync (50 emails)
    settings.RECORD_SYNC_CONFIG = {
        'historical_days': 0,
        'max_messages_per_record': 50,
        'batch_size': 50,
        'channels': {
            'email': {'enabled': True, 'historical_days': 0, 'max_messages': 50, 'batch_size': 50},
            'gmail': {'enabled': True, 'historical_days': 0, 'max_messages': 50, 'batch_size': 50}
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
        record_id=66,  # Saul
        trigger_reason='Test participant tracking improvements'
    )
    
    return result

def analyze_results():
    """Analyze participant tracking results"""
    print("\n📊 PARTICIPANT TRACKING ANALYSIS")
    print("="*70)
    
    # 1. Total participants
    total_participants = Participant.objects.count()
    print(f"\n✅ TOTAL PARTICIPANTS: {total_participants}")
    
    # 2. Participants with names
    with_names = Participant.objects.exclude(name='').count()
    print(f"✅ With names: {with_names}/{total_participants} ({with_names/total_participants*100:.1f}%)")
    
    # 3. Sample participants with names
    print(f"\n👤 SAMPLE PARTICIPANTS WITH NAMES:")
    for p in Participant.objects.exclude(name='')[:10]:
        print(f"  - {p.name}: {p.email or p.phone}")
    
    # 4. ConversationParticipant links
    conv_participants = ConversationParticipant.objects.all()
    conv_part_count = conv_participants.count()
    print(f"\n✅ CONVERSATION-PARTICIPANT LINKS: {conv_part_count}")
    
    # Check role distribution
    from django.db.models import Count
    role_counts = conv_participants.values('role').annotate(count=Count('id'))
    print(f"\n📧 ROLE DISTRIBUTION:")
    for role in role_counts:
        print(f"  - {role['role']}: {role['count']}")
    
    # 5. Messages with sender_participant
    messages_with_sender = Message.objects.exclude(sender_participant__isnull=True).count()
    total_messages = Message.objects.count()
    print(f"\n✅ MESSAGES WITH SENDER: {messages_with_sender}/{total_messages} ({messages_with_sender/total_messages*100:.1f}%)")
    
    # 6. Check specific conversation participants
    links = RecordCommunicationLink.objects.filter(record_id=66)
    if links.exists():
        sample_conv = links.first().conversation
        conv_parts = ConversationParticipant.objects.filter(conversation=sample_conv)
        print(f"\n📬 SAMPLE CONVERSATION PARTICIPANTS:")
        print(f"Conversation: {sample_conv.subject[:50]}...")
        for cp in conv_parts[:5]:
            print(f"  - {cp.participant.get_display_name()} ({cp.role})")

def main():
    """Main test function"""
    tenant_schema = 'oneotalent'
    
    print("\n" + "="*70)
    print("PARTICIPANT TRACKING TEST")
    print("="*70)
    print(f"Timestamp: {datetime.now()}")
    print(f"Tenant: {tenant_schema}")
    print("="*70)
    
    with schema_context(tenant_schema):
        try:
            # 1. Clear existing data
            clear_participant_data()
            
            # 2. Run sync
            result = run_test_sync()
            
            if result.get('success'):
                print(f"\n✓ Sync successful!")
                print(f"  - Conversations: {result.get('total_conversations', 0)}")
                print(f"  - Messages: {result.get('total_messages', 0)}")
            else:
                print(f"\n✗ Sync failed: {result.get('error')}")
                return
            
            # 3. Analyze results
            analyze_results()
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            logger.exception("Test failed")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()