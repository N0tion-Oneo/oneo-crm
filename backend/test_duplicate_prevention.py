#!/usr/bin/env python
"""Test that duplicate prevention is working in batch processing"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from communications.models import Participant, ParticipantSettings
from communications.services.auto_create_service import AutoCreateContactService
from pipelines.models import Pipeline, Record

User = get_user_model()

# Switch to oneotalent tenant
schema_name = 'oneotalent'

with schema_context(schema_name):
    print(f"\n🧪 Testing duplicate prevention in tenant: {schema_name}")
    
    # Get admin user
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        print("❌ No admin user found")
        sys.exit(1)
    print(f"✅ Using admin user: {admin.email}")
    
    # Get settings
    settings = ParticipantSettings.objects.first()
    if not settings:
        print("❌ No participant settings found")
        sys.exit(1)
    
    # Make sure duplicate checking is enabled
    settings.check_duplicates_before_create = True
    settings.save()
    print(f"✅ Duplicate checking enabled: {settings.check_duplicates_before_create}")
    
    # Get the contact pipeline
    contacts_pipeline = Pipeline.objects.filter(name='Contacts').first()
    if not contacts_pipeline:
        print("❌ No Contacts pipeline found")
        sys.exit(1)
    
    # Create a test contact record first
    test_email = "duplicate.test@example.com"
    test_phone = "+27123456789"
    
    print(f"\n📋 Creating initial contact record with email: {test_email}")
    
    initial_record = Record.objects.create(
        pipeline=contacts_pipeline,
        title="Test Contact",
        data={
            'personal_email': test_email,
            'phone_number': test_phone,
            'first_name': 'Test',
            'last_name': 'Contact'
        },
        created_by=admin,
        updated_by=admin
    )
    print(f"✅ Created initial record: {initial_record.id}")
    
    # Now create participants with slightly different emails but they should still be matched
    print(f"\n🔄 Creating 3 participants with variations...")
    
    participants = []
    # Create first participant with exact email and make it eligible
    p1 = Participant.objects.create(
        email=test_email,
        name="Test Participant 1",
        total_messages=5  # Make eligible
    )
    participants.append(p1)
    print(f"  - Created participant: {p1.name} with email: {p1.email}")
    
    # Create second with phone only
    p2 = Participant.objects.create(
        phone=test_phone,
        name="Test Participant 2",
        total_messages=5  # Make eligible
    )
    participants.append(p2)
    print(f"  - Created participant: {p2.name} with phone: {p2.phone}")
    
    # Create third with different email but from same person
    p3 = Participant.objects.create(
        email="duplicate.test+alias@example.com",
        name="Test Participant 3",
        total_messages=5  # Make eligible
    )
    participants.append(p3)
    print(f"  - Created participant: {p3.name} with email: {p3.email}")
    
    # Initialize the auto-create service
    service = AutoCreateContactService()
    
    print(f"\n🚀 Processing batch to check duplicate prevention...")
    
    # Process the batch
    results = service.process_batch(batch_size=10, user=admin)
    
    print(f"\n📊 Batch processing results:")
    print(f"  Created: {results.get('created', 0)}")
    print(f"  Contacts created: {results.get('contacts_created', 0)}")
    print(f"  Skipped: {results.get('skipped', 0)}")
    print(f"  Duplicates: {results.get('duplicates', 0)}")
    print(f"  Errors: {results.get('errors', 0)}")
    
    # Check how many contact records exist with this email
    records_with_email = Record.objects.filter(
        pipeline=contacts_pipeline,
        data__personal_email=test_email
    )
    
    print(f"\n🔍 Checking for duplicates...")
    print(f"  Records with email {test_email}: {records_with_email.count()}")
    
    if records_with_email.count() == 1:
        print("✅ SUCCESS: No duplicates created! Duplicate prevention is working.")
        
        # Check that participants were linked to existing record
        linked_count = 0
        for p in participants:
            p.refresh_from_db()
            if p.contact_record_id == initial_record.id:
                linked_count += 1
        
        print(f"✅ {linked_count}/{len(participants)} participants linked to existing record")
    else:
        print(f"❌ FAILURE: Found {records_with_email.count()} records, expected 1")
        for record in records_with_email:
            print(f"  - Record {record.id}: {record.data.get('personal_email')}")
    
    # Cleanup
    print(f"\n🧹 Cleaning up test data...")
    for p in participants:
        p.delete()
    initial_record.delete()
    print("✅ Test data cleaned up")