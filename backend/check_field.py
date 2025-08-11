#!/usr/bin/env python
import os
import sys
import django

# Add the backend directory to Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

# Setup Django
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Field, Pipeline

with schema_context('oneotalent'):
    # Check if pipeline 2 exists
    try:
        pipeline = Pipeline.objects.get(id=2)
        print(f'Pipeline exists: {pipeline.name}')
    except Pipeline.DoesNotExist:
        print('Pipeline 2 does not exist')
        print('Available pipelines:')
        for p in Pipeline.objects.all():
            print(f'  - ID {p.id}: {p.name}')
    
    # Check if field 67 exists (including deleted)
    try:
        field = Field.objects.get(id=67)
        print(f'Field exists: ID {field.id}, Name: {field.name}, Pipeline: {field.pipeline.name}, Deleted: {field.is_deleted}')
        
        # Check if field is in the right pipeline
        if field.pipeline.id != 2:
            print(f'WARNING: Field 67 is in pipeline {field.pipeline.id}, not pipeline 2')
            
    except Field.DoesNotExist:
        print('Field 67 does not exist')
        print('Available deleted fields:')
        for f in Field.objects.filter(is_deleted=True):
            print(f'  - ID {f.id}: {f.name} (Pipeline: {f.pipeline.name})')