#!/usr/bin/env python
"""
Debug LinkedIn field extraction for Saul's record
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record
from tenants.models import Tenant
from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor

# Get oneotalent tenant
tenant = Tenant.objects.get(schema_name='oneotalent')

with schema_context(tenant.schema_name):
    # Get the pipeline and record
    pipeline = Pipeline.objects.get(slug='contacts')
    record = Record.objects.get(id=66)  # Saul's record
    
    print(f"Record data: {record.data}")
    print("\n" + "=" * 60)
    
    # Check fields in the pipeline
    fields = Field.objects.filter(pipeline=pipeline, is_deleted=False)
    
    print("Pipeline fields:")
    for field in fields:
        print(f"  {field.slug}: {field.field_type} - {field.label}")
        if field.slug == 'linkedin':
            print(f"    -> Field config: {field.field_config}")
    
    print("\n" + "=" * 60)
    
    # Extract identifiers
    extractor = RecordIdentifierExtractor()
    
    # Check individual field processing
    if 'linkedin' in record.data:
        linkedin_value = record.data['linkedin']
        print(f"\nLinkedIn value: {linkedin_value}")
        
        # Find the field
        try:
            linkedin_field = Field.objects.get(pipeline=pipeline, slug='linkedin', is_deleted=False)
            print(f"LinkedIn field type: {linkedin_field.field_type}")
            
            # Process this field directly
            result = extractor._categorize_identifier(
                linkedin_value,
                linkedin_field.field_type,
                linkedin_field.field_config
            )
            print(f"Categorized result: {result}")
        except Field.DoesNotExist:
            print("LinkedIn field not found in pipeline")
    
    print("\n" + "=" * 60)
    
    # Full extraction
    identifiers = extractor.extract_identifiers_from_record(record)
    print(f"\nExtracted identifiers: {identifiers}")