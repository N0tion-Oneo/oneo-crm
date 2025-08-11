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
    pipeline = Pipeline.objects.get(id=2)
    print(f'Pipeline: {pipeline.name}')
    
    # Get all fields in pipeline 2 (including deleted)
    all_fields = Field.objects.with_deleted().filter(pipeline=pipeline)
    print(f'\nAll fields in pipeline (including deleted):')
    for field in all_fields:
        status = "DELETED" if field.is_deleted else "ACTIVE"
        print(f'  - ID {field.id}: {field.name} ({status})')
    
    # Get specifically deleted fields
    deleted_fields = Field.objects.deleted_only().filter(pipeline=pipeline)
    print(f'\nDeleted fields available for restore:')
    for field in deleted_fields:
        print(f'  - ID {field.id}: {field.name}')