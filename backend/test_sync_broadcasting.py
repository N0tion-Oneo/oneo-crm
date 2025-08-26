#!/usr/bin/env python
"""
Test WebSocket sync progress broadcasting
"""
import os
import sys
import django
import time
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from communications.models import Channel, UserChannelConnection, SyncJob, SyncJobType
from communications.channels.whatsapp.sync.utils import SyncProgressTracker, SyncJobManager
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()

def test_sync_broadcasting():
    """Test that WebSocket broadcasting is working for sync progress"""
    
    # Use oneotalent tenant (we know it has data)
    with schema_context('oneotalent'):
        print("\n🧪 Testing Sync Progress WebSocket Broadcasting")
        print("=" * 60)
        
        # Get test user
        test_user = User.objects.filter(is_superuser=True).first()
        if not test_user:
            print("❌ No superuser found")
            return
        
        print(f"✅ Using test user: {test_user.username}")
        
        # Get or create test channel
        channel, created = Channel.objects.get_or_create(
            channel_type='whatsapp',
            defaults={
                'name': 'Test WhatsApp Channel',
                'auth_status': 'authenticated',
                'is_active': True,
                'created_by': test_user
            }
        )
        
        # Create a test sync job with celery_task_id (frontend needs this)
        celery_task_id = f"test-task-{int(time.time())}"
        sync_job = SyncJobManager.create_sync_job(
            channel_id=str(channel.id),
            user_id=str(test_user.id),
            sync_type=SyncJobType.COMPREHENSIVE,
            options={'max_conversations': 10, 'max_messages_per_chat': 100},
            task_id=celery_task_id
        )
        
        print(f"✅ Created sync job: {sync_job.id}")
        print(f"✅ Celery task ID: {celery_task_id}")
        
        # Initialize progress tracker with broadcaster
        tracker = SyncProgressTracker(sync_job, provider_type='whatsapp')
        
        # Get channel layer for monitoring
        channel_layer = get_channel_layer()
        
        print(f"\n📡 Broadcasting to channels:")
        print(f"   - sync_progress_{celery_task_id}")
        print(f"   - sync_jobs_{test_user.id}")
        print(f"   - sync_job_{sync_job.id}")
        print(f"   - sync_whatsapp_{test_user.id}")
        
        # Test conversation progress updates
        print("\n📱 Testing conversation progress broadcasting...")
        
        # Simulate sync progress
        phases = [
            ('conversations', 10, [
                (0, "Starting conversation sync"),
                (3, "Processing conversation 3 of 10"),
                (5, "Processing conversation 5 of 10"),
                (7, "Processing conversation 7 of 10"),
                (10, "Completed: 10 conversations")
            ]),
            ('messages', 100, [
                (0, "Starting message sync"),
                (25, "Processing message batch 1"),
                (50, "Processing message batch 2"),
                (75, "Processing message batch 3"),
                (100, "Completed: 100 messages")
            ])
        ]
        
        for phase, total, updates in phases:
            print(f"\n🔄 Phase: {phase}")
            
            for current, details in updates:
                # Update progress
                tracker.update_progress(current, total, phase, details)
                
                # Calculate percentage
                percentage = round((current / total) * 100) if total > 0 else 0
                print(f"   📊 Progress: {current}/{total} ({percentage}%) - {details}")
                
                # Small delay to simulate work
                time.sleep(0.5)
        
        # Test nested progress
        print("\n📨 Testing nested progress broadcasting...")
        tracker.update_nested_progress(
            parent_phase='conversations',
            parent_current=5,
            parent_total=10,
            child_phase='messages',
            child_current=50,
            child_total=100,
            details='Syncing messages for conversation 5'
        )
        time.sleep(0.5)
        
        # Test job completion
        print("\n🎯 Testing job completion broadcasting...")
        
        # Update stats
        tracker.increment_stat('conversations_synced', 10)
        tracker.increment_stat('messages_synced', 500)
        
        # Finalize with success
        tracker.finalize()
        
        print("\n✅ Broadcasting test completed!")
        print(f"📊 Final stats: {tracker.get_stats()}")
        
        # Clean up
        sync_job.delete()
        print("\n🧹 Test sync job cleaned up")
        
        print("\n" + "=" * 60)
        print("📡 To verify broadcasts were sent:")
        print("1. Check Django logs for broadcast messages")
        print("2. Connect a WebSocket client to the channels above")
        print("3. Run with a frontend connected to see real-time updates")
        print("=" * 60)

if __name__ == '__main__':
    test_sync_broadcasting()