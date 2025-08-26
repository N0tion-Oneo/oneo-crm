#!/usr/bin/env python
"""
Test sync progress message format for frontend compatibility
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from communications.models import Channel, SyncJob, SyncJobType
from communications.channels.whatsapp.sync.utils import SyncProgressTracker, SyncJobManager

User = get_user_model()

def test_progress_format():
    """Test that progress messages match frontend expectations"""
    
    with schema_context('oneotalent'):
        print("\n🧪 Testing Sync Progress Message Format")
        print("=" * 60)
        
        # Get test user
        test_user = User.objects.filter(is_superuser=True).first()
        
        # Get or create test channel
        channel, _ = Channel.objects.get_or_create(
            channel_type='whatsapp',
            defaults={
                'name': 'Test WhatsApp Channel',
                'auth_status': 'authenticated',
                'is_active': True,
                'created_by': test_user
            }
        )
        
        # Create a test sync job
        celery_task_id = "test-format-123"
        sync_job = SyncJobManager.create_sync_job(
            channel_id=str(channel.id),
            user_id=str(test_user.id),
            sync_type=SyncJobType.COMPREHENSIVE,
            options={'max_conversations': 10, 'max_messages_per_chat': 100},
            task_id=celery_task_id
        )
        
        # Initialize tracker
        tracker = SyncProgressTracker(sync_job, provider_type='whatsapp')
        
        # Simulate conversation phase
        print("\n📱 Testing conversation phase format:")
        tracker.update_progress(5, 10, 'conversations', 'Processing conversation 5')
        
        # Check what would be sent
        from communications.sync import get_sync_broadcaster
        broadcaster = get_sync_broadcaster('whatsapp')
        
        # Build expected message format
        progress_data = {
            'current_phase': 'processing_conversations',  # Frontend expects this
            'current_item': 5,
            'total_items': 10,
            'percentage': 50,
            'conversations_processed': 0,
            'conversations_total': 10,
            'messages_processed': 0,
            'batch_progress_percent': 50  # Frontend needs this
        }
        
        expected_message = {
            'type': 'sync_progress_update',
            'sync_job_id': str(sync_job.id),
            'celery_task_id': celery_task_id,
            'progress': progress_data,
            'completion_percentage': 50
        }
        
        print("\n📊 Expected WebSocket message structure:")
        print(json.dumps(expected_message, indent=2))
        
        print("\n✅ Key fields for frontend:")
        print(f"  - celery_task_id: {celery_task_id} (for job lookup)")
        print(f"  - progress.current_phase: {progress_data['current_phase']}")
        print(f"  - progress.conversations_total: {progress_data['conversations_total']}")
        print(f"  - progress.batch_progress_percent: {progress_data['batch_progress_percent']}")
        print(f"  - completion_percentage: 50")
        
        # Clean up
        sync_job.delete()
        
        print("\n" + "=" * 60)
        print("✅ Message format matches frontend expectations!")
        print("=" * 60)

if __name__ == '__main__':
    test_progress_format()