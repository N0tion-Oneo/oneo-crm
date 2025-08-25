#!/usr/bin/env python
"""Test background sync with live monitoring"""
import os
import sys
import django
import time
import requests
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from communications.models import SyncJob, Channel, UserChannelConnection

User = get_user_model()

def get_auth_token():
    """Get authentication token for API requests"""
    login_url = "http://oneotalent.localhost:8000/auth/login/"
    login_data = {
        "email": "josh@oneodigital.com",
        "password": "admin123"
    }
    
    response = requests.post(login_url, json=login_data)
    if response.status_code == 200:
        data = response.json()
        return data.get('access')
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def start_background_sync(token):
    """Start a background sync via API"""
    sync_url = "http://oneotalent.localhost:8000/api/v1/communications/whatsapp/sync/background/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    sync_data = {
        "sync_options": {
            "days_back": 7,
            "max_messages_per_chat": 100,
            "conversations_per_batch": 10,
            "messages_per_batch": 50
        }
    }
    
    print("🚀 Starting background sync...")
    response = requests.post(sync_url, json=sync_data, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Sync started successfully!")
        print(f"   Response: {json.dumps(data, indent=2)}")
        return data
    else:
        print(f"❌ Failed to start sync: {response.status_code}")
        print(response.text)
        return None

def monitor_sync_progress(token, celery_task_id=None):
    """Monitor sync job progress"""
    print("\n📊 Monitoring sync progress...")
    
    # Get active sync jobs
    active_url = "http://oneotalent.localhost:8000/api/v1/communications/whatsapp/sync/jobs/active/"
    headers = {"Authorization": f"Bearer {token}"}
    
    start_time = time.time()
    timeout = 120  # 2 minutes timeout
    last_progress = {}
    
    while time.time() - start_time < timeout:
        try:
            # Check active jobs
            response = requests.get(active_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                active_jobs = data.get('active_sync_jobs', [])
                
                if active_jobs:
                    print(f"\n⏳ Active sync jobs: {len(active_jobs)}")
                    for job in active_jobs:
                        job_id = job.get('id')
                        status = job.get('status')
                        progress = job.get('progress', {})
                        completion = job.get('completion_percentage', 0)
                        
                        # Check if progress changed
                        job_key = str(job_id)
                        if job_key not in last_progress or last_progress[job_key] != progress:
                            print(f"\n📈 Job {job_id[:8]}...")
                            print(f"   Status: {status}")
                            print(f"   Completion: {completion}%")
                            print(f"   Phase: {progress.get('current_phase', 'unknown')}")
                            print(f"   Conversations: {progress.get('conversations_processed', 0)}/{progress.get('conversations_total', '?')}")
                            print(f"   Messages: {progress.get('messages_processed', 0)}")
                            last_progress[job_key] = progress.copy()
                else:
                    # Check completed jobs
                    all_jobs_url = "http://oneotalent.localhost:8000/api/v1/communications/whatsapp/sync/jobs/"
                    response = requests.get(all_jobs_url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        recent_jobs = data.get('sync_jobs', [])[:3]  # Get last 3 jobs
                        
                        if recent_jobs:
                            print("\n📋 Recent sync jobs:")
                            for job in recent_jobs:
                                status = job.get('status')
                                result = job.get('result_summary', {})
                                error = job.get('error_details', {})
                                
                                print(f"   Job {job.get('id', 'unknown')[:8]}... - {status}")
                                if status == 'completed':
                                    print(f"      ✅ Synced: {result.get('conversations_synced', 0)} chats, {result.get('messages_synced', 0)} messages")
                                elif status == 'failed':
                                    print(f"      ❌ Error: {error.get('error', 'Unknown error')}")
                            
                            # If we found completed jobs, we're done
                            if any(job.get('status') in ['completed', 'failed'] for job in recent_jobs):
                                print("\n✨ Sync finished!")
                                return
            
            # Also check via Django ORM
            with schema_context('oneotalent'):
                if celery_task_id:
                    sync_job = SyncJob.objects.filter(celery_task_id=celery_task_id).first()
                    if sync_job:
                        print(f"\n🔍 Direct DB check for task {celery_task_id[:8]}...")
                        print(f"   DB Status: {sync_job.status}")
                        print(f"   DB Progress: {sync_job.progress}")
                        if sync_job.status in ['completed', 'failed']:
                            print(f"\n✨ Sync {sync_job.status}!")
                            if sync_job.status == 'completed':
                                print(f"   Result: {sync_job.result_summary}")
                            else:
                                print(f"   Error: {sync_job.error_details}")
                            return
            
        except Exception as e:
            print(f"❌ Error checking progress: {e}")
        
        time.sleep(3)  # Check every 3 seconds
    
    print(f"\n⏱️ Monitoring timeout after {timeout} seconds")

def check_whatsapp_setup():
    """Check if WhatsApp is properly configured"""
    print("\n🔍 Checking WhatsApp setup...")
    
    with schema_context('oneotalent'):
        # Check user
        user = User.objects.filter(email='josh@oneodigital.com').first()
        if not user:
            print("❌ User josh@oneodigital.com not found")
            return False
        print(f"✅ User found: {user.email}")
        
        # Check connections
        connections = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp'
        )
        print(f"✅ WhatsApp connections: {connections.count()}")
        for conn in connections:
            print(f"   - {conn.unipile_account_id}: {conn.account_name} ({conn.auth_status})")
        
        # Check channels
        channels = Channel.objects.filter(channel_type='whatsapp')
        print(f"✅ WhatsApp channels: {channels.count()}")
        for channel in channels[:3]:
            print(f"   - {channel.id}: {channel.name}")
        
        return connections.exists() and channels.exists()

def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 WHATSAPP BACKGROUND SYNC TEST")
    print("=" * 60)
    
    # Check setup
    if not check_whatsapp_setup():
        print("❌ WhatsApp not properly configured")
        return
    
    # Get auth token
    print("\n🔐 Getting authentication token...")
    token = get_auth_token()
    if not token:
        print("❌ Failed to get auth token")
        return
    print("✅ Got auth token")
    
    # Start background sync
    sync_result = start_background_sync(token)
    if not sync_result:
        print("❌ Failed to start sync")
        return
    
    # Extract celery task ID
    celery_task_id = None
    sync_jobs = sync_result.get('sync_jobs', [])
    for job in sync_jobs:
        if job.get('status') == 'started':
            celery_task_id = job.get('celery_task_id')
            break
    
    if celery_task_id:
        print(f"\n📌 Celery Task ID: {celery_task_id}")
        print(f"   WebSocket channel: sync_progress_{celery_task_id}")
    
    # Monitor progress
    monitor_sync_progress(token, celery_task_id)
    
    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()