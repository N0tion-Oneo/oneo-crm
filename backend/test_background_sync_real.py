#!/usr/bin/env python
"""
Test real background sync via API endpoint
"""
import os
import sys
import django
import json
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from tenants.models import Tenant
from django.db import connection as db_connection
from communications.models import SyncJob, Conversation, Message, ConversationAttendee

User = get_user_model()

def test_background_sync():
    """Test background sync through API endpoint"""
    print("=" * 60)
    print("Testing Background Sync via API")
    print("=" * 60)
    
    # Set tenant context
    tenant = Tenant.objects.get(schema_name='oneotalent')
    db_connection.set_tenant(tenant)
    print(f"\n✅ Set tenant context: {tenant.name}")
    
    # Get user
    user = User.objects.filter(email='josh@oneodigital.com').first()
    if not user:
        print("❌ User not found")
        return
    print(f"✅ Found user: {user.email}")
    
    # Create JWT token
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    # Create API client
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    # Get initial counts
    initial_conversations = Conversation.objects.count()
    initial_messages = Message.objects.count()
    initial_attendees = ConversationAttendee.objects.count()
    
    print(f"\n📊 Initial data counts:")
    print(f"   Conversations: {initial_conversations}")
    print(f"   Messages: {initial_messages}")
    print(f"   Attendees: {initial_attendees}")
    
    # Clear any existing sync jobs
    SyncJob.objects.filter(status__in=['pending', 'running']).update(status='cancelled')
    print(f"\n🧹 Cleared existing sync jobs")
    
    print(f"\n🚀 Starting background sync via API...")
    print(f"   Endpoint: /communications/whatsapp/background-sync/start/")
    
    # Call the background sync endpoint
    response = client.post(
        'http://oneotalent.localhost:8000/communications/whatsapp/background-sync/start/',
        {
            'sync_options': {
                'days_back': 30,
                'max_messages_per_chat': 100,  # Using safe limit
                'max_conversations': 50
            }
        },
        format='json',
        HTTP_HOST='oneotalent.localhost'
    )
    
    print(f"\n📡 API Response:")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Success: {data.get('success')}")
        print(f"   Message: {data.get('message')}")
        
        sync_jobs = data.get('sync_jobs', [])
        if sync_jobs:
            print(f"\n📋 Sync Jobs Created:")
            for job in sync_jobs:
                print(f"   - Channel ID: {job.get('channel_id')}")
                print(f"     Task ID: {job.get('celery_task_id', 'N/A')}")
                print(f"     Status: {job.get('status')}")
                print(f"     Message: {job.get('message')}")
                
                # Get the task ID for monitoring
                task_id = job.get('celery_task_id')
                
                if task_id and job.get('status') == 'started':
                    print(f"\n⏳ Waiting for Celery task {task_id} to complete...")
                    print(f"   Note: Make sure Celery worker is running:")
                    print(f"   celery -A oneo_crm worker -l info")
                    
                    # Monitor the sync job
                    channel_id = job.get('channel_id')
                    if channel_id:
                        # Poll for job completion (max 30 seconds)
                        for i in range(30):
                            time.sleep(1)
                            
                            # Check sync job status
                            sync_job = SyncJob.objects.filter(
                                channel_id=channel_id,
                                celery_task_id=task_id
                            ).first()
                            
                            if sync_job:
                                if sync_job.status == 'completed':
                                    print(f"\n✅ Sync completed!")
                                    print(f"   Duration: {(sync_job.completed_at - sync_job.started_at).total_seconds():.1f}s")
                                    
                                    # Show results
                                    if sync_job.result_summary:
                                        print(f"\n📊 Sync Results:")
                                        for key, value in sync_job.result_summary.items():
                                            print(f"   {key}: {value}")
                                    break
                                elif sync_job.status == 'failed':
                                    print(f"\n❌ Sync failed!")
                                    if sync_job.error_details:
                                        print(f"   Error: {sync_job.error_details}")
                                    break
                                elif i % 5 == 0:
                                    print(f"   Still running... ({i}s)")
                                    if sync_job.progress:
                                        prog = sync_job.progress
                                        print(f"   Progress: {prog}")
                        else:
                            print(f"\n⏱️ Timeout waiting for sync to complete (30s)")
                            print(f"   The sync may still be running in the background")
        
        # Get final counts
        final_conversations = Conversation.objects.count()
        final_messages = Message.objects.count()
        final_attendees = Attendee.objects.count()
        
        print(f"\n📊 Final data counts:")
        print(f"   Conversations: {final_conversations} (+{final_conversations - initial_conversations})")
        print(f"   Messages: {final_messages} (+{final_messages - initial_messages})")
        print(f"   Attendees: {final_attendees} (+{final_attendees - initial_attendees})")
        
    else:
        print(f"   ❌ Error: {response.status_code}")
        if hasattr(response, 'json'):
            try:
                error_data = response.json()
                print(f"   Details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Response: {response.content}")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == "__main__":
    test_background_sync()