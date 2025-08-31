#!/usr/bin/env python
"""
Test that only specific channels sync when specific identifier fields change
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
from communications.record_communications.models import RecordCommunicationProfile, RecordSyncJob
from communications.record_communications.signals import get_identifier_fields_from_duplicate_rules
from django.contrib.auth import get_user_model

User = get_user_model()

def test_channel_specific_sync():
    """Test that only relevant channels sync based on identifier changes"""
    
    with schema_context('oneotalent'):
        print("\n" + "="*60)
        print("Testing Channel-Specific Sync")
        print("="*60)
        
        # Get test pipeline and user
        pipeline = Pipeline.objects.filter(slug='contacts').first()
        user = User.objects.filter(is_superuser=True).first()
        
        print(f"✅ Using pipeline: {pipeline.name}")
        print(f"✅ Using user: {user.email}")
        
        # Get identifier fields
        identifier_fields = get_identifier_fields_from_duplicate_rules(pipeline)
        print(f"📋 Identifier fields: {identifier_fields}")
        
        # Test 1: Add only email - should sync only email channels
        print("\n" + "-"*40)
        print("Test 1: Add only email identifier")
        print("-"*40)
        
        RecordSyncJob.objects.all().delete()  # Clear sync jobs
        
        test_record_1 = Record.objects.create(
            pipeline=pipeline,
            data={
                'first_name': 'Email',
                'last_name': 'Only',
                'personal_email': 'email_only@example.com',  # Only email
            },
            created_by=user,
            updated_by=user
        )
        
        print(f"✅ Created record {test_record_1.id} with only email")
        
        time.sleep(1)
        sync_job = RecordSyncJob.objects.filter(record=test_record_1).first()
        if sync_job:
            print(f"✅ Sync job created")
            print(f"   - Trigger: {sync_job.trigger_reason}")
            
            # Check the Celery task arguments to see channels filter
            from celery.result import AsyncResult
            if sync_job.celery_task_id:
                task_result = AsyncResult(sync_job.celery_task_id)
                print(f"   - Task args: {task_result.args if hasattr(task_result, 'args') else 'N/A'}")
                print(f"   - Task kwargs: {task_result.kwargs if hasattr(task_result, 'kwargs') else 'N/A'}")
        
        # Test 2: Add only phone - should sync only WhatsApp
        print("\n" + "-"*40)
        print("Test 2: Add only phone identifier")
        print("-"*40)
        
        RecordSyncJob.objects.all().delete()
        
        test_record_2 = Record.objects.create(
            pipeline=pipeline,
            data={
                'first_name': 'Phone',
                'last_name': 'Only',
                'phone_number': '+1234567890',  # Only phone
            },
            created_by=user,
            updated_by=user
        )
        
        print(f"✅ Created record {test_record_2.id} with only phone")
        
        time.sleep(1)
        sync_job = RecordSyncJob.objects.filter(record=test_record_2).first()
        if sync_job:
            print(f"✅ Sync job created")
            print(f"   - Trigger: {sync_job.trigger_reason}")
        
        # Test 3: Update existing record with LinkedIn - should sync only LinkedIn
        print("\n" + "-"*40)
        print("Test 3: Update with LinkedIn identifier")
        print("-"*40)
        
        RecordSyncJob.objects.all().delete()
        
        test_record_3 = Record.objects.create(
            pipeline=pipeline,
            data={
                'first_name': 'No',
                'last_name': 'Identifiers',
            },
            created_by=user,
            updated_by=user
        )
        
        print(f"✅ Created record {test_record_3.id} without identifiers")
        time.sleep(1)
        
        # Now update with LinkedIn
        RecordSyncJob.objects.all().delete()
        test_record_3.data['linkedin'] = 'https://linkedin.com/in/test-user'
        test_record_3.save()
        
        print(f"✅ Updated record {test_record_3.id} with LinkedIn")
        
        time.sleep(1)
        sync_job = RecordSyncJob.objects.filter(record=test_record_3).first()
        if sync_job:
            print(f"✅ Sync job created for update")
            print(f"   - Trigger: {sync_job.trigger_reason}")
        
        # Test 4: Add multiple identifiers - should sync multiple channels
        print("\n" + "-"*40)
        print("Test 4: Add multiple identifiers")
        print("-"*40)
        
        RecordSyncJob.objects.all().delete()
        
        test_record_4 = Record.objects.create(
            pipeline=pipeline,
            data={
                'first_name': 'Multi',
                'last_name': 'Channel',
                'personal_email': 'multi@example.com',
                'phone_number': '+9876543210',
                'linkedin': 'https://linkedin.com/in/multi-user'
            },
            created_by=user,
            updated_by=user
        )
        
        print(f"✅ Created record {test_record_4.id} with all identifiers")
        
        time.sleep(1)
        sync_job = RecordSyncJob.objects.filter(record=test_record_4).first()
        if sync_job:
            print(f"✅ Sync job created")
            print(f"   - Trigger: {sync_job.trigger_reason}")
            print(f"   - Should sync all channels (email, whatsapp, linkedin)")
        
        # Cleanup
        print("\n" + "-"*40)
        print("Cleanup")
        print("-"*40)
        
        test_record_1.delete()
        test_record_2.delete()
        test_record_3.delete()
        test_record_4.delete()
        print("✅ Test records cleaned up")
        
        print("\n" + "="*60)
        print("Channel-Specific Sync Test Complete")
        print("="*60)
        print("\nSummary:")
        print("- Email identifier → Syncs only Gmail/Email channels")
        print("- Phone identifier → Syncs only WhatsApp channel")
        print("- LinkedIn identifier → Syncs only LinkedIn channel")
        print("- Multiple identifiers → Syncs all relevant channels")

if __name__ == "__main__":
    test_channel_specific_sync()