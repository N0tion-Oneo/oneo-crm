#!/usr/bin/env python
"""Test real background sync with UniPile data"""
import os
import sys
import django
import time
import requests

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import SyncJob, Channel
from communications.channels.whatsapp.background_sync import sync_account_comprehensive_background

def test_real_sync():
    """Test real sync with UniPile API"""
    
    print("=" * 60)
    print("🚀 TESTING REAL WHATSAPP SYNC WITH UNIPILE")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        # Get the WhatsApp channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No WhatsApp channel found")
            return
        
        print(f"✅ Found channel: {channel.name} ({channel.id})")
        print(f"   UniPile Account: {channel.unipile_account_id}")
        
        # Trigger sync with minimal data for testing
        sync_options = {
            'days_back': 7,  # Only sync last 7 days
            'max_messages_per_chat': 2,  # Very limited for quick attendee testing
            'conversations_per_batch': 5,  # Just 5 conversations to test attendees
            'messages_per_batch': 2
        }
        
        print(f"\n📋 Sync options:")
        print(f"   Days back: {sync_options['days_back']}")
        print(f"   Max messages per chat: {sync_options['max_messages_per_chat']}")
        
        print("\n🚀 Starting background sync...")
        
        # Call the sync task directly
        result = sync_account_comprehensive_background.delay(
            channel_id=str(channel.id),
            user_id='1',  # Admin user
            sync_options=sync_options,
            tenant_schema='oneotalent'
        )
        
        print(f"✅ Sync task queued: {result.id}")
        
        # Monitor the sync job
        print("\n📊 Monitoring sync progress...")
        
        start_time = time.time()
        last_status = None
        last_progress = {}
        
        while time.time() - start_time < 60:  # Monitor for up to 60 seconds
            # Check sync job status
            sync_job = SyncJob.objects.filter(celery_task_id=result.id).first()
            
            if sync_job:
                current_status = sync_job.status
                current_progress = sync_job.progress
                
                # Print updates when status or progress changes
                if current_status != last_status or current_progress != last_progress:
                    print(f"\n⏱️ Time: {int(time.time() - start_time)}s")
                    print(f"   Status: {current_status}")
                    
                    if current_progress:
                        phase = current_progress.get('current_phase', 'unknown')
                        convs = current_progress.get('conversations_processed', 0)
                        msgs = current_progress.get('messages_processed', 0)
                        print(f"   Phase: {phase}")
                        print(f"   Conversations: {convs}")
                        print(f"   Messages: {msgs}")
                    
                    last_status = current_status
                    last_progress = current_progress.copy()
                
                # Check if completed
                if current_status in ['completed', 'failed']:
                    print(f"\n{'✅' if current_status == 'completed' else '❌'} Sync {current_status}!")
                    
                    if current_status == 'completed':
                        result_summary = sync_job.result_summary or {}
                        print(f"   Conversations synced: {result_summary.get('conversations_synced', 0)}")
                        print(f"   Messages synced: {result_summary.get('messages_synced', 0)}")
                        print(f"   Duration: {result_summary.get('duration_seconds', 0):.2f}s")
                    else:
                        error_details = sync_job.error_details or {}
                        print(f"   Error: {error_details.get('error', 'Unknown error')}")
                    
                    break
            
            time.sleep(2)  # Check every 2 seconds
        
        print("\n" + "=" * 60)
        print("✅ Test complete!")
        print("=" * 60)

if __name__ == '__main__':
    test_real_sync()