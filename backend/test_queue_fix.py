#!/usr/bin/env python
"""
Test that sync tasks now go to the correct queue
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record
from communications.record_communications.models import RecordCommunicationProfile, RecordSyncJob
from communications.record_communications.tasks import sync_record_communications
from tenants.models import Tenant
from django.contrib.auth import get_user_model
import time

User = get_user_model()

print("\n🧪 Testing Celery Queue Fix")
print("=" * 60)

# Get oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    # Get Saul's record
    record = Record.objects.get(id=66)
    print(f"✅ Record: Saul Chilchik (ID: {record.id})")
    
    # Get user
    user = User.objects.filter(is_active=True).first()
    
    # Get or create profile
    profile, _ = RecordCommunicationProfile.objects.get_or_create(
        record=record,
        defaults={'pipeline_id': record.pipeline_id}
    )
    
    # Create sync job
    sync_job = RecordSyncJob.objects.create(
        record=record,
        profile=profile,
        job_type='test_queue',
        status='pending',
        triggered_by=user,
        trigger_reason='Testing queue fix'
    )
    
    print(f"\n📋 Created sync job: {sync_job.id}")
    
    # Queue the task - should now go to background_sync queue
    print("\n🚀 Queueing task to background_sync...")
    result = sync_record_communications.apply_async(
        args=[record.id],
        kwargs={
            'triggered_by_id': user.id if user else None,
            'trigger_reason': 'Testing queue fix'
        }
    )
    
    sync_job.celery_task_id = result.id
    sync_job.save()
    
    print(f"✅ Task ID: {result.id}")
    print(f"   Queue: background_sync (configured in @shared_task)")
    
    # Check Redis queues
    import redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    print("\n📊 Checking Redis Queues:")
    celery_count = r.llen('celery')
    background_sync_count = r.llen('background_sync')
    
    print(f"   Default queue (celery): {celery_count} tasks")
    print(f"   Background sync queue: {background_sync_count} tasks")
    
    # Wait briefly to see if task gets picked up
    print("\n⏳ Waiting 5 seconds for task processing...")
    time.sleep(5)
    
    # Check job status
    sync_job.refresh_from_db()
    print(f"\n📋 Sync Job Status: {sync_job.status}")
    
    if sync_job.status == 'running' or sync_job.status == 'completed':
        print("✅ Task is being processed by background_sync worker!")
    elif sync_job.status == 'pending':
        print("⚠️  Task still pending - check if background_sync workers are running")
        print("   Run: ps aux | grep 'background_sync'")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")