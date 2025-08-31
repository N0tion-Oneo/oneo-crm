#!/usr/bin/env python
"""
Test script to run a sync and verify all fields are properly populated
"""
import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from pipelines.models import Record
from communications.models import (
    UserChannelConnection, Conversation, Message, 
    Participant, ConversationParticipant, Channel,
    CommunicationAnalytics, TenantUniPileConfig
)
from communications.record_communications.models import (
    RecordCommunicationProfile, RecordSyncJob
)
from communications.record_communications.tasks.sync_tasks import sync_record_communications

User = get_user_model()


def check_field_population(schema_name='oneotalent'):
    """Check if fields are properly populated after sync"""
    
    print(f"\n{'='*60}")
    print("FIELD POPULATION VERIFICATION")
    print(f"{'='*60}\n")
    
    with schema_context(schema_name):
        # 1. Check TenantUniPileConfig fields
        print("1. TenantUniPileConfig Fields:")
        try:
            config = TenantUniPileConfig.objects.first()
            if config:
                print(f"   ✓ webhook_secret: {'Set' if config.webhook_secret else '❌ Not set'}")
                print(f"   ✓ provider_preferences: {'Set' if config.provider_preferences else '❌ Not set'}")
                print(f"   ✓ last_webhook_received: {config.last_webhook_received or '❌ Never'}")
                print(f"   ✓ webhook_failures: {config.webhook_failures}")
            else:
                print("   ❌ No TenantUniPileConfig found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. Check UserChannelConnection fields
        print("\n2. UserChannelConnection Fields:")
        connections = UserChannelConnection.objects.all()[:2]
        for conn in connections:
            print(f"   Connection: {conn.account_name}")
            print(f"   ✓ access_token: {'Encrypted' if conn.access_token else '❌ Not set'}")
            print(f"   ✓ token_expires_at: {conn.token_expires_at or '❌ Not set'}")
            print(f"   ✓ messages_sent_count: {conn.messages_sent_count}")
            print(f"   ✓ messages_sent_today: {conn.messages_sent_today}")
            print(f"   ✓ rate_limit_per_hour: {conn.rate_limit_per_hour}")
            print(f"   ✓ last_rate_limit_reset: {conn.last_rate_limit_reset or '❌ Not set'}")
            print()
        
        # 3. Check Channel fields
        print("3. Channel Fields:")
        channels = Channel.objects.all()[:2]
        for channel in channels:
            print(f"   Channel: {channel.id}")
            print(f"   ✓ message_count: {channel.message_count}")
            print(f"   ✓ last_message_at: {channel.last_message_at or '❌ Not set'}")
            print(f"   ✓ last_sync_at: {channel.last_sync_at or '❌ Not set'}")
            print(f"   ✓ sync_settings: {'Set' if channel.sync_settings else '❌ Not set'}")
            print()
        
        # 4. Check Conversation fields
        print("4. Conversation Fields:")
        conversations = Conversation.objects.all()[:2]
        for conv in conversations:
            print(f"   Conversation: {conv.subject or conv.id}")
            print(f"   ✓ conversation_type: {conv.conversation_type}")
            print(f"   ✓ participant_count: {conv.participant_count}")
            print(f"   ✓ priority: {conv.priority}")
            print(f"   ✓ is_hot: {conv.is_hot}")
            print(f"   ✓ sync_status: {conv.sync_status}")
            print(f"   ✓ sync_error_count: {conv.sync_error_count}")
            print(f"   ✓ last_accessed_at: {conv.last_accessed_at or '❌ Not set'}")
            print()
        
        # 5. Check Message fields
        print("5. Message Fields:")
        messages = Message.objects.all()[:2]
        for msg in messages:
            print(f"   Message: {msg.external_message_id[:20]}...")
            print(f"   ✓ sent_at: {msg.sent_at or '❌ Not set'}")
            print(f"   ✓ received_at: {msg.received_at or '❌ Not set'}")
            print(f"   ✓ subject: {msg.subject or '❌ Not set (OK for non-email)'}")
            print(f"   ✓ is_local_only: {msg.is_local_only}")
            print()
        
        # 6. Check Participant fields
        print("6. Participant Fields:")
        participants = Participant.objects.all()[:2]
        for part in participants:
            print(f"   Participant: {part.name or part.email or part.phone}")
            print(f"   ✓ resolution_method: {part.resolution_method or '❌ Not set'}")
            print(f"   ✓ resolved_at: {part.resolved_at or '❌ Not set'}")
            print(f"   ✓ resolution_confidence: {part.resolution_confidence}")
            print(f"   ✓ total_conversations: {part.total_conversations}")
            print(f"   ✓ total_messages: {part.total_messages}")
            print(f"   ✓ first_seen: {part.first_seen or '❌ Not set'}")
            print(f"   ✓ last_seen: {part.last_seen or '❌ Not set'}")
            print()
        
        # 7. Check ConversationParticipant fields
        print("7. ConversationParticipant Fields:")
        conv_parts = ConversationParticipant.objects.all()[:2]
        for cp in conv_parts:
            print(f"   ConvParticipant: {cp.id}")
            print(f"   ✓ message_count: {cp.message_count}")
            print(f"   ✓ last_message_at: {cp.last_message_at or '❌ Not set'}")
            print(f"   ✓ last_read_at: {cp.last_read_at or '❌ Not set'}")
            print(f"   ✓ unread_count: {cp.unread_count}")
            print(f"   ✓ left_at: {cp.left_at or 'Active'}")
            print()
        
        # 8. Check CommunicationAnalytics
        print("8. CommunicationAnalytics:")
        analytics = CommunicationAnalytics.objects.all()[:1]
        if analytics:
            for ana in analytics:
                print(f"   ✓ Date: {ana.date}")
                print(f"   ✓ messages_sent: {ana.messages_sent}")
                print(f"   ✓ messages_received: {ana.messages_received}")
                print(f"   ✓ response_rate: {ana.response_rate}%")
                print(f"   ✓ engagement_score: {ana.engagement_score}")
        else:
            print("   ❌ No analytics records found (will be created by scheduled task)")
        
        # 9. Check RecordSyncJob fields
        print("\n9. RecordSyncJob Fields:")
        sync_jobs = RecordSyncJob.objects.all()[:2]
        for job in sync_jobs:
            print(f"   Job: {job.id}")
            print(f"   ✓ trigger_reason: {job.trigger_reason or '❌ Not set'}")
            print(f"   ✓ triggered_by: {job.triggered_by or '❌ Not set'}")
            print(f"   ✓ accounts_synced: {job.accounts_synced}")
            print(f"   ✓ progress_percentage: {job.progress_percentage}%")
            print()


def run_test_sync(schema_name='oneotalent', record_id=None):
    """Run a test sync for a record"""
    
    print(f"\n{'='*60}")
    print("RUNNING TEST SYNC")
    print(f"{'='*60}\n")
    
    with schema_context(schema_name):
        # Get a record to sync
        if record_id:
            record = Record.objects.get(id=record_id)
        else:
            # Get first record with email or phone
            records = Record.objects.filter(
                data__email__isnull=False
            ) | Record.objects.filter(
                data__phone__isnull=False
            )
            record = records.first()
        
        if not record:
            print("❌ No suitable record found for sync")
            return
        
        print(f"Selected Record: {record.id}")
        print(f"  Pipeline: {record.pipeline.name if record.pipeline else 'Unknown'}")
        print(f"  Data: {record.data}")
        
        # Get a user to trigger the sync
        user = User.objects.filter(is_staff=True).first()
        
        # Run the sync synchronously for testing
        print("\nStarting sync...")
        
        try:
            # Call the task directly (not via Celery)
            # The task is bound, so first arg is self
            result = sync_record_communications(
                None,  # self (not needed when calling directly)
                record.id,  # record_id as positional arg
                tenant_schema=schema_name,
                triggered_by_id=user.id if user else None,
                trigger_reason='Test sync with field verification'
            )
            
            print("\nSync Result:")
            print(f"  Success: {result.get('success', False)}")
            print(f"  Total Conversations: {result.get('total_conversations', 0)}")
            print(f"  Total Messages: {result.get('total_messages', 0)}")
            
            if result.get('channel_results'):
                print("\nChannel Results:")
                for channel, data in result['channel_results'].items():
                    print(f"  {channel}: {data}")
            
            if not result.get('success'):
                print(f"  Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Sync failed with error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main function"""
    
    schema_name = input("Enter schema name (default: oneotalent): ").strip() or 'oneotalent'
    
    # First check existing field population
    print("\n" + "="*60)
    print("CHECKING EXISTING FIELD POPULATION")
    print("="*60)
    check_field_population(schema_name)
    
    # Ask if user wants to run a sync
    run_sync = input("\nRun a test sync? (y/n): ").strip().lower()
    
    if run_sync == 'y':
        record_id = input("Enter record ID (leave blank for auto-select): ").strip()
        record_id = int(record_id) if record_id else None
        
        # Run the sync
        run_test_sync(schema_name, record_id)
        
        # Check field population again
        print("\n" + "="*60)
        print("CHECKING FIELD POPULATION AFTER SYNC")
        print("="*60)
        check_field_population(schema_name)
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == '__main__':
    main()