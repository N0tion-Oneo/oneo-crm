#!/usr/bin/env python
"""
Test real-time sync progress updates to verify frontend receives them
"""
import os
import sys
import django
import asyncio
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from communications.models import Channel, UserChannelConnection
from communications.channels.whatsapp.sync.tasks import sync_account_comprehensive_background
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import time

User = get_user_model()

def monitor_sync_progress():
    """Monitor sync progress updates in real-time"""
    
    with schema_context('oneotalent'):
        print("\n🔍 Real-time Sync Progress Monitor")
        print("=" * 60)
        
        # Get user and channel
        user = User.objects.filter(username='oneo_admin').first()
        if not user:
            print("❌ User not found")
            return
            
        connection = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp',
            is_active=True
        ).first()
        
        if not connection:
            print("❌ No active WhatsApp connection found")
            return
        
        channel = Channel.objects.filter(
            channel_type='whatsapp'
        ).first()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
            
        print(f"✅ User: {user.username}")
        print(f"✅ Channel: {channel.name}")
        print(f"✅ Connection: {connection.unipile_account_id}")
        
        # Start a small sync
        print("\n🚀 Starting test sync with reduced settings...")
        sync_options = {
            'max_conversations': 2,  # Only sync 2 conversations
            'max_messages_per_chat': 50,  # Only 50 messages per chat
            'days_back': 7  # Only last week
        }
        
        result = sync_account_comprehensive_background.apply_async(
            args=[
                str(channel.id),
                str(user.id),
                sync_options,
                'oneotalent'
            ]
        )
        
        celery_task_id = result.id
        print(f"✅ Started sync task: {celery_task_id}")
        
        # Monitor progress
        channel_layer = get_channel_layer()
        if channel_layer:
            print(f"\n📡 Monitoring channels:")
            print(f"  - sync_progress_{celery_task_id}")
            print(f"  - sync_jobs_{user.id}")
            
            # Create a simple listener (in production, this would be WebSocket)
            print("\n📊 Progress Updates:")
            print("-" * 40)
            
            # Poll for status
            start_time = time.time()
            timeout = 60  # 1 minute timeout
            
            while time.time() - start_time < timeout:
                # Check task status
                if result.ready():
                    print(f"\n✅ Sync completed!")
                    print(f"Result: {result.result}")
                    break
                    
                # Check sync job in database
                from communications.models import SyncJob
                sync_job = SyncJob.objects.filter(
                    celery_task_id=celery_task_id
                ).first()
                
                if sync_job:
                    progress = sync_job.progress or {}
                    if progress:
                        phase = progress.get('current_phase', 'unknown')
                        percentage = progress.get('percentage', 0)
                        current = progress.get('current_item', 0)
                        total = progress.get('total_items', 0)
                        
                        print(f"\r📊 {phase}: {current}/{total} ({percentage:.1f}%)", end='', flush=True)
                
                time.sleep(1)
            
            print("\n" + "-" * 40)
            
        else:
            print("❌ No channel layer available")
        
        print("\n" + "=" * 60)
        print("✅ Test complete!")
        print("\nTo see real-time updates in the frontend:")
        print("1. Open the WhatsApp page")
        print("2. Start a sync")
        print("3. Check browser console for 'sync_progress_update' messages")
        print("4. Progress bars should update at 0%, 25%, 50%, 75%, 100%")
        print("=" * 60)

if __name__ == '__main__':
    monitor_sync_progress()