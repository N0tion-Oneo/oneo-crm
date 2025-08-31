#!/usr/bin/env python
"""
Performance test for email sync - Record 66 (Saul Chilchik)
This script tests the record sync system with 500 emails and comprehensive metrics.
"""

import os
import sys
import django
import logging
import time
from datetime import datetime
from collections import defaultdict

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Configure logging to be very verbose
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'email_sync_performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

# Set specific loggers to INFO level
logging.getLogger('communications.record_communications').setLevel(logging.INFO)
logging.getLogger('communications.unipile').setLevel(logging.INFO)
logging.getLogger('django.db.backends').setLevel(logging.WARNING)  # Reduce SQL noise

from django_tenants.utils import schema_context
from django.db import connection
from pipelines.models import Record
from communications.models import (
    UserChannelConnection, Message, Conversation, 
    Participant, ConversationParticipant
)
from communications.record_communications.models import (
    RecordCommunicationProfile, RecordCommunicationLink, 
    RecordSyncJob, RecordAttendeeMapping
)
from communications.record_communications.services.record_sync_orchestrator import RecordSyncOrchestrator
from communications.unipile.core.client import UnipileClient
from django.conf import settings

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Track timing and metrics for each phase of the sync"""
    
    def __init__(self):
        self.timings = {}
        self.metrics = defaultdict(int)
        self.phase_stack = []
        
    def start_phase(self, phase_name):
        """Start timing a phase"""
        start_time = time.time()
        self.phase_stack.append((phase_name, start_time))
        print(f"\n⏱️  Starting: {phase_name}")
        
    def end_phase(self, phase_name=None):
        """End timing a phase and record duration"""
        if not self.phase_stack:
            return
            
        name, start_time = self.phase_stack.pop()
        duration = time.time() - start_time
        
        if phase_name and phase_name != name:
            logger.warning(f"Phase mismatch: expected {phase_name}, got {name}")
            
        self.timings[name] = duration
        print(f"✅ Completed: {name} - {duration:.2f} seconds")
        return duration
        
    def add_metric(self, key, value):
        """Add a metric value"""
        self.metrics[key] = value
        
    def increment_metric(self, key, value=1):
        """Increment a metric counter"""
        self.metrics[key] += value
        
    def print_summary(self):
        """Print performance summary"""
        print("\n" + "="*80)
        print("PERFORMANCE SUMMARY")
        print("="*80)
        
        print("\n📊 Timing Breakdown:")
        total_time = sum(self.timings.values())
        for phase, duration in self.timings.items():
            percentage = (duration / total_time * 100) if total_time > 0 else 0
            print(f"  {phase:40} {duration:8.2f}s ({percentage:5.1f}%)")
        print(f"  {'TOTAL':40} {total_time:8.2f}s")
        
        print("\n📈 Metrics:")
        for key, value in sorted(self.metrics.items()):
            print(f"  {key:40} {value:,}")
            
        # Calculate rates
        if total_time > 0:
            messages_per_sec = self.metrics.get('total_messages', 0) / total_time
            print(f"\n⚡ Processing Rate: {messages_per_sec:.1f} messages/second")


def analyze_saved_data(record_id, tracker):
    """Analyze what data was saved and where"""
    
    print("\n" + "="*80)
    print("DATA STORAGE ANALYSIS")
    print("="*80)
    
    tracker.start_phase("Data Analysis")
    
    # 1. Communication Profile
    print("\n📁 RecordCommunicationProfile:")
    profile = RecordCommunicationProfile.objects.filter(record_id=record_id).first()
    if profile:
        print(f"  ✓ Profile ID: {profile.id}")
        print(f"  ✓ Identifiers: {profile.communication_identifiers}")
        print(f"  ✓ Total Messages: {profile.total_messages}")
        print(f"  ✓ Total Conversations: {profile.total_conversations}")
        print(f"  ✓ Last Sync: {profile.last_full_sync}")
        print(f"  ✓ Sync Status: {profile.sync_status}")
        tracker.add_metric('profile_exists', 1)
        tracker.add_metric('profile_total_messages', profile.total_messages)
        tracker.add_metric('profile_total_conversations', profile.total_conversations)
    
    # 2. Communication Links
    print("\n📁 RecordCommunicationLink:")
    links = RecordCommunicationLink.objects.filter(record_id=record_id)
    link_count = links.count()
    print(f"  ✓ Total Links: {link_count}")
    
    # Sample first 5 links
    for link in links[:5]:
        print(f"    - Link {link.id}: Conv {link.conversation_id} ({link.match_type}: {link.match_identifier})")
    if link_count > 5:
        print(f"    ... and {link_count - 5} more")
    tracker.add_metric('communication_links', link_count)
    
    # 3. Conversations
    print("\n📁 Conversations:")
    conv_ids = links.values_list('conversation_id', flat=True).distinct()
    conversations = Conversation.objects.filter(id__in=conv_ids)
    conv_count = conversations.count()
    print(f"  ✓ Total Conversations: {conv_count}")
    
    # Analyze conversation types
    conv_by_type = conversations.values('conversation_type').annotate(
        count=models.Count('id')
    )
    for conv_type in conv_by_type:
        print(f"    - {conv_type['conversation_type']}: {conv_type['count']}")
    tracker.add_metric('conversations_stored', conv_count)
    
    # 4. Messages
    print("\n📁 Messages:")
    messages = Message.objects.filter(conversation_id__in=conv_ids)
    msg_count = messages.count()
    print(f"  ✓ Total Messages: {msg_count}")
    
    # Analyze message distribution
    from django.db import models
    msg_stats = messages.aggregate(
        total=models.Count('id'),
        with_content=models.Count('id', filter=models.Q(content__isnull=False)),
        inbound=models.Count('id', filter=models.Q(direction='inbound')),
        outbound=models.Count('id', filter=models.Q(direction='outbound'))
    )
    print(f"    - With content: {msg_stats['with_content']}")
    print(f"    - Inbound: {msg_stats['inbound']}")
    print(f"    - Outbound: {msg_stats['outbound']}")
    tracker.add_metric('messages_stored', msg_count)
    tracker.add_metric('messages_with_content', msg_stats['with_content'])
    
    # 5. Participants
    print("\n📁 Participants:")
    participant_ids = set()
    
    # Get participants from messages
    msg_participants = messages.values_list('sender_participant_id', flat=True).distinct()
    participant_ids.update(msg_participants)
    
    # Get participants from conversation participants
    conv_participants = ConversationParticipant.objects.filter(
        conversation_id__in=conv_ids
    ).values_list('participant_id', flat=True).distinct()
    participant_ids.update(conv_participants)
    
    participants = Participant.objects.filter(id__in=participant_ids)
    part_count = participants.count()
    print(f"  ✓ Total Participants: {part_count}")
    
    # Sample participants
    for participant in participants[:5]:
        print(f"    - {participant.name or 'Unknown'}: {participant.email or participant.phone or 'No contact'}")
    if part_count > 5:
        print(f"    ... and {part_count - 5} more")
    tracker.add_metric('participants_stored', part_count)
    
    # 6. Sync Jobs
    print("\n📁 RecordSyncJob:")
    sync_jobs = RecordSyncJob.objects.filter(record_id=record_id).order_by('-created_at')
    job_count = sync_jobs.count()
    print(f"  ✓ Total Sync Jobs: {job_count}")
    
    # Show recent jobs
    for job in sync_jobs[:3]:
        print(f"    - Job {job.id}: {job.status} - {job.messages_found} messages, {job.conversations_found} conversations")
        if job.completed_at and job.started_at:
            duration = (job.completed_at - job.started_at).total_seconds()
            print(f"      Duration: {duration:.2f}s")
    tracker.add_metric('sync_jobs', job_count)
    
    # 7. Database table sizes (approximate)
    print("\n📊 Database Storage (estimated):")
    
    with connection.cursor() as cursor:
        # Get table sizes
        tables = [
            ('communications_message', 'Messages'),
            ('communications_conversation', 'Conversations'),
            ('communications_participant', 'Participants'),
            ('record_communications_recordcommunicationlink', 'Record Links'),
            ('record_communications_recordcommunicationprofile', 'Profiles'),
        ]
        
        for table_name, display_name in tables:
            try:
                cursor.execute(f"""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('{table_name}')) as size,
                        COUNT(*) as row_count
                    FROM {table_name}
                """)
                result = cursor.fetchone()
                if result:
                    print(f"    {display_name:30} {result[0]:>10} ({result[1]:,} rows)")
            except Exception as e:
                print(f"    {display_name:30} Unable to get size: {e}")
    
    tracker.end_phase("Data Analysis")


def test_email_sync_performance():
    """Test email sync performance for Saul Chilchik (Record 66 in oneotalent)"""
    
    # Use the oneotalent tenant
    tenant_schema = 'oneotalent'
    record_id = 66  # Saul is ID 66 in oneotalent tenant
    
    print("\n" + "="*80)
    print("EMAIL SYNC PERFORMANCE TEST - RECORD 66 (Saul Chilchik)")
    print("="*80)
    print(f"Timestamp: {datetime.now()}")
    print(f"Tenant: {tenant_schema}")
    print(f"Record ID: {record_id}")
    print(f"Target: 500 emails")
    print("="*80 + "\n")
    
    tracker = PerformanceTracker()
    
    with schema_context(tenant_schema):
        try:
            # PHASE 1: Setup and Verification
            tracker.start_phase("Setup and Verification")
            
            # Verify record exists
            record = Record.objects.get(id=record_id)
            print(f"✓ Found record: {record.data.get('first_name', '')} {record.data.get('last_name', '')}")
            
            # Check for email in record data
            email_fields = ['email', 'email_address', 'work_email', 'personal_email']
            found_emails = []
            
            for field in email_fields:
                if field in record.data and record.data[field]:
                    found_emails.append(record.data[field])
            
            print(f"✓ Found {len(found_emails)} email addresses: {found_emails}")
            tracker.add_metric('email_addresses_found', len(found_emails))
            
            # Check email connections
            email_connections = UserChannelConnection.objects.filter(
                channel_type__in=['email', 'gmail', 'outlook'],
                is_active=True,
                account_status='active'
            )
            
            print(f"✓ Found {email_connections.count()} active email connections")
            tracker.add_metric('email_connections', email_connections.count())
            
            if not email_connections:
                print("⚠ No active email connections found")
                return
            
            tracker.end_phase("Setup and Verification")
            
            # PHASE 2: Initialize UniPile
            tracker.start_phase("UniPile Initialization")
            
            if not settings.UNIPILE_SETTINGS.is_configured():
                print("✗ UniPile is not configured in environment")
                return
            
            unipile_client = UnipileClient(
                dsn=settings.UNIPILE_DSN,
                access_token=settings.UNIPILE_API_KEY
            )
            print(f"✓ UniPile client initialized")
            
            tracker.end_phase("UniPile Initialization")
            
            # PHASE 3: Configure and Run Sync
            tracker.start_phase("Email Sync Execution")
            
            print("\nSync Configuration:")
            print("  - Historical days: 0 (fetch all)")
            print("  - Max emails: 500")
            print("  - Batch size: 100")
            
            # Override sync config for testing with 500 emails
            # Set it in Django settings BEFORE creating the orchestrator
            settings.RECORD_SYNC_CONFIG = {
                'historical_days': 0,
                'max_messages_per_record': 500,
                'batch_size': 100,
                'channels': {
                    'email': {
                        'enabled': True,
                        'historical_days': 0,
                        'max_messages': 500,
                        'batch_size': 100
                    },
                    'gmail': {
                        'enabled': True,
                        'historical_days': 0,
                        'max_messages': 500,
                        'batch_size': 100
                    }
                }
            }
            
            # Force reload of config with our settings
            from communications.record_communications import utils
            utils._sync_config = None  # Reset global config
            
            # Now create orchestrator which will use the settings
            orchestrator = RecordSyncOrchestrator(unipile_client)
            
            # Clear any existing data for clean test
            print("\nClearing existing data for clean test...")
            RecordCommunicationLink.objects.filter(record_id=record_id).delete()
            RecordSyncJob.objects.filter(record_id=record_id).delete()
            
            # Run the sync
            print("\nStarting sync...")
            result = orchestrator.sync_record(
                record_id=record_id,
                trigger_reason='Performance test - 500 email sync'
            )
            
            tracker.end_phase("Email Sync Execution")
            
            # PHASE 4: Process Results
            tracker.start_phase("Result Processing")
            
            if result.get('success'):
                print("\n✓ SYNC SUCCESSFUL")
                tracker.add_metric('sync_success', 1)
                tracker.add_metric('total_conversations', result.get('total_conversations', 0))
                tracker.add_metric('total_messages', result.get('total_messages', 0))
                
                # Show channel-specific results
                channel_results = result.get('channel_results', {})
                if channel_results:
                    print("\nChannel breakdown:")
                    for channel, stats in channel_results.items():
                        if 'email' in channel.lower() or 'gmail' in channel.lower():
                            print(f"  - {channel}: {stats.get('messages', 0)} messages in {stats.get('conversations', 0)} conversations")
                            tracker.add_metric(f'{channel}_messages', stats.get('messages', 0))
                            tracker.add_metric(f'{channel}_conversations', stats.get('conversations', 0))
            else:
                print("\n✗ SYNC FAILED")
                print(f"Error: {result.get('error', 'Unknown error')}")
                tracker.add_metric('sync_success', 0)
            
            tracker.end_phase("Result Processing")
            
            # PHASE 5: Analyze Saved Data
            analyze_saved_data(record_id, tracker)
            
            # Print Performance Summary
            tracker.print_summary()
            
        except Record.DoesNotExist:
            print(f"✗ Record {record_id} not found in tenant {tenant_schema}")
        except Exception as e:
            print(f"✗ Error during sync: {e}")
            logger.exception("Detailed error:")
    
    print("\n" + "="*80)
    print("PERFORMANCE TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_email_sync_performance()