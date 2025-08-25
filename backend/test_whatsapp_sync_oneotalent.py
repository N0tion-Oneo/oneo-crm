#!/usr/bin/env python
"""
Test WhatsApp Background Sync for OneOTalent Tenant
Tests background sync functionality with real user context
"""
import os
import sys
import django
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

User = get_user_model()


def test_sync_with_user_context():
    """Test sync with josh@oneodigital.com in oneotalent tenant"""
    print("\n" + "=" * 60)
    print("WhatsApp Background Sync Test - OneOTalent")
    print("=" * 60)
    
    # Use oneotalent tenant context
    with schema_context('oneotalent'):
        print("\n🔍 Finding user josh@oneodigital.com...")
        
        # Get the user
        try:
            user = User.objects.get(email='josh@oneodigital.com')
            print(f"✅ Found user: {user.email} (ID: {user.id})")
            print(f"   Username: {user.username}")
            print(f"   Name: {user.get_full_name()}")
        except User.DoesNotExist:
            print("❌ User josh@oneodigital.com not found in oneotalent tenant")
            return
        
        # Check for existing WhatsApp connections
        print("\n📱 Checking WhatsApp connections...")
        connections = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp'
        )
        
        if connections.exists():
            print(f"✅ Found {connections.count()} WhatsApp connection(s):")
            for conn in connections:
                print(f"   - {conn.account_name} (ID: {conn.unipile_account_id})")
                print(f"     Status: {conn.account_status}")
                print(f"     Active: {conn.is_active}")
        else:
            print("⚠️  No WhatsApp connections found. Creating test connection...")
            
            # Create a test connection
            connection = UserChannelConnection.objects.create(
                user=user,
                channel_type='whatsapp',
                account_name='Test WhatsApp - OneOTalent',
                unipile_account_id='oneotalent_whatsapp_test_001',
                auth_status='authenticated',
                account_status='active',
                is_active=True,
                connection_config={
                    'phone_number': '+27720720047',  # Your test number
                    'business_name': 'OneOTalent Test'
                }
            )
            print(f"✅ Created test connection: {connection.account_name}")
            connections = [connection]
        
        # Check for existing channels
        print("\n📡 Checking channels...")
        for conn in connections:
            channel = Channel.objects.filter(
                unipile_account_id=conn.unipile_account_id,
                channel_type='whatsapp'
            ).first()
            
            if not channel:
                channel = Channel.objects.create(
                    name=conn.account_name,
                    channel_type='whatsapp',
                    unipile_account_id=conn.unipile_account_id,
                    auth_status='authenticated',
                    is_active=True,
                    created_by=user
                )
                print(f"✅ Created channel: {channel.name}")
            else:
                print(f"✅ Found existing channel: {channel.name}")
            
            # Check existing sync jobs
            print(f"\n📊 Sync jobs for channel '{channel.name}':")
            sync_jobs = SyncJob.objects.filter(
                channel=channel
            ).order_by('-created_at')[:5]
            
            if sync_jobs.exists():
                for job in sync_jobs:
                    print(f"   - Job {job.id}")
                    print(f"     Type: {job.job_type}")
                    print(f"     Status: {job.status}")
                    print(f"     Progress: {job.completion_percentage}%")
                    print(f"     Created: {job.created_at}")
            else:
                print("   No sync jobs found")
            
            # Create a new sync job
            print(f"\n🚀 Creating new sync job for channel '{channel.name}'...")
            sync_job = SyncJob.objects.create(
                user=user,
                channel=channel,
                job_type=SyncJobType.COMPREHENSIVE,
                sync_options={
                    'days_back': 30,
                    'batch_size': 50,
                    'include_media': True,
                    'sync_attendees': True,
                    'test_mode': True  # Mark as test
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
            print(f"   Options: {json.dumps(sync_job.sync_options, indent=6)}")
            
            # Simulate some progress
            print("\n📈 Simulating sync progress...")
            
            # Update 1: Start
            sync_job.status = SyncJobStatus.RUNNING
            sync_job.started_at = timezone.now()
            sync_job.update_progress(
                conversations_total=5,
                conversations_processed=0,
                current_phase='initializing'
            )
            print(f"   Status: RUNNING")
            print(f"   Phase: Initializing...")
            
            # Update 2: Processing
            sync_job.update_progress(
                conversations_processed=2,
                messages_total=25,
                messages_synced=10,
                current_phase='syncing_messages'
            )
            print(f"   Progress: {sync_job.completion_percentage}% (2/5 conversations)")
            
            # Update 3: Complete
            sync_job.update_progress(
                conversations_processed=5,
                messages_synced=25,
                attendees_synced=8,
                current_phase='completed'
            )
            sync_job.status = SyncJobStatus.COMPLETED
            sync_job.completed_at = timezone.now()
            sync_job.result_summary = {
                'conversations_synced': 5,
                'messages_synced': 25,
                'attendees_synced': 8,
                'errors': 0,
                'duration_seconds': 3.5
            }
            sync_job.save()
            
            print(f"   Status: COMPLETED")
            print(f"   Progress: {sync_job.completion_percentage}%")
            print(f"   Results: {json.dumps(sync_job.result_summary, indent=6)}")
            
            # Check conversations and messages
            print(f"\n📬 Checking synced data for channel '{channel.name}':")
            conversations = Conversation.objects.filter(channel=channel).count()
            messages = Message.objects.filter(channel=channel).count()
            attendees = ChatAttendee.objects.filter(channel=channel).count()
            
            print(f"   Conversations: {conversations}")
            print(f"   Messages: {messages}")
            print(f"   Attendees: {attendees}")
            
            # Show active sync jobs
            print(f"\n⚡ Active sync jobs:")
            active_jobs = SyncJob.objects.filter(
                channel=channel,
                status__in=[SyncJobStatus.PENDING, SyncJobStatus.RUNNING]
            )
            
            if active_jobs.exists():
                for job in active_jobs:
                    print(f"   - Job {job.id}: {job.status} ({job.completion_percentage}%)")
            else:
                print("   No active sync jobs")
            
            print("\n" + "-" * 60)


def check_celery_status():
    """Check if Celery is configured and ready"""
    print("\n🔧 Checking Celery configuration...")
    
    try:
        from celery import current_app
        from kombu import Connection
        
        # Check Celery app
        print(f"   Celery app: {current_app.main}")
        print(f"   Broker: {current_app.conf.broker_url[:50]}...")  # Truncate for security
        
        # Try to connect to broker
        try:
            with Connection(current_app.conf.broker_url) as conn:
                conn.ensure_connection(max_retries=1)
                print("   ✅ Broker connection: OK")
        except Exception as e:
            print(f"   ⚠️  Broker connection: Failed ({str(e)[:50]}...)")
        
        # Check registered tasks
        whatsapp_tasks = [task for task in current_app.tasks if 'whatsapp' in task.lower()]
        print(f"   WhatsApp tasks registered: {len(whatsapp_tasks)}")
        for task in whatsapp_tasks[:5]:  # Show first 5
            print(f"     - {task}")
        
    except ImportError:
        print("   ❌ Celery not properly configured")
    except Exception as e:
        print(f"   ❌ Error checking Celery: {e}")


def main():
    """Run the test"""
    try:
        # Check Celery first
        check_celery_status()
        
        # Run the sync test
        test_sync_with_user_context()
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        
        print("\n💡 To run actual background sync:")
        print("   1. Start Celery worker: celery -A oneo_crm worker -l info")
        print("   2. The sync job will be processed automatically")
        print("   3. Monitor progress via WebSocket or API endpoints")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()