#!/usr/bin/env python
"""
Test WhatsApp Background Sync System
Tests the comprehensive background sync functionality for WhatsApp messages
"""
import os
import sys
import django
import asyncio
import json
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from communications.models import (
    Channel, UserChannelConnection, SyncJob, SyncJobType, 
    SyncJobStatus, Conversation, Message, ChatAttendee
)
# Import the actual background sync task
from communications.channels.whatsapp.background_sync import sync_account_comprehensive_background

User = get_user_model()


def setup_test_environment():
    """Setup test environment with a WhatsApp channel"""
    print("\n🔧 Setting up test environment...")
    
    # Use demo tenant for testing
    with schema_context('demo'):
        # Get or create test user
        user, created = User.objects.get_or_create(
            username='whatsapp_test_user',
            defaults={
                'email': 'whatsapp.test@demo.com',
                'first_name': 'WhatsApp',
                'last_name': 'Tester'
            }
        )
        if created:
            user.set_password('test123')
            user.save()
            print(f"✅ Created test user: {user.username}")
        else:
            print(f"✅ Using existing test user: {user.username}")
        
        # Create or get WhatsApp channel connection
        connection, created = UserChannelConnection.objects.get_or_create(
            user=user,
            channel_type='whatsapp',
            account_name='Test WhatsApp Account',
            defaults={
                'unipile_account_id': 'test_whatsapp_account_123',
                'auth_status': 'authenticated',
                'account_status': 'active',
                'is_active': True,
                'connection_config': {
                    'phone_number': '+1234567890',
                    'business_name': 'Test Business'
                }
            }
        )
        if created:
            print(f"✅ Created WhatsApp connection: {connection.account_name}")
        else:
            print(f"✅ Using existing WhatsApp connection: {connection.account_name}")
        
        # Create or get channel
        channel, created = Channel.objects.get_or_create(
            unipile_account_id=connection.unipile_account_id,
            channel_type='whatsapp',
            defaults={
                'name': connection.account_name,
                'auth_status': 'authenticated',
                'is_active': True,
                'created_by': user
            }
        )
        if created:
            print(f"✅ Created channel: {channel.name}")
        else:
            print(f"✅ Using existing channel: {channel.name}")
        
        return user, connection, channel


def test_sync_job_creation():
    """Test creating a background sync job"""
    print("\n📝 Testing sync job creation...")
    
    with schema_context('demo'):
        user, connection, channel = setup_test_environment()
        
        # Create a comprehensive sync job
        sync_job = SyncJob.objects.create(
            user=user,
            channel=channel,
            job_type=SyncJobType.COMPREHENSIVE,
            sync_options={
                'days_back': 30,
                'batch_size': 50,
                'include_media': True,
                'sync_attendees': True
            },
            status=SyncJobStatus.PENDING,
            progress={
                'conversations_total': 0,
                'conversations_processed': 0,
                'messages_total': 0,
                'messages_synced': 0,
                'attendees_synced': 0
            }
        )
        
        print(f"✅ Created sync job: {sync_job.id}")
        print(f"   Type: {sync_job.job_type}")
        print(f"   Status: {sync_job.status}")
        print(f"   Options: {json.dumps(sync_job.sync_options, indent=2)}")
        
        return sync_job


