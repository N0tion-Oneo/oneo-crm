#!/usr/bin/env python
"""Test sync job creation and WebSocket broadcasting"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from django.utils import timezone
from communications.models import (
    SyncJob, SyncJobStatus, SyncJobType, Channel
)
import uuid
import time

User = get_user_model()

def test_sync_job_creation():
    """Test creating a sync job and updating its progress"""
    
    # Use oneotalent tenant context
    with schema_context('oneotalent'):
        print("🔍 Testing in oneotalent tenant schema")
        
        # Get user and channel
        user = User.objects.filter(email='josh@oneodigital.com').first()
        if not user:
            print("❌ User not found")
            return
            
        print(f"✅ Found user: {user.email}")
        
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        if not channel:
            print("❌ No WhatsApp channel found")
            return
            
        print(f"✅ Found channel: {channel.id}")
        
        # Create a test sync job with a test Celery task ID
        test_celery_task_id = str(uuid.uuid4())
        print(f"📊 Creating sync job with Celery task ID: {test_celery_task_id}")
        
        sync_job = SyncJob.objects.create(
            user=user,
            channel=channel,
            job_type=SyncJobType.COMPREHENSIVE,
            status=SyncJobStatus.RUNNING,
            celery_task_id=test_celery_task_id,
            started_at=timezone.now(),
            sync_options={
                'test': True,
                'days_back': 7
            }
        )
        
        print(f"✅ Created sync job: {sync_job.id}")
        print(f"   Status: {sync_job.status}")
        print(f"   Celery Task ID: {sync_job.celery_task_id}")
        
        # Update progress to trigger signal
        print("\n📈 Updating progress...")
        time.sleep(1)
        
        sync_job.update_progress(
            conversations_total=100,
            conversations_processed=25,
            messages_processed=150,
            current_phase='testing'
        )
        
        print(f"✅ Progress updated:")
        print(f"   Progress data: {sync_job.progress}")
        print(f"   Completion: {sync_job.completion_percentage}%")
        
        # Update again
        time.sleep(1)
        sync_job.update_progress(
            conversations_processed=50,
            messages_processed=300
        )
        
        print(f"\n✅ Second progress update:")
        print(f"   Progress data: {sync_job.progress}")
        print(f"   Completion: {sync_job.completion_percentage}%")
        
        # Mark as completed
        time.sleep(1)
        sync_job.status = SyncJobStatus.COMPLETED
        sync_job.completed_at = timezone.now()
        sync_job.result_summary = {
            'conversations_synced': 100,
            'messages_synced': 500
        }
        sync_job.save()
        
        print(f"\n✅ Sync job completed:")
        print(f"   Status: {sync_job.status}")
        print(f"   Result: {sync_job.result_summary}")
        
        print(f"\n🎉 Test complete! Check frontend WebSocket console for:")
        print(f"   - sync_progress_{test_celery_task_id}")
        print(f"   - Look for 'sync_progress_update' messages")
        
        return test_celery_task_id

if __name__ == '__main__':
    task_id = test_sync_job_creation()
    if task_id:
        print(f"\n📌 Use this Celery task ID in frontend: {task_id}")
        print("   You can manually subscribe in browser console:")
        print(f"   subscribe('sync_progress_{task_id}', (msg) => console.log('Progress:', msg))")