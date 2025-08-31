#!/usr/bin/env python
"""
Test automatic record communication sync triggers
Tests that sync is triggered when identifier fields are added or updated
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
from duplicates.models import DuplicateRule
from communications.record_communications.models import RecordCommunicationProfile, RecordSyncJob
from communications.record_communications.signals import get_identifier_fields_from_duplicate_rules
from django.contrib.auth import get_user_model

User = get_user_model()

def test_automatic_sync_triggers():
    """Test that record communication sync triggers automatically"""
    
    with schema_context('oneotalent'):
        print("\n" + "="*60)
        print("Testing Automatic Record Communication Sync Triggers")
        print("="*60)
        
        # Get test pipeline
        pipeline = Pipeline.objects.filter(slug='contacts').first()
        if not pipeline:
            print("❌ Contacts pipeline not found in test tenant")
            return
        
        print(f"✅ Using pipeline: {pipeline.name}")
        
        # Get identifier fields from duplicate rules
        identifier_fields = get_identifier_fields_from_duplicate_rules(pipeline)
        print(f"📋 Identifier fields from duplicate rules: {identifier_fields}")
        
        if not identifier_fields:
            print("⚠️  No identifier fields defined in duplicate rules")
            # Check if there are any duplicate rules
            rules = DuplicateRule.objects.filter(pipeline=pipeline)
            print(f"   Found {rules.count()} duplicate rules for pipeline")
            for rule in rules:
                print(f"   - {rule.name}: {rule.logic}")
            return
        
        # Get test user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ No superuser found for testing")
            return
        
        print(f"✅ Using user: {user.email}")
        
        # Test 1: Create new record with identifier
        print("\n" + "-"*40)
        print("Test 1: Create record with identifier")
        print("-"*40)
        
        # Clear any existing sync jobs for clean test
        RecordSyncJob.objects.all().delete()
        
        test_email = f"test_{int(time.time())}@example.com"
        test_record = Record.objects.create(
            pipeline=pipeline,
            data={
                'first_name': 'Test',
                'last_name': 'User',
                'personal_email': test_email,  # This should be an identifier field
            },
            created_by=user,
            updated_by=user  # Required field
        )
        
        print(f"✅ Created record {test_record.id} with email: {test_email}")
        
        # Check if sync was triggered
        time.sleep(1)  # Give signals time to process
        
        sync_jobs = RecordSyncJob.objects.filter(record=test_record)
        if sync_jobs.exists():
            sync_job = sync_jobs.first()
            print(f"✅ Sync job created automatically!")
            print(f"   - Job ID: {sync_job.id}")
            print(f"   - Type: {sync_job.job_type}")
            print(f"   - Status: {sync_job.status}")
            print(f"   - Reason: {sync_job.trigger_reason}")
            print(f"   - Celery Task: {sync_job.celery_task_id}")
            if sync_job.metadata:
                print(f"   - Changed fields: {sync_job.metadata.get('changed_fields', [])}")
        else:
            print("❌ No sync job was created automatically")
        
        # Check if profile was created
        profile = RecordCommunicationProfile.objects.filter(record=test_record).first()
        if profile:
            print(f"✅ Communication profile created")
            print(f"   - Identifiers: {profile.communication_identifiers}")
            print(f"   - Identifier fields: {profile.identifier_fields}")
        else:
            print("❌ No communication profile created")
        
        # Test 2: Update record with new identifier
        print("\n" + "-"*40)
        print("Test 2: Update record with new identifier")
        print("-"*40)
        
        # Clear previous sync jobs
        RecordSyncJob.objects.filter(record=test_record).delete()
        
        # Update record with phone number
        test_record.data['phone_number'] = '+1234567890'
        test_record.updated_by = user
        test_record.save()
        
        print(f"✅ Updated record {test_record.id} with phone: +1234567890")
        
        # Check if sync was triggered for update
        time.sleep(1)
        
        sync_jobs = RecordSyncJob.objects.filter(record=test_record)
        if sync_jobs.exists():
            sync_job = sync_jobs.first()
            print(f"✅ Sync job created for update!")
            print(f"   - Job ID: {sync_job.id}")
            print(f"   - Type: {sync_job.job_type}")
            print(f"   - Reason: {sync_job.trigger_reason}")
            if sync_job.metadata:
                print(f"   - Changed fields: {sync_job.metadata.get('changed_fields', [])}")
        else:
            print("❌ No sync job created for update")
        
        # Test 3: Update non-identifier field (should NOT trigger sync)
        print("\n" + "-"*40)
        print("Test 3: Update non-identifier field")
        print("-"*40)
        
        # Clear previous sync jobs
        RecordSyncJob.objects.filter(record=test_record).delete()
        
        # Update a non-identifier field
        test_record.data['notes'] = 'Some test notes'
        test_record.updated_by = user
        test_record.save()
        
        print(f"✅ Updated record {test_record.id} with notes (non-identifier)")
        
        # Check if sync was triggered
        time.sleep(1)
        
        sync_jobs = RecordSyncJob.objects.filter(record=test_record)
        if sync_jobs.exists():
            print("⚠️  Sync job was created (unexpected - notes is not an identifier)")
            sync_job = sync_jobs.first()
            print(f"   - Reason: {sync_job.trigger_reason}")
        else:
            print("✅ No sync job created (correct - notes is not an identifier)")
        
        # Test 4: Check sync throttling
        print("\n" + "-"*40)
        print("Test 4: Check sync throttling")
        print("-"*40)
        
        # Update profile to simulate recent sync
        if profile:
            from django.utils import timezone
            profile.last_full_sync = timezone.now()
            profile.save()
            print("✅ Set last_full_sync to now")
        
        # Try to update identifier again
        test_record.data['personal_email'] = f"updated_{test_email}"
        test_record.updated_by = user
        test_record.save()
        
        print(f"✅ Updated email immediately after sync")
        
        time.sleep(1)
        sync_jobs = RecordSyncJob.objects.filter(
            record=test_record,
            created_at__gt=timezone.now() - timezone.timedelta(seconds=5)
        )
        
        if sync_jobs.exists():
            print("⚠️  Sync job created despite recent sync")
        else:
            print("✅ No sync job created (throttled due to recent sync)")
        
        print("\n" + "="*60)
        print("Automatic Sync Trigger Test Complete")
        print("="*60)
        
        # Cleanup
        test_record.delete()
        print("\n✅ Test record cleaned up")

if __name__ == "__main__":
    test_automatic_sync_triggers()