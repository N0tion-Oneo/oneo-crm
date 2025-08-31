#!/usr/bin/env python
"""
Test record-level communication sync with proper tenant context
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

print("\n🧪 Testing Record-Level Sync with Tenant Context")
print("=" * 60)

# Get oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')
print(f"✅ Using tenant: {tenant.name} (schema: {tenant.schema_name})")

# Connect to Redis to monitor queues
r = redis.Redis(host='localhost', port=6379, db=0)

# Check initial queue states
print("\n📊 Initial Queue States:")
celery_count = r.llen('celery')
background_sync_count = r.llen('background_sync')
print(f"   Default queue (celery): {celery_count} tasks")
print(f"   Background sync queue: {background_sync_count} tasks")

with schema_context(tenant.schema_name):
    # Get Saul's record
    record = Record.objects.get(id=66)
    print(f"\n✅ Record: Saul Chilchik (ID: {record.id})")
    
    # Get user
    user = User.objects.filter(is_active=True).first()
    
    # Queue the sync task with tenant schema
    print("\n🚀 Queueing sync task with tenant context...")
    result = sync_record_communications.apply_async(
        args=[record.id],
        kwargs={
            'tenant_schema': tenant.schema_name,  # Pass tenant schema
            'triggered_by_id': user.id if user else None,
            'trigger_reason': 'Testing with tenant context'
        }
    )
    
    print(f"✅ Task ID: {result.id}")
    print(f"   Tenant: {tenant.schema_name}")
    print(f"   Record: {record.id}")
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
    else:
        print("\n⚠️  Task may have already been processed by worker")
    
    # Check if task is being processed
    print("\n⏳ Waiting 10 seconds for task processing...")
    time.sleep(10)
    
    # Check the sync job status
    sync_job = RecordSyncJob.objects.filter(
        record=record
    ).order_by('-created_at').first()
    
    if sync_job:
        print(f"\n📋 Latest Sync Job:")
        print(f"   Status: {sync_job.status}")
        print(f"   Created: {sync_job.created_at}")
        print(f"   Messages Found: {sync_job.messages_found}")
        print(f"   Conversations Found: {sync_job.conversations_found}")
        if sync_job.error_message:
            print(f"   Error: {sync_job.error_message}")
        
        if sync_job.status == 'completed':
            print("\n✅ SUCCESS: Task completed successfully with tenant context!")
        elif sync_job.status == 'running':
            print("\n⚠️  Task is still running...")
        elif sync_job.status == 'failed':
            print("\n❌ Task failed - check error message above")
        else:
            print(f"\n⚠️  Task in {sync_job.status} state")

print("\n" + "=" * 60)
print("✅ Tenant context test completed!")