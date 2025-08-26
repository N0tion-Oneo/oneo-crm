#!/usr/bin/env python3
"""
Debug WebSocket broadcasting
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.sync import get_sync_broadcaster

# Create a broadcaster
broadcaster = get_sync_broadcaster('whatsapp')

# Test data
sync_job_id = 'test_sync_123'
celery_task_id = 'celery_task_456'
user_id = 'user_789'

print("Testing WebSocket broadcasting...")
print(f"Channel layer available: {bool(broadcaster.channel_layer)}")

# Test 1: Initial broadcast with 0 counts
print("\n1. Broadcasting initial progress (all 0s):")
progress_data = {
    'current_phase': 'initializing',
    'conversations_processed': 0,
    'messages_processed': 0,
    'attendees_processed': 0,
}
broadcaster.broadcast_progress(
    sync_job_id=sync_job_id,
    celery_task_id=celery_task_id,
    user_id=user_id,
    progress_data=progress_data,
    force=True
)

# Test 2: Broadcast with some counts
print("\n2. Broadcasting with counts:")
progress_data = {
    'current_phase': 'processing_conversations',
    'conversations_processed': 5,
    'messages_processed': 0,
    'attendees_processed': 0,
}
broadcaster.broadcast_progress(
    sync_job_id=sync_job_id,
    celery_task_id=celery_task_id,
    user_id=user_id,
    progress_data=progress_data,
    force=True
)

# Test 3: Broadcast with all counts
print("\n3. Broadcasting with all counts:")
progress_data = {
    'current_phase': 'syncing_messages',
    'conversations_processed': 10,
    'messages_processed': 50,
    'attendees_processed': 15,
}
broadcaster.broadcast_progress(
    sync_job_id=sync_job_id,
    celery_task_id=celery_task_id,
    user_id=user_id,
    progress_data=progress_data,
    force=True
)

print("\n✅ Test complete - check logs for broadcast messages")