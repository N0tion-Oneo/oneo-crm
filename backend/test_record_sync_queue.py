#!/usr/bin/env python
"""
Test record-level communication sync with proper queue routing
"""
import os
import sys
import django
import redis
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Record
from communications.record_communications.models import RecordCommunicationProfile, RecordSyncJob
from communications.record_communications.tasks.sync_tasks import sync_record_communications
from tenants.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n🧪 Testing Record-Level Sync Queue Routing")
print("=" * 60)

# Connect to Redis to monitor queues
r = redis.Redis(host='localhost', port=6379, db=0)

# Check initial queue states
print("\n📊 Initial Queue States:")
celery_count = r.llen('celery')
background_sync_count = r.llen('background_sync')
print(f"   Default queue (celery): {celery_count} tasks")
print(f"   Background sync queue: {background_sync_count} tasks")

# Get oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    # Get Saul's record
    record = Record.objects.get(id=66)
    print(f"\n✅ Record: Saul Chilchik (ID: {record.id})")
    
    # Get user
    user = User.objects.filter(is_active=True).first()
    
    # Queue the sync task - should go to background_sync queue
    print("\n🚀 Queueing sync task...")
    result = sync_record_communications.apply_async(
        args=[record.id],
        kwargs={
            'triggered_by_id': user.id if user else None,
            'trigger_reason': 'Testing queue routing'
        }
    )
    
    print(f"✅ Task ID: {result.id}")
    print(f"   Routing: sync_record_communications -> background_sync queue")
    
    # Give it a moment to hit the queue
    time.sleep(1)
    
    # Check queue states after queueing
    print("\n📊 Queue States After Queueing:")
    celery_count_after = r.llen('celery')
    background_sync_count_after = r.llen('background_sync')
    
    print(f"   Default queue (celery): {celery_count_after} tasks (change: {celery_count_after - celery_count})")
    print(f"   Background sync queue: {background_sync_count_after} tasks (change: {background_sync_count_after - background_sync_count})")
    
    if background_sync_count_after > background_sync_count:
        print("\n✅ SUCCESS: Task correctly routed to background_sync queue!")
    elif celery_count_after > celery_count:
        print("\n❌ ERROR: Task incorrectly routed to default queue!")
        print("   Check celery.py task_routes configuration")
    else:
        print("\n⚠️  Task may have already been processed by worker")
        print("   Check if background_sync worker is running:")
        print("   ps aux | grep 'celery.*background_sync'")
    
    # Check if task is being processed
    print("\n⏳ Waiting 5 seconds to check task processing...")
    time.sleep(5)
    
    # Try to get the sync job status
    try:
        sync_job = RecordSyncJob.objects.filter(
            record=record
        ).order_by('-created_at').first()
        
        if sync_job:
            print(f"\n📋 Latest Sync Job:")
            print(f"   Status: {sync_job.status}")
            print(f"   Created: {sync_job.created_at}")
            if sync_job.status in ['running', 'completed']:
                print("   ✅ Task is being processed by background_sync worker!")
    except Exception as e:
        print(f"\n⚠️  Could not check sync job status: {e}")

print("\n" + "=" * 60)
print("✅ Queue routing test completed!")
print("\nTo monitor workers in real-time:")
print("   celery -A oneo_crm events")
print("\nTo check active tasks:")
print("   celery -A oneo_crm inspect active")