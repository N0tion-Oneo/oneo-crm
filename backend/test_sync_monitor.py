#!/usr/bin/env python3
"""
Test WhatsApp sync and monitor logs
"""
import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
os.environ.setdefault('DJANGO_DEBUG', 'True')
django.setup()

from django_tenants.utils import schema_context
from communications.channels.whatsapp.sync.tasks import sync_account_comprehensive_background
from communications.models import Channel, UserChannelConnection, SyncJob
from tenants.models import User

def test_sync():
    """Test sync and monitor progress"""
    
    # Set connection to demo schema first
    from django.db import connection
    connection.set_schema('demo')
    
    # Use demo tenant
    with schema_context('demo'):
        # Get channel
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        if not channel:
            print("❌ No WhatsApp channel found")
            return
            
        print(f"✅ Found channel: {channel.id}")
        
        # Get connection
        connection = UserChannelConnection.objects.filter(
            channel_type='whatsapp',
            is_active=True
        ).first()
        
        if connection:
            print(f"✅ Found connection: {connection.unipile_account_id}")
        
        # Get user
        user = User.objects.first()
        if not user:
            print("❌ No user found")
            return
            
        print(f"✅ Found user: {user.email}")
        
        # Trigger sync directly (not via Celery)
        print("\n🚀 Starting sync task directly...")
        
        # Import and run directly
        from communications.channels.whatsapp.sync.comprehensive import ComprehensiveSyncService
        from communications.channels.whatsapp.sync.utils import SyncJobManager, SyncProgressTracker
        
        # Create sync job
        sync_job = SyncJobManager.create_sync_job(
            channel_id=str(channel.id),
            user_id=str(user.id),
            sync_type='comprehensive',
            options={
                'max_conversations': 2,
                'max_messages_per_chat': 3
            },
            task_id='manual_test_123'
        )
        
        print(f"✅ Created sync job: {sync_job.id}")
        print(f"   Celery task ID: {sync_job.celery_task_id}")
        
        # Run sync
        sync_service = ComprehensiveSyncService(
            channel=channel,
            connection=connection,
            sync_job=sync_job
        )
        
        print("\n📊 Running comprehensive sync...")
        stats = sync_service.run_comprehensive_sync({
            'max_conversations': 2,
            'max_messages_per_chat': 3
        })
        
        print(f"\n✅ Sync completed: {stats}")

if __name__ == '__main__':
    test_sync()