def test_sync_progress_update():
    """Test updating sync job progress"""
    print("\n📊 Testing sync progress updates...")
    
    with schema_context('demo'):
        sync_job = test_sync_job_creation()
        
        # Simulate progress updates
        print("\n🔄 Simulating progress updates...")
        
        # Update 1: Starting sync
        sync_job.status = SyncJobStatus.RUNNING
        sync_job.started_at = timezone.now()
        sync_job.update_progress(
            conversations_total=10,
            conversations_processed=0,
            messages_total=0,
            messages_synced=0,
            current_phase='fetching_conversations'
        )
        print(f"   Phase: Fetching conversations (0/10)")
        
        # Update 2: Processing conversations
        sync_job.update_progress(
            conversations_processed=3,
            messages_total=45,
            current_phase='processing_conversations'
        )
        print(f"   Phase: Processing conversations (3/10)")
        print(f"   Completion: {sync_job.completion_percentage}%")
        
        # Update 3: Syncing messages
        sync_job.update_progress(
            conversations_processed=5,
            messages_synced=20,
            current_phase='syncing_messages'
        )
        print(f"   Phase: Syncing messages (5/10 conversations, 20/45 messages)")
        print(f"   Completion: {sync_job.completion_percentage}%")
        
        # Update 4: Complete
        sync_job.update_progress(
            conversations_processed=10,
            messages_synced=45,
            attendees_synced=15,
            current_phase='completed'
        )
        sync_job.status = SyncJobStatus.COMPLETED
        sync_job.completed_at = timezone.now()
        sync_job.result_summary = {
            'conversations_synced': 10,
            'messages_synced': 45,
            'attendees_synced': 15,
            'errors': 0,
            'duration_seconds': 12.5
        }
        sync_job.save()
        
        print(f"   Phase: Completed")
        print(f"   Completion: {sync_job.completion_percentage}%")
        print(f"   Summary: {json.dumps(sync_job.result_summary, indent=2)}")
        
        return sync_job


def test_background_sync_task():
    """Test the background sync task creation"""
    print("\n🚀 Testing background sync task...")
    
    with schema_context('demo'):
        user, connection, channel = setup_test_environment()
        
        # Create a sync job for the task
        sync_job = SyncJob.objects.create(
            user=user,
            channel=channel,
            job_type=SyncJobType.COMPREHENSIVE,
            sync_options={
                'days_back': 7,
                'batch_size': 50,
                'include_media': True,
                'sync_attendees': True
            },
            status=SyncJobStatus.PENDING
        )
        
        print(f"✅ Created sync job: {sync_job.id}")
        print(f"   Status: {sync_job.status}")
        print(f"   Type: {sync_job.job_type}")
        
        # Note: We can't actually execute the Celery task in this test
        # without a running Celery worker, but we can verify the job was created
        print("\n📦 Sync job ready for background processing")
        print("   To execute, run: celery -A oneo_crm worker -l info")
        
        # Check for active jobs
        active_jobs = SyncJob.objects.filter(
            channel=channel,
            status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
        )
        print(f"\n📋 Active sync jobs for channel: {active_jobs.count()}")
        for job in active_jobs:
            print(f"   - Job {job.id}: {job.status} ({job.completion_percentage}%)")
        
        return sync_job


def test_mock_sync_execution():
    """Test sync execution with mock data"""
    print("\n🧪 Testing mock sync execution...")
    
    with schema_context('demo'):
        user, connection, channel = setup_test_environment()
        sync_job = test_sync_job_creation()
        
        # Mock sync execution
        print("\n📥 Simulating message sync...")
        
        # Create mock conversations and messages
        for i in range(3):
            # Create conversation
            conversation = Conversation.objects.create(
                channel=channel,
                external_thread_id=f'mock_chat_{i}',
                subject=f'Mock Chat {i + 1}',
                status='active',
                sync_status='synced',
                last_message_at=timezone.now(),
                metadata={
                    'is_mock': True,
                    'sync_job_id': str(sync_job.id)
                }
            )
            print(f"   Created conversation: {conversation.subject}")
            
            # Create attendee
            attendee = ChatAttendee.objects.create(
                channel=channel,
                external_attendee_id=f'mock_attendee_{i}',
                provider_id=f'mock_user_{i}@whatsapp',
                name=f'Mock User {i + 1}',
                metadata={'is_mock': True}
            )
            
            # Link attendee to conversation
            conversation.attendees.add(attendee)
            
            # Create messages
            for j in range(5):
                message = Message.objects.create(
                    channel=channel,
                    conversation=conversation,
                    external_message_id=f'mock_msg_{i}_{j}',
                    sender=attendee,
                    content=f'Mock message {j + 1} in chat {i + 1}',
                    direction='inbound' if j % 2 == 0 else 'outbound',
                    status='delivered',
                    created_at=timezone.now() - timedelta(hours=j),
                    metadata={
                        'is_mock': True,
                        'sync_job_id': str(sync_job.id)
                    }
                )
            
            # Update sync job progress
            sync_job.update_progress(
                conversations_processed=i + 1,
                messages_synced=(i + 1) * 5,
                attendees_synced=i + 1
            )
        
        # Complete the sync
        sync_job.status = SyncJobStatus.COMPLETED
        sync_job.completed_at = timezone.now()
        sync_job.save()
        
        print(f"\n✅ Mock sync completed:")
        print(f"   Conversations: {Conversation.objects.filter(channel=channel).count()}")
        print(f"   Messages: {Message.objects.filter(channel=channel).count()}")
        print(f"   Attendees: {ChatAttendee.objects.filter(channel=channel).count()}")
        
        return sync_job


