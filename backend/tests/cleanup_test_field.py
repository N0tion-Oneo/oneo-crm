#!/usr/bin/env python3
"""
Clean up the test field we created during testing
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
from pipelines.models import Pipeline, Field

with schema_context('oneotalent'):
    # Find and delete the test field
    pipeline = Pipeline.objects.filter(name='Sales Pipeline').first()
    if pipeline:
        test_field = pipeline.fields.filter(name='migration_test_field').first()
        if test_field:
            print(f"🗑️  Deleting test field: {test_field.name} (slug: {test_field.slug})")
            test_field.delete()
            print("✅ Test field deleted successfully")
        else:
            print("❌ Test field not found")
    else:
        print("❌ Sales Pipeline not found")