#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from pipelines.models import Pipeline

# Mapping of old invalid types to valid ones
type_mapping = {
    'crm': 'deals',
    'ats': 'contacts', 
    'cms': 'custom',
    'projects': 'custom'
}

# Get valid choices
valid_types = [choice[0] for choice in Pipeline.PIPELINE_TYPES]
print(f"Valid pipeline types: {valid_types}")

# Fix invalid pipeline types
for pipeline in Pipeline.objects.all():
    if pipeline.pipeline_type not in valid_types:
        old_type = pipeline.pipeline_type
        new_type = type_mapping.get(old_type, 'custom')
        pipeline.pipeline_type = new_type
        pipeline.save()
        print(f"Fixed pipeline {pipeline.id}: {old_type} -> {new_type}")
    else:
        print(f"Pipeline {pipeline.id} already has valid type: {pipeline.pipeline_type}")

print("Done!")