def test_sync_job_queries():
    """Test querying sync jobs and their status"""
    print("\n🔍 Testing sync job queries...")
    
    with schema_context('demo'):
        user, connection, channel = setup_test_environment()
        
        # Get all sync jobs for the channel
        all_jobs = SyncJob.objects.filter(channel=channel).order_by('-created_at')
        print(f"\n📊 Total sync jobs for channel: {all_jobs.count()}")
        
        for job in all_jobs[:5]:  # Show last 5 jobs
            print(f"\n   Job ID: {job.id}")
            print(f"   Type: {job.job_type}")
            print(f"   Status: {job.status}")
            print(f"   Progress: {job.completion_percentage}%")
            print(f"   Created: {job.created_at}")
            
            if job.status == SyncJobStatus.COMPLETED and job.result_summary:
                print(f"   Results: {json.dumps(job.result_summary, indent=6)}")
        
        # Get active jobs
        active_jobs = SyncJob.objects.filter(
            channel=channel,
            status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
        )
        print(f"\n⚡ Active sync jobs: {active_jobs.count()}")
        
        # Get failed jobs
        failed_jobs = SyncJob.objects.filter(
            channel=channel,
            status=SyncJobStatus.FAILED
        )
        print(f"❌ Failed sync jobs: {failed_jobs.count()}")
        
        # Get completed jobs with stats
        completed_jobs = SyncJob.objects.filter(
            channel=channel,
            status=SyncJobStatus.COMPLETED
        )
        print(f"✅ Completed sync jobs: {completed_jobs.count()}")
        
        if completed_jobs.exists():
            # Calculate aggregate stats
            total_messages = 0
            total_conversations = 0
            for job in completed_jobs:
                if job.result_summary:
                    total_messages += job.result_summary.get('messages_synced', 0)
                    total_conversations += job.result_summary.get('conversations_synced', 0)
            
            print(f"\n📈 Aggregate Stats:")
            print(f"   Total messages synced: {total_messages}")
            print(f"   Total conversations synced: {total_conversations}")


def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    with schema_context('demo'):
        # Delete mock messages
        mock_messages = Message.objects.filter(metadata__is_mock=True)
        msg_count = mock_messages.count()
        mock_messages.delete()
        print(f"   Deleted {msg_count} mock messages")
        
        # Delete mock conversations
        mock_conversations = Conversation.objects.filter(metadata__is_mock=True)
        conv_count = mock_conversations.count()
        mock_conversations.delete()
        print(f"   Deleted {conv_count} mock conversations")
        
        # Delete mock attendees
        mock_attendees = ChatAttendee.objects.filter(metadata__is_mock=True)
        att_count = mock_attendees.count()
        mock_attendees.delete()
        print(f"   Deleted {att_count} mock attendees")
        
        print("✅ Cleanup complete")


def main():
    """Run all background sync tests"""
    print("=" * 60)
    print("WhatsApp Background Sync Test Suite")
    print("=" * 60)
    
    try:
        # Run tests
        test_sync_job_creation()
        test_sync_progress_update()
        test_background_sync_task()
        test_mock_sync_execution()
        test_sync_job_queries()
        
        print("\n" + "=" * 60)
        print("✅ All background sync tests completed successfully!")
        print("=" * 60)
        
        # Optional cleanup
        response = input("\n🧹 Clean up test data? (y/n): ")
        if response.lower() == 'y':
            cleanup_test_data()
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()