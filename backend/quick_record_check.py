#!/usr/bin/env python3
"""
Quick check: Find which pipeline in OneOTalent has records
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django environment  
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = '1'

import django
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record

with schema_context('oneotalent'):
    print("📊 OneOTalent Pipelines & Records:")
    print("=" * 50)
    
    pipelines = Pipeline.objects.all()
    for pipeline in pipelines:
        record_count = pipeline.records.filter(is_deleted=False).count()
        field_count = pipeline.fields.count()
        
        print(f"🔹 {pipeline.name} (ID: {pipeline.id})")
        print(f"   Fields: {field_count}")
        print(f"   Records: {record_count}")
        
        if record_count > 0:
            sample_record = pipeline.records.filter(is_deleted=False).first()
            if sample_record and sample_record.data:
                data_keys = list(sample_record.data.keys())
                print(f"   Sample record keys: {sorted(data_keys)[:8]}{'...' if len(data_keys) > 8 else ''}")
        print()