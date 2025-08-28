#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record

with schema_context('oneotalent'):
    # Revert the test record back to structured phone format
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
            
            # Revert to structured format
            test_record.data['phone_number'] = {
                'number': '782270354',
                'country_code': '+27'
            }
            test_record.save()
            
            print(f"Reverted phone to structured format: {test_record.data.get('phone_number')}")
        else:
            print("Test record not found")
    else:
        print("Contacts pipeline not found")