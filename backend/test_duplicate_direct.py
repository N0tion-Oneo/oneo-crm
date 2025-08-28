#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from django_tenants.utils import schema_context
from duplicates.logic_engine import FieldMatcher
from pipelines.models import Pipeline, Record, Field

with schema_context('oneotalent'):
    # Test the phone matching directly
    matcher = FieldMatcher()
    
    # Test data
    stored_phone = {
        'number': '782270354',
        'country_code': '+27'
    }
    
    test_phones = [
        '+27782270354',      # String format
        '27782270354',       # Without +
        stored_phone         # Dict format
    ]
    
    print("Testing phone matching with structured data:")
    print("=" * 60)
    print(f"Stored phone (dict): {stored_phone}")
    print()
    
    # Get phone field for config
    contacts_pipeline = Pipeline.objects.filter(slug='contacts').first()
    if contacts_pipeline:
        # List all fields first
        fields = Field.objects.filter(pipeline=contacts_pipeline)
        print(f"Available fields: {[f.name for f in fields]}")
        
        phone_field = Field.objects.filter(
            pipeline=contacts_pipeline,
            name='Phone Number'  # Try the label format
        ).first()
        
        if not phone_field:
            # Try to find any phone field
            phone_field = Field.objects.filter(
                pipeline=contacts_pipeline,
                field_type='phone'
            ).first()
        
        if phone_field:
            print("Testing matches:")
            for test_phone in test_phones:
                result = matcher._match_phone_normalized(
                    stored_phone, 
                    test_phone,
                    phone_field.field_config if phone_field else {}
                )
                normalized1 = matcher._extract_and_normalize_phone(stored_phone)
                normalized2 = matcher._extract_and_normalize_phone(test_phone)
                
                print(f"\nComparing:")
                print(f"  Stored: {stored_phone} -> normalized: '{normalized1}'")
                print(f"  Test:   {test_phone} -> normalized: '{normalized2}'")
                print(f"  Match:  {'✅ YES' if result else '❌ NO'}")
        else:
            print("Phone field not found")
    else:
        print("Contacts pipeline not found")