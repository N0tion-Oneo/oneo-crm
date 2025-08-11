#!/usr/bin/env python
"""Check what fields are actually defined in the pipeline"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record

def check_fields():
    with schema_context('oneotalent'):
        pipeline = Pipeline.objects.get(id=1)
        print(f"📋 Pipeline: {pipeline.name} (ID: {pipeline.id})")
        
        fields = Field.objects.filter(pipeline=pipeline)
        print(f"🔧 Pipeline has {fields.count()} defined fields:")
        
        for field in fields:
            print(f"   • {field.slug} ({field.field_type}) - {field.name}")
        
        # Check if test_field exists
        test_field = fields.filter(slug='test_field').first()
        if test_field:
            print(f"\n✅ test_field EXISTS:")
            print(f"   Type: {test_field.field_type}")
            print(f"   Name: {field.name}")
        else:
            print(f"\n❌ test_field DOES NOT EXIST in pipeline definition")
            
        # Check a sample record's data
        record = Record.objects.filter(pipeline=pipeline).first()
        if record:
            print(f"\n📝 Sample record data keys:")
            if 'test_field' in record.data:
                print(f"   ✅ test_field exists in record data: {record.data['test_field']}")
            else:
                print(f"   ❌ test_field not in record data")
            print(f"   Record has {len(record.data)} fields: {list(record.data.keys())[:10]}")

if __name__ == '__main__':
    check_fields()