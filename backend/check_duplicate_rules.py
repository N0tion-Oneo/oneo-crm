#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')
django.setup()

from django_tenants.utils import schema_context
from duplicates.models import DuplicateRule
from pipelines.models import Pipeline, Field

with schema_context('oneotalent'):
    # Get contacts pipeline
    contacts_pipeline = Pipeline.objects.filter(slug='contacts').first()
    
    if contacts_pipeline:
        print(f"Contacts Pipeline: {contacts_pipeline.name} (ID: {contacts_pipeline.id})")
        
        # Show all fields
        fields = Field.objects.filter(pipeline=contacts_pipeline)
        print(f"\nFields in pipeline:")
        for field in fields:
            print(f"  - {field.name} ({field.field_type})")
        
        # Show duplicate rules
        rules = DuplicateRule.objects.filter(pipeline=contacts_pipeline, is_active=True)
        print(f"\nActive duplicate rules: {rules.count()}")
        
        for rule in rules:
            print(f"\n  Rule: {rule.name}")
            print(f"    Fields: {rule.fields}")
            print(f"    Logic tree: {rule.logic_tree}")
            
            # Check if phone_number is in the rule
            if 'phone_number' in str(rule.fields) or 'phone_number' in str(rule.logic_tree):
                print(f"    ✅ Rule includes phone_number field")
            else:
                print(f"    ❌ Rule does NOT include phone_number field")
    else:
        print("No contacts pipeline found")