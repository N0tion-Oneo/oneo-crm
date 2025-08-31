#!/usr/bin/env python
"""
Test that automatic sync actually executes and syncs communications
"""
import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from communications.record_communications.models import (
    RecordCommunicationProfile, RecordSyncJob, RecordCommunicationLink
)
from communications.models import Conversation, Message
from django.contrib.auth import get_user_model

User = get_user_model()

def test_sync_execution():
    """Test that the sync actually executes and links communications"""
    
    with schema_context('oneotalent'):
        print("\n" + "="*60)
        print("Testing Automatic Sync Execution")
        print("="*60)
        
        # Get test pipeline and user
        pipeline = Pipeline.objects.filter(slug='contacts').first()
        user = User.objects.filter(is_superuser=True).first()
        
        print(f"✅ Using pipeline: {pipeline.name}")
        print(f"✅ Using user: {user.email}")
        
        # Use Saul's email to get real communications
        saul_email = 'saul.chilchik@example.com'  # Replace with actual email
        
        # For testing, let's find a record with existing communications
        # Look for record 66 which is Saul
        existing_record = Record.objects.filter(id=66).first()
        
        if existing_record:
            print(f"\n✅ Found existing record: {existing_record.id}")
            print(f"   Data: {existing_record.data}")
            
            # Check profile
            profile = RecordCommunicationProfile.objects.filter(record=existing_record).first()
            if profile:
                print(f"\n📱 Communication Profile:")
                print(f"   - Identifiers: {profile.communication_identifiers}")
                print(f"   - Total conversations: {profile.total_conversations}")
                print(f"   - Total messages: {profile.total_messages}")
                print(f"   - Last sync: {profile.last_full_sync}")
                print(f"   - Sync in progress: {profile.sync_in_progress}")
            
            # Check sync jobs
            sync_jobs = RecordSyncJob.objects.filter(
                record=existing_record
            ).order_by('-created_at')[:5]
            
            if sync_jobs:
                print(f"\n📋 Recent Sync Jobs:")
                for job in sync_jobs:
                    print(f"   - {job.created_at}: {job.job_type} - {job.status}")
                    print(f"     Reason: {job.trigger_reason}")
                    if job.result_summary:
                        print(f"     Results: {job.result_summary}")
            
            # Check linked communications
            links = RecordCommunicationLink.objects.filter(
                record=existing_record
            ).select_related('conversation')[:10]
            
            if links:
                print(f"\n💬 Linked Communications (sample):")
                for link in links:
                    conv = link.conversation
                    print(f"   - {conv.channel.channel_type}: {conv.subject or 'No subject'}")
                    print(f"     Messages: {conv.messages.count()}, Last: {conv.last_message_at}")
        else:
            print("❌ Record 66 not found")
        
        # Create a new test record and wait for sync
        print("\n" + "-"*40)
        print("Creating new record to test sync")
        print("-"*40)
        
        test_record = Record.objects.create(
            pipeline=pipeline,
            data={
                'first_name': 'Auto',
                'last_name': 'Sync Test',
                'personal_email': 'test_sync@example.com',
                'phone_number': '+1234567890'
            },
            created_by=user,
            updated_by=user
        )
        
        print(f"✅ Created test record: {test_record.id}")
        
        # Check if sync job was created
        sync_job = RecordSyncJob.objects.filter(record=test_record).first()
        if sync_job:
            print(f"✅ Sync job created: {sync_job.id}")
            print(f"   Status: {sync_job.status}")
            print(f"   Type: {sync_job.job_type}")
            
            # Wait a bit for sync to process
            print("\n⏳ Waiting 5 seconds for sync to process...")
            time.sleep(5)
            
            # Refresh sync job status
            sync_job.refresh_from_db()
            print(f"   Updated status: {sync_job.status}")
            
            if sync_job.status == 'completed':
                print("✅ Sync completed successfully!")
                if sync_job.result_summary:
                    print(f"   Results: {sync_job.result_summary}")
            elif sync_job.status == 'failed':
                print("❌ Sync failed")
                if sync_job.error_message:
                    print(f"   Error: {sync_job.error_message}")
            else:
                print(f"⏳ Sync still {sync_job.status}")
        
        # Check for any linked communications
        links = RecordCommunicationLink.objects.filter(record=test_record)
        print(f"\n💬 Communications linked to test record: {links.count()}")
        
        # Cleanup
        test_record.delete()
        print("\n✅ Test record cleaned up")
        
        print("\n" + "="*60)
        print("Sync Execution Test Complete")
        print("="*60)

if __name__ == "__main__":
    test_sync_execution()