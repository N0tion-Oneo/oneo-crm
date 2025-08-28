#!/usr/bin/env python
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from duplicates.models import DuplicateRule

with schema_context('oneotalent'):
    # Get contacts pipeline
    contacts_pipeline = Pipeline.objects.filter(slug='contacts').first()
    
    if contacts_pipeline:
        print(f"Checking phone number storage in Contacts pipeline...")
        print("=" * 60)
        
        # Get a record with phone number
        record_with_phone = Record.objects.filter(
            pipeline=contacts_pipeline,
            data__phone_number__isnull=False
        ).first()
        
        if record_with_phone:
            print(f"\nRecord ID: {record_with_phone.id}")
            print(f"Raw data: {json.dumps(record_with_phone.data, indent=2)}")
            
            # Check specific field
            phone_value = record_with_phone.data.get('phone_number')
            print(f"\nPhone field value:")
            print(f"  Type: {type(phone_value)}")
            print(f"  Value: {phone_value}")
            
            if isinstance(phone_value, list):
                print(f"  ⚠️ Phone is stored as ARRAY/LIST")
                print(f"  Array contents: {phone_value}")
            elif isinstance(phone_value, str):
                print(f"  ✅ Phone is stored as STRING")
            else:
                print(f"  ❓ Phone is stored as: {type(phone_value)}")
        
        # Check duplicate rule
        print("\n" + "=" * 60)
        print("Duplicate Rule Configuration:")
        rules = DuplicateRule.objects.filter(pipeline=contacts_pipeline, is_active=True)
        for rule in rules:
            print(f"\nRule: {rule.name}")
            print(f"Logic: {json.dumps(rule.logic, indent=2)}")
            
            # Check if rule is looking for phone_number
            logic_str = json.dumps(rule.logic)
            if 'phone_number' in logic_str:
                print("✅ Rule references phone_number field")
                
                # Check if it handles arrays
                if 'array' in logic_str.lower() or 'list' in logic_str.lower():
                    print("✅ Rule might handle arrays")
                else:
                    print("⚠️ Rule might NOT handle arrays properly")
            else:
                print("❌ Rule does NOT reference phone_number field")