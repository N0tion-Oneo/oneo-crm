#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record, Field

with schema_context('oneotalent'):
    # Update the test record to store phone as a simple string
    contacts_pipeline = Pipeline.objects.filter(slug='contacts').first()
    
    if contacts_pipeline:
        # Find our test record
        test_record = Record.objects.filter(
            pipeline=contacts_pipeline,
            data__first_name='John Smith (Test Contact)'
        ).first()
        
        if test_record:
            print(f"Found test record ID: {test_record.id}")
            print(f"Current phone data: {test_record.data.get('phone_number')}")
            
            # Update to store phone as a simple string
            test_record.data['phone_number'] = '+27782270354'
            test_record.save()
            
            print(f"Updated phone to simple string: {test_record.data.get('phone_number')}")
            print("\nNow the duplicate detection should work!")
        else:
            print("Test record not found")
    else:
        print("Contacts pipeline not found")