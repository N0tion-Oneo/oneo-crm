#!/usr/bin/env python
"""
Test sync progress tracking updates
"""
import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from communications.models import Channel, UserChannelConnection, SyncJob, SyncJobProgress
from communications.channels.whatsapp.sync.comprehensive import ComprehensiveSyncService
from communications.channels.whatsapp.sync.utils import SyncProgressTracker
from django_tenants.utils import schema_context

User = get_user_model()

def test_progress_tracking():
    """Test that progress tracking is working properly"""
    
    # Use demo tenant
    with schema_context('demo'):
        print("\n🧪 Testing Sync Progress Tracking")
        print("=" * 50)
        
        # Create test sync job
        test_user = User.objects.filter(is_superuser=True).first()
        if not test_user:
            print("❌ No superuser found")
            return
        
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
        
        # Create sync job
        sync_job = SyncJob.objects.create(
            channel=channel,
            user=test_user,
            job_type='comprehensive',
            status='pending'
        )
        
        print(f"✅ Created test sync job: {sync_job.id}")
        
        # Test progress tracker
        tracker = SyncProgressTracker(sync_job)
        
        # Test conversation progress
        print("\n📱 Testing conversation progress updates...")
        tracker.update_progress(0, 10, 'conversations', 'Starting conversation sync')
        tracker.update_progress(3, 10, 'conversations', 'Processing conversation 3 of 10')
        tracker.update_progress(7, 10, 'conversations', 'Processing conversation 7 of 10')
        tracker.update_progress(10, 10, 'conversations', 'Completed: 10 conversations')
        
        # Test message progress
        print("\n📨 Testing message progress updates...")
        tracker.update_progress(0, 100, 'messages', 'Starting message sync')
        tracker.update_progress(25, 100, 'messages', 'Processing message 25 of 100')
        tracker.update_progress(50, 100, 'messages', 'Processing message 50 of 100')
        tracker.update_progress(75, 100, 'messages', 'Processing message 75 of 100')
        tracker.update_progress(100, 100, 'messages', 'Completed: 100 messages')
        
        # Check progress entries
        progress_entries = SyncJobProgress.objects.filter(sync_job=sync_job).order_by('created_at')
        
        print(f"\n📊 Progress entries created: {progress_entries.count()}")
        for entry in progress_entries:
            percentage = entry.completion_percentage
            print(f"  - {entry.phase_name}: {entry.items_processed}/{entry.items_total} ({percentage}%) - {entry.step_name}")
        
        # Check sync job progress field
        sync_job.refresh_from_db()
        if sync_job.progress:
            print(f"\n📈 Sync job progress data:")
            print(f"  - Current phase: {sync_job.progress.get('current_phase')}")
            print(f"  - Percentage: {sync_job.progress.get('percentage')}%")
            print(f"  - Last update: {sync_job.progress.get('last_update')}")
        
        # Cleanup
        sync_job.delete()
        print("\n✅ Progress tracking test completed!")

if __name__ == '__main__':
    test_progress_tracking()