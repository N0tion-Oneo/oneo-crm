#!/usr/bin/env python
"""
Test Celery task queuing
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.channels.whatsapp.sync.tasks import sync_account_comprehensive_background

# Test sending task to queue
print("🧪 Testing Celery task queuing...")

# Send task asynchronously
result = sync_account_comprehensive_background.delay(
    channel_id='8356e64e-21f7-4960-b75f-b4554ecc99c2',
    user_id='1',
    sync_options={
        'max_conversations': 5,
        'max_messages_per_chat': 10,
        'days_back': 7
    },
    tenant_schema='oneotalent'
)

print(f"✅ Task queued with ID: {result.id}")
print(f"📊 Task state: {result.state}")
print(f"🎯 Backend: {result.backend}")

# Wait a moment to check status
import time
time.sleep(2)
print(f"📊 Task state after 2s: {result.state}")

if result.ready():
    print(f"✅ Task completed with result: {result.result}")
else:
    print(f"⏳ Task still pending/running...